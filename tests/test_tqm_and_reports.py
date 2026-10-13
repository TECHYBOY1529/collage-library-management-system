from datetime import timedelta
from app.extensions import db
from app.models import (
    Member,
    Feedback,
    Complaint,
    RootCauseAnalysis,
    ImprovementAction,
    PDCACycle,
    User,
    Book,
    utcnow,
)
from app.services.tqm_service import (
    get_customer_satisfaction_metrics,
    get_pareto_analysis,
    get_control_charts_data,
    get_all_kpis,
)
from seed import seed_demo_data, clear_demo_data_only
from tests.conftest import login_as


def test_feedback_and_complaint_submission_and_pareto_analysis(client, app):
    login_as(client, "student1", "StudPass123")

    # Submit customer satisfaction feedback via member endpoint
    fb_resp = client.post(
        "/member/feedback-complaints",
        data={
            "form_type": "feedback",
            "fb-category": "Book Availability",
            "fb-rating": 5,
            "fb-book_id": 0,
            "fb-comments": "Great collection of computer science books.",
            "fb-is_recurring_concern": False,
        },
        follow_redirects=True,
    )
    assert fb_resp.status_code == 200
    assert b"quality feedback has been recorded" in fb_resp.data

    # Submit formal complaint via member endpoint
    cmp_resp = client.post(
        "/member/feedback-complaints",
        data={
            "form_type": "complaint",
            "cmp-title": "Long wait time at circulation desk",
            "cmp-category": "Waiting Time",
            "cmp-severity": "High",
            "cmp-description": "Queue took more than 10 minutes at noon.",
        },
        follow_redirects=True,
    )
    assert cmp_resp.status_code == 200
    assert b"complaint has been logged" in cmp_resp.data

    with app.app_context():
        sat = get_customer_satisfaction_metrics()
        assert sat["total_responses"] == 1
        assert sat["average_score"] == 5.0

        pareto = get_pareto_analysis()
        assert pareto["total_complaints"] == 1
        assert pareto["categories"] == ["Waiting Time"]
        assert pareto["cumulative_pct"] == [100.0]


def test_pdca_rca_kaizen_and_spc_insufficient_data_honesty(client, app):
    # With only 0 observations in empty test DB, SPC must honestly report Insufficient Data (never in control)
    with app.app_context():
        charts = get_control_charts_data()
        assert charts["satisfaction"]["sufficient_data"] is False
        assert charts["satisfaction"]["in_statistical_control"] is None
        assert "Insufficient Data" in charts["satisfaction"]["statistical_status"]

    login_as(client, "qm_test", "QmPass123")

    # Create PDCA Cycle
    pdca_resp = client.post(
        "/quality/pdca",
        data={
            "title": "Reduce Checkout Processing Time",
            "current_phase": "Plan",
            "problem_statement": "Average checkout takes 65s",
            "baseline_metric": "65s",
            "target_metric": "<= 45s",
            "measurement_method": "Loan processing_time_seconds log",
            "assigned_owner": "Quality Team",
            "intervention_details": "Standardize 3-step checklist",
        },
        follow_redirects=True,
    )
    assert pdca_resp.status_code == 200
    assert b"Reduce Checkout Processing Time" in pdca_resp.data

    with app.app_context():
        cycle = PDCACycle.query.first()
        assert cycle is not None
        cycle_id = cycle.id

    # Advance PDCA Cycle to Check/Act
    adv_resp = client.post(
        f"/quality/pdca/{cycle_id}/advance",
        data={
            "current_phase": "Check",
            "measured_outcome": "Reduced to 34s",
            "target_achieved": "1",
        },
        follow_redirects=True,
    )
    assert adv_resp.status_code == 200
    assert b"Reduced to 34s" in adv_resp.data

    # Create Root Cause Analysis (Fishbone + 5 Whys)
    rca_resp = client.post(
        "/quality/rca",
        data={
            "complaint_id": 0,
            "problem_title": "Delayed Reshelving of Returned Books",
            "fishbone_people": "Limited student assistants during afternoon shift",
            "fishbone_processes": "Batch cart sorting done only once per day",
            "fishbone_technology": "No sorting cart scanner",
            "fishbone_materials": "Single return cart",
            "fishbone_environment": "Narrow aisle in CS section",
            "fishbone_policies": "No hourly reshelving SLA",
            "why_1": "Books sit on return cart for 6 hours",
            "why_2": "Cart is only cleared at 5 PM",
            "why_3": "No hourly sorting schedule assigned",
            "identified_root_cause": "Lack of hourly sorting schedule and category-coded carts",
        },
        follow_redirects=True,
    )
    assert rca_resp.status_code == 200
    assert b"Delayed Reshelving of Returned Books" in rca_resp.data


def test_demo_seeding_kpis_and_csv_report_exports(client, app):
    with app.app_context():
        # Create a real non-demo user first to ensure reset_existing_demo preserves real data!
        real_user = User(
            username="real_faculty",
            email="real@college.edu",
            full_name="Real Faculty Member",
            role="member",
            is_demo=False,
        )
        real_user.set_password("RealPass123")
        db.session.add(real_user)
        db.session.commit()

        summary = seed_demo_data(reset_existing_demo=True)
        assert summary["books"] >= 30
        assert summary["members"] >= 10

        # Verify KPI calculations with seeded data
        kpis = get_all_kpis()
        assert len(kpis) == 10
        for k in kpis:
            assert k["value"] != "Insufficient Data"
            assert k["formula"]
            assert k["data_source"]

        # Verify SPC control charts now have sufficient data (n >= 5)
        charts = get_control_charts_data()
        assert charts["satisfaction"]["sufficient_data"] is True
        assert charts["processing_time"]["sufficient_data"] is True
        assert charts["complaint_resolution"]["sufficient_data"] is True

        # Verify clear_demo_data_only removes demo books but preserves real_faculty!
        clear_demo_data_only()
        assert Book.query.filter_by(is_demo=True).count() == 0
        assert User.query.filter_by(username="real_faculty").first() is not None

        # Re-seed for CSV export verification
        seed_demo_data(reset_existing_demo=True)

    login_as(client, "admin_test", "AdminPass123")
    for endpoint in [
        "/reports/export/inventory.csv",
        "/reports/export/loans.csv",
        "/reports/export/overdue.csv",
        "/reports/export/fines.csv",
        "/reports/export/tqm_kpis.csv",
        "/reports/export/complaints.csv",
    ]:
        csv_resp = client.get(endpoint)
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.content_type
        assert len(csv_resp.data) > 50
