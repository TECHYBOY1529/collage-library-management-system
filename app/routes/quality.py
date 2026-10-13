from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.extensions import db
from app.models import (
    Role,
    Complaint,
    RootCauseAnalysis,
    ImprovementAction,
    PDCACycle,
    StaffSuggestion,
    utcnow,
)
from app.decorators import role_required, get_current_user
from app.forms import RootCauseAnalysisForm, ImprovementActionForm, PDCACycleForm
from app.services.tqm_service import (
    get_customer_satisfaction_metrics,
    get_pareto_analysis,
    get_control_charts_data,
    get_all_kpis,
    get_borrowing_trend_chart,
)
from app.services.audit_service import log_audit

quality_bp = Blueprint("quality", __name__, url_prefix="/quality")


@quality_bp.route("/dashboard")
@role_required(Role.QUALITY, Role.ADMIN)
def dashboard():
    kpis = get_all_kpis()
    satisfaction = get_customer_satisfaction_metrics()
    pareto = get_pareto_analysis()
    borrowing_chart = get_borrowing_trend_chart()

    pdca_cycles = PDCACycle.query.order_by(PDCACycle.updated_at.desc()).all()
    actions = ImprovementAction.query.order_by(ImprovementAction.target_completion_date.asc()).all()

    action_counts = {
        "Open": sum(1 for a in actions if a.computed_display_status == "Open"),
        "In Progress": sum(1 for a in actions if a.computed_display_status == "In Progress"),
        "Overdue": sum(1 for a in actions if a.computed_display_status == "Overdue"),
        "Completed": sum(1 for a in actions if a.computed_display_status == "Completed"),
    }

    return render_template(
        "quality/dashboard.html",
        kpis=kpis,
        satisfaction=satisfaction,
        pareto=pareto,
        borrowing_chart=borrowing_chart,
        pdca_cycles=pdca_cycles,
        actions=actions[:6],
        action_counts=action_counts,
    )


@quality_bp.route("/kaizen", methods=["GET", "POST"])
@role_required(Role.QUALITY, Role.ADMIN)
def kaizen():
    form = ImprovementActionForm()
    rcas = RootCauseAnalysis.query.order_by(RootCauseAnalysis.created_at.desc()).all()
    form.rca_id.choices = [(0, "Independent Kaizen Action (No linked RCA)")] + [
        (r.id, f"RCA #{r.id}: {r.problem_title}") for r in rcas
    ]

    if form.validate_on_submit():
        rca_id = form.rca_id.data if form.rca_id.data and form.rca_id.data > 0 else None
        target_dt = datetime.combine(form.target_completion_date.data, datetime.min.time())
        action = ImprovementAction(
            rca_id=rca_id,
            problem_description=form.problem_description.data.strip(),
            identified_root_cause=form.identified_root_cause.data.strip(),
            proposed_corrective_action=form.proposed_corrective_action.data.strip(),
            assigned_owner=form.assigned_owner.data.strip(),
            priority=form.priority.data,
            target_completion_date=target_dt,
            status="Open",
            expected_result=form.expected_result.data.strip(),
            is_demo=False,
        )
        db.session.add(action)
        log_audit(
            "CREATE_KAIZEN_ACTION",
            "ImprovementAction",
            action.assigned_owner,
            f"Created Kaizen corrective action assigned to {action.assigned_owner} (Priority: {action.priority}).",
            get_current_user(),
            commit=True,
        )
        flash("Kaizen continuous improvement action registered.", "success")
        return redirect(url_for("quality.kaizen"))

    status_filter = request.args.get("status", "all")
    all_actions = ImprovementAction.query.order_by(
        ImprovementAction.target_completion_date.asc()
    ).all()
    if status_filter != "all":
        all_actions = [
            a for a in all_actions if a.computed_display_status.lower() == status_filter.lower()
        ]

    return render_template(
        "quality/kaizen.html",
        form=form,
        actions=all_actions,
        status_filter=status_filter,
    )


@quality_bp.route("/kaizen/<int:action_id>/update", methods=["POST"])
@role_required(Role.QUALITY, Role.ADMIN)
def update_kaizen(action_id):
    action = db.get_or_404(ImprovementAction, action_id)
    new_status = request.form.get("status", action.status)
    measured_result = request.form.get("measured_result", "").strip()
    completion_notes = request.form.get("completion_notes", "").strip()

    action.status = new_status
    if measured_result:
        action.measured_result = measured_result
    if completion_notes:
        action.completion_notes = completion_notes
    if new_status == "Completed" and not action.completed_date:
        action.completed_date = utcnow()

    log_audit(
        "UPDATE_KAIZEN_ACTION",
        "ImprovementAction",
        action.id,
        f"Updated Kaizen action #{action.id} status to '{new_status}'.",
        get_current_user(),
        commit=True,
    )
    flash(f"Kaizen action #{action.id} updated to '{new_status}'.", "success")
    return redirect(url_for("quality.kaizen"))


@quality_bp.route("/pdca", methods=["GET", "POST"])
@role_required(Role.QUALITY, Role.ADMIN)
def pdca():
    form = PDCACycleForm()
    if form.validate_on_submit():
        cycle = PDCACycle(
            title=form.title.data.strip(),
            current_phase=form.current_phase.data,
            problem_statement=form.problem_statement.data.strip(),
            baseline_metric=form.baseline_metric.data.strip(),
            target_metric=form.target_metric.data.strip(),
            measurement_method=form.measurement_method.data.strip(),
            assigned_owner=form.assigned_owner.data.strip(),
            intervention_details=form.intervention_details.data.strip() if form.intervention_details.data else None,
            implementation_start_date=utcnow() if form.current_phase.data in ("Do", "Check", "Act", "Completed") else None,
            measured_outcome=form.measured_outcome.data.strip() if form.measured_outcome.data else None,
            comparison_analysis=form.comparison_analysis.data.strip() if form.comparison_analysis.data else None,
            target_achieved=bool(form.target_achieved.data),
            standardization_action=form.standardization_action.data.strip() if form.standardization_action.data else None,
            next_cycle_recommendations=form.next_cycle_recommendations.data.strip() if form.next_cycle_recommendations.data else None,
            is_demo=False,
        )
        db.session.add(cycle)
        log_audit(
            "CREATE_PDCA_CYCLE",
            "PDCACycle",
            cycle.title,
            f"Created PDCA cycle '{cycle.title}' in phase '{cycle.current_phase}'.",
            get_current_user(),
            commit=True,
        )
        flash(f"PDCA cycle '{cycle.title}' created successfully.", "success")
        return redirect(url_for("quality.pdca"))

    cycles = PDCACycle.query.order_by(PDCACycle.updated_at.desc()).all()
    return render_template("quality/pdca.html", form=form, cycles=cycles)


@quality_bp.route("/pdca/<int:cycle_id>/advance", methods=["POST"])
@role_required(Role.QUALITY, Role.ADMIN)
def update_pdca(cycle_id):
    cycle = db.get_or_404(PDCACycle, cycle_id)
    cycle.current_phase = request.form.get("current_phase", cycle.current_phase)
    if request.form.get("intervention_details"):
        cycle.intervention_details = request.form.get("intervention_details").strip()
    if request.form.get("measured_outcome"):
        cycle.measured_outcome = request.form.get("measured_outcome").strip()
    if request.form.get("comparison_analysis"):
        cycle.comparison_analysis = request.form.get("comparison_analysis").strip()
    if "target_achieved" in request.form:
        cycle.target_achieved = request.form.get("target_achieved") == "1"
    if request.form.get("standardization_action"):
        cycle.standardization_action = request.form.get("standardization_action").strip()
    if request.form.get("next_cycle_recommendations"):
        cycle.next_cycle_recommendations = request.form.get("next_cycle_recommendations").strip()

    if cycle.current_phase == "Do" and not cycle.implementation_start_date:
        cycle.implementation_start_date = utcnow()
    if cycle.current_phase in ("Check", "Act", "Completed") and not cycle.implementation_end_date:
        cycle.implementation_end_date = utcnow()

    log_audit(
        "UPDATE_PDCA_CYCLE",
        "PDCACycle",
        cycle.id,
        f"Updated PDCA cycle #{cycle.id} ('{cycle.title}') to phase '{cycle.current_phase}'.",
        get_current_user(),
        commit=True,
    )
    flash(f"PDCA cycle '{cycle.title}' updated to {cycle.current_phase}.", "success")
    return redirect(url_for("quality.pdca"))


@quality_bp.route("/rca", methods=["GET", "POST"])
@role_required(Role.QUALITY, Role.ADMIN)
def rca():
    form = RootCauseAnalysisForm()
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    form.complaint_id.choices = [(0, "Systemic Quality Investigation (No single complaint)")] + [
        (c.id, f"CMP #{c.id}: {c.title} ({c.category})") for c in complaints
    ]

    if form.validate_on_submit():
        cmp_id = form.complaint_id.data if form.complaint_id.data and form.complaint_id.data > 0 else None
        rca_record = RootCauseAnalysis(
            complaint_id=cmp_id,
            problem_title=form.problem_title.data.strip(),
            fishbone_people=form.fishbone_people.data.strip() if form.fishbone_people.data else None,
            fishbone_processes=form.fishbone_processes.data.strip() if form.fishbone_processes.data else None,
            fishbone_technology=form.fishbone_technology.data.strip() if form.fishbone_technology.data else None,
            fishbone_materials=form.fishbone_materials.data.strip() if form.fishbone_materials.data else None,
            fishbone_environment=form.fishbone_environment.data.strip() if form.fishbone_environment.data else None,
            fishbone_policies=form.fishbone_policies.data.strip() if form.fishbone_policies.data else None,
            why_1=form.why_1.data.strip(),
            why_2=form.why_2.data.strip() if form.why_2.data else None,
            why_3=form.why_3.data.strip() if form.why_3.data else None,
            why_4=form.why_4.data.strip() if form.why_4.data else None,
            why_5=form.why_5.data.strip() if form.why_5.data else None,
            identified_root_cause=form.identified_root_cause.data.strip(),
            created_by_id=get_current_user().id,
            is_demo=False,
        )
        db.session.add(rca_record)
        log_audit(
            "CREATE_RCA",
            "RootCauseAnalysis",
            rca_record.problem_title,
            f"Completed Fishbone & 5-Whys RCA for '{rca_record.problem_title}'.",
            get_current_user(),
            commit=True,
        )
        flash("Root-Cause Analysis (Fishbone + 5 Whys) saved.", "success")
        return redirect(url_for("quality.rca"))

    rcas = RootCauseAnalysis.query.order_by(RootCauseAnalysis.created_at.desc()).all()
    return render_template("quality/rca.html", form=form, rcas=rcas)


@quality_bp.route("/control-charts")
@role_required(Role.QUALITY, Role.ADMIN)
def control_charts():
    charts = get_control_charts_data()
    return render_template("quality/control_charts.html", charts=charts)


@quality_bp.route("/suggestions", methods=["GET", "POST"])
@role_required(Role.QUALITY, Role.ADMIN)
def suggestions():
    if request.method == "POST":
        action_type = request.form.get("action_type", "create")
        if action_type == "create":
            title = request.form.get("title", "").strip()
            process_area = request.form.get("process_area", "Circulation & Issue/Return").strip()
            details = request.form.get("suggestion_details", "").strip()
            benefit = request.form.get("expected_benefit", "").strip()
            if title and details and benefit:
                s = StaffSuggestion(
                    submitted_by_id=get_current_user().id,
                    title=title,
                    process_area=process_area,
                    suggestion_details=details,
                    expected_benefit=benefit,
                    status="Submitted",
                )
                db.session.add(s)
                log_audit(
                    "SUBMIT_STAFF_SUGGESTION",
                    "StaffSuggestion",
                    title,
                    f"Staff suggestion '{title}' submitted for {process_area}.",
                    get_current_user(),
                    commit=True,
                )
                flash("Staff standardization & improvement suggestion recorded.", "success")
            else:
                flash("Please complete all required suggestion fields.", "danger")
        elif action_type == "review":
            s_id = request.form.get("suggestion_id", type=int)
            s = db.get_or_404(StaffSuggestion, s_id)
            s.status = request.form.get("status", s.status)
            s.review_notes = request.form.get("review_notes", "").strip()
            log_audit(
                "REVIEW_STAFF_SUGGESTION",
                "StaffSuggestion",
                s.id,
                f"Updated suggestion #{s.id} status to '{s.status}'.",
                get_current_user(),
                commit=True,
            )
            flash(f"Suggestion #{s.id} updated to '{s.status}'.", "info")
        return redirect(url_for("quality.suggestions"))

    suggestions_list = StaffSuggestion.query.order_by(StaffSuggestion.created_at.desc()).all()
    return render_template("quality/suggestions.html", suggestions=suggestions_list)
