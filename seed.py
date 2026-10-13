from datetime import timedelta
from app.extensions import db
from app.models import (
    Role,
    User,
    Member,
    Author,
    Publisher,
    Category,
    Book,
    BookCopy,
    FinePolicy,
    Loan,
    Reservation,
    Fine,
    Feedback,
    Complaint,
    RootCauseAnalysis,
    ImprovementAction,
    PDCACycle,
    StaffSuggestion,
    Notification,
    AuditLog,
    utcnow,
)


def clear_demo_data_only():
    """Safely remove ONLY records marked with is_demo=True, preserving all real user data."""
    # Delete child tables first to respect foreign keys
    AuditLog.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Notification.query.filter_by(is_demo=True).delete(synchronize_session=False)
    StaffSuggestion.query.filter_by(is_demo=True).delete(synchronize_session=False)
    PDCACycle.query.filter_by(is_demo=True).delete(synchronize_session=False)
    ImprovementAction.query.filter_by(is_demo=True).delete(synchronize_session=False)
    RootCauseAnalysis.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Complaint.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Feedback.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Fine.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Reservation.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Loan.query.filter_by(is_demo=True).delete(synchronize_session=False)
    BookCopy.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Book.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Category.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Publisher.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Author.query.filter_by(is_demo=True).delete(synchronize_session=False)
    Member.query.filter_by(is_demo=True).delete(synchronize_session=False)
    User.query.filter_by(is_demo=True).delete(synchronize_session=False)
    db.session.commit()
    db.session.expire_all()


def seed_demo_data(reset_existing_demo: bool = True) -> dict:
    """Seed comprehensive academic & TQM demonstration data (32 books, 12 members, loans, Pareto complaints, RCA, Kaizen, PDCA)."""
    if reset_existing_demo:
        clear_demo_data_only()

    now = utcnow()

    # 1. Ensure Active FinePolicy exists
    if not FinePolicy.query.filter_by(is_active=True).first():
        db.session.add(
            FinePolicy(
                name="Standard College Library Policy",
                loan_duration_days=14,
                fine_per_day=2.00,
                grace_period_days=0,
                max_fine_cap=100.00,
                is_active=True,
            )
        )

    # 2. Create Demo Staff Users (Admin & Quality Manager) if not present
    admin_user = User.query.filter_by(username="admin_demo").first()
    if not admin_user:
        admin_user = User(
            username="admin_demo",
            email="librarian.demo@college-library.edu",
            full_name="Dr. Eleanor Vance [DEMO ADMIN]",
            role=Role.ADMIN,
            is_active=True,
            is_demo=True,
        )
        admin_user.set_password("Admin@123")
        db.session.add(admin_user)

    qm_user = User.query.filter_by(username="tqm_demo").first()
    if not qm_user:
        qm_user = User(
            username="tqm_demo",
            email="quality.demo@college-library.edu",
            full_name="Prof. Hiroshi Tanaka [DEMO TQM MANAGER]",
            role=Role.QUALITY,
            is_active=True,
            is_demo=True,
        )
        qm_user.set_password("Quality@123")
        db.session.add(qm_user)

    db.session.flush()

    # 3. Create 12 Fictional Library Members
    member_specs = [
        ("member_demo", "Aarav Sharma [DEMO]", "Computer Science", "Student", "MEM-DEMO-001"),
        ("priya_demo", "Priya Nair [DEMO]", "Mechanical Engineering", "Student", "MEM-DEMO-002"),
        ("rohan_demo", "Rohan Verma [DEMO]", "Electrical Engineering", "Student", "MEM-DEMO-003"),
        ("ananya_demo", "Ananya Iyer [DEMO]", "Management & TQM", "Researcher", "MEM-DEMO-004"),
        ("kabir_demo", "Kabir Mehta [DEMO]", "Data Science", "Student", "MEM-DEMO-005"),
        ("sneha_demo", "Dr. Sneha Kulkarni [DEMO]", "Industrial Engineering", "Faculty", "MEM-DEMO-006"),
        ("vikram_demo", "Vikram Joshi [DEMO]", "Civil Engineering", "Student", "MEM-DEMO-007"),
        ("meera_demo", "Meera Krishnan [DEMO]", "Mathematics", "Student", "MEM-DEMO-008"),
        ("aditya_demo", "Aditya Rao [DEMO]", "Physics", "Researcher", "MEM-DEMO-009"),
        ("divya_demo", "Divya Menon [DEMO]", "Computer Science", "Student", "MEM-DEMO-010"),
        ("siddharth_demo", "Prof. Siddharth Sen [DEMO]", "Economics", "Faculty", "MEM-DEMO-011"),
        ("neha_demo", "Neha Gupta [DEMO]", "Electronics", "Student", "MEM-DEMO-012"),
    ]

    members = []
    for uname, fname, dept, mtype, mem_no in member_specs:
        u = User.query.filter_by(username=uname).first()
        if not u:
            u = User(
                username=uname,
                email=f"{uname}@student.college-library.edu",
                full_name=fname,
                role=Role.MEMBER,
                is_active=True,
                is_demo=True,
            )
            u.set_password("Member@123")
            db.session.add(u)
            db.session.flush()

            m = Member(
                user_id=u.id,
                membership_number=mem_no,
                department=dept,
                member_type=mtype,
                phone="555-0199",
                max_books_allowed=6 if mtype in ("Faculty", "Researcher") else 4,
                status="Active",
                is_demo=True,
                joined_at=now - timedelta(days=90),
            )
            db.session.add(m)
            db.session.flush()
            members.append(m)
        else:
            members.append(u.member_profile)

    # 4. Create 7 Categories
    category_specs = [
        ("Computer Science & AI", "CSAI", "Algorithms, Software Engineering, Machine Learning, and Databases"),
        ("Quality Management & TQM", "TQMM", "Six Sigma, Kaizen, Lean Operations, ISO 9001, and Statistical Quality Control"),
        ("Electrical & Electronics", "ELEC", "Circuit Theory, Embedded Systems, Control Engineering, and Power"),
        ("Mechanical & Industrial", "MECH", "Thermodynamics, Manufacturing Processes, Robotics, and CAD"),
        ("Applied Mathematics", "MATH", "Linear Algebra, Probability, Calculus, and Numerical Methods"),
        ("Data Science & Analytics", "DATA", "Statistical Modeling, Data Mining, Visualization, and Big Data"),
        ("Academic Research & Ethics", "RESE", "Research Methodology, Technical Writing, and Systems Thinking"),
    ]
    categories = {}
    for cname, ccode, cdesc in category_specs:
        cat = Category.query.filter_by(code=ccode).first()
        if not cat:
            cat = Category(name=cname, code=ccode, description=cdesc, is_demo=True)
            db.session.add(cat)
            db.session.flush()
        categories[ccode] = cat

    # 5. Create Publishers & Authors
    publisher_names = [
        "Apex Academic Press [DEMO]",
        "Global Engineering Publications [DEMO]",
        "Meridian University Press [DEMO]",
        "Horizon Technical House [DEMO]",
        "Kaizen Institute Publishing [DEMO]",
    ]
    publishers = []
    for pname in publisher_names:
        pub = Publisher.query.filter_by(name=pname).first()
        if not pub:
            pub = Publisher(name=pname, website="https://example-publisher.edu", is_demo=True)
            db.session.add(pub)
            db.session.flush()
        publishers.append(pub)

    author_names = [
        "Dr. W. Edwards Deming (Fictional Ed.) [DEMO]",
        "Prof. Kaoru Ishikawa (Fictional Ed.) [DEMO]",
        "Dr. Aravind Ramanathan [DEMO]",
        "Prof. Clara Lindqvist [DEMO]",
        "Dr. Marcus Vance [DEMO]",
        "Prof. Kenji Takahashi [DEMO]",
        "Dr. Sophia Al-Mansoor [DEMO]",
        "Prof. David K. Sterling [DEMO]",
        "Dr. Elena Rostova [DEMO]",
        "Prof. Rajeshwar Kulkarni [DEMO]",
        "Dr. Hannah Montgomery [DEMO]",
        "Prof. Liam O'Connor [DEMO]",
    ]
    authors = []
    for aname in author_names:
        auth = Author.query.filter_by(name=aname).first()
        if not auth:
            auth = Author(name=aname, biography="Academic author in engineering and quality management.", is_demo=True)
            db.session.add(auth)
            db.session.flush()
        authors.append(auth)

    # 6. Create 32 Fictional Books & Physical Copies
    book_specs = [
        ("978-0-990001-01-1", "Total Quality Management in Academic Libraries [DEMO]", "TQMM", 0, 4, 2024, "TQM-101", 3),
        ("978-0-990001-02-8", "Kaizen and Continuous Improvement Systems [DEMO]", "TQMM", 1, 4, 2023, "TQM-102", 3),
        ("978-0-990001-03-5", "Statistical Process Control for Service Operations [DEMO]", "TQMM", 5, 4, 2024, "TQM-103", 2),
        ("978-0-990001-04-2", "The PDCA Deming Cycle Handbook [DEMO]", "TQMM", 0, 2, 2022, "TQM-104", 2),
        ("978-0-990001-05-9", "Root Cause Analysis: Fishbone and 5 Whys [DEMO]", "TQMM", 1, 4, 2023, "TQM-105", 2),
        ("978-0-990001-06-6", "Modern Distributed Database Systems [DEMO]", "CSAI", 2, 0, 2024, "CS-201", 3),
        ("978-0-990001-07-3", "Algorithm Design and Complexity Analysis [DEMO]", "CSAI", 3, 0, 2023, "CS-202", 3),
        ("978-0-990001-08-0", "Clean Software Architecture & Testing [DEMO]", "CSAI", 4, 3, 2024, "CS-203", 2),
        ("978-0-990001-09-7", "Operating System Kernels and Concurrency [DEMO]", "CSAI", 6, 1, 2022, "CS-204", 2),
        ("978-0-990001-10-3", "Deep Learning Foundations and Neural Nets [DEMO]", "CSAI", 8, 3, 2024, "CS-205", 3),
        ("978-0-990001-11-0", "Compiler Construction Principles [DEMO]", "CSAI", 7, 2, 2021, "CS-206", 2),
        ("978-0-990001-12-7", "Computer Networks and Zero-Trust Security [DEMO]", "CSAI", 10, 0, 2024, "CS-207", 2),
        ("978-0-990001-13-4", "Applied Regression and Statistical Inference [DEMO]", "DATA", 8, 2, 2023, "DS-301", 2),
        ("978-0-990001-14-1", "Time Series Forecasting and Control Limits [DEMO]", "DATA", 5, 4, 2024, "DS-302", 2),
        ("978-0-990001-15-8", "Exploratory Data Visualization Principles [DEMO]", "DATA", 3, 3, 2023, "DS-303", 2),
        ("978-0-990001-16-5", "Bayesian Data Analysis in Python [DEMO]", "DATA", 11, 0, 2024, "DS-304", 2),
        ("978-0-990001-17-2", "Microcontroller Systems and RTOS Design [DEMO]", "ELEC", 9, 1, 2023, "EE-401", 2),
        ("978-0-990001-18-9", "Digital Signal Processing & Filter Design [DEMO]", "ELEC", 2, 1, 2022, "EE-402", 2),
        ("978-0-990001-19-6", "Modern Feedback Control Systems [DEMO]", "ELEC", 5, 1, 2024, "EE-403", 2),
        ("978-0-990001-20-2", "Power Electronics and Renewable Grids [DEMO]", "ELEC", 9, 3, 2023, "EE-404", 2),
        ("978-0-990001-21-9", "Lean Manufacturing and Six Sigma Green Belt [DEMO]", "MECH", 1, 4, 2024, "ME-501", 2),
        ("978-0-990001-22-6", "Engineering Thermodynamics and Heat Transfer [DEMO]", "MECH", 7, 1, 2022, "ME-502", 2),
        ("978-0-990001-23-3", "Robotics Kinematics and Dynamics [DEMO]", "MECH", 6, 3, 2024, "ME-503", 2),
        ("978-0-990001-24-0", "Finite Element Analysis for Structures [DEMO]", "MECH", 4, 1, 2023, "ME-504", 2),
        ("978-0-990001-25-7", "Linear Algebra and Matrix Computation [DEMO]", "MATH", 8, 2, 2023, "MA-601", 2),
        ("978-0-990001-26-4", "Stochastic Processes and Queueing Theory [DEMO]", "MATH", 11, 2, 2024, "MA-602", 2),
        ("978-0-990001-27-1", "Discrete Mathematics and Graph Theory [DEMO]", "MATH", 3, 0, 2022, "MA-603", 2),
        ("978-0-990001-28-8", "Numerical Optimization Algorithms [DEMO]", "MATH", 6, 2, 2023, "MA-604", 2),
        ("978-0-990001-29-5", "Quantitative Research Methodology [DEMO]", "RESE", 10, 2, 2024, "RS-701", 2),
        ("978-0-990001-30-1", "Academic Technical Writing and Peer Review [DEMO]", "RESE", 10, 0, 2023, "RS-702", 2),
        ("978-0-990001-31-8", "Systems Thinking in Higher Education [DEMO]", "RESE", 0, 2, 2024, "RS-703", 2),
        ("978-0-990001-32-5", "ISO 9001:2015 Quality Auditing in Practice [DEMO]", "TQMM", 1, 4, 2024, "TQM-106", 2),
    ]

    books = []
    all_copies = []
    for idx, (isbn, title, ccode, auth_idx, pub_idx, yr, shelf, num_copies) in enumerate(book_specs, start=1):
        b = Book.query.filter_by(isbn=isbn).first()
        if not b:
            b = Book(
                isbn=isbn,
                title=title,
                subtitle="Demonstration Edition for Academic & TQM Evaluation",
                author_id=authors[auth_idx].id,
                publisher_id=publishers[pub_idx].id,
                category_id=categories[ccode].id,
                publication_year=yr,
                edition="2nd Demo Ed.",
                shelf_location=shelf,
                description=f"Demonstration catalog entry #{idx} covering {categories[ccode].name}.",
                is_archived=False,
                is_demo=True,
            )
            db.session.add(b)
            db.session.flush()

            for cp_num in range(1, num_copies + 1):
                cp_code = f"DEMO-CP-{idx:03d}-{cp_num:02d}"
                # Leave 1 copy unverified out of ~70 to demonstrate realistic 98.6% Inventory Accuracy KPI
                verified = not (idx == 32 and cp_num == 2)
                cp = BookCopy(
                    book_id=b.id,
                    copy_code=cp_code,
                    status="Available",
                    condition="Good" if cp_num > 1 else "New",
                    inventory_verified=verified,
                    last_audit_date=now - timedelta(days=3),
                    is_demo=True,
                )
                db.session.add(cp)
                db.session.flush()
                all_copies.append(cp)
        else:
            all_copies.extend(b.copies.all())
        books.append(b)

    # 7. Seed Loans (Returned on time, Returned late with fine, Active on time, Active Overdue)
    loan_configs = [
        # (copy_index, member_index, days_ago_issued, duration_days, returned_days_ago, proc_sec)
        (0, 0, 35, 14, 23, 32.5),
        (2, 1, 32, 14, 19, 38.0),
        (4, 2, 28, 14, 10, 41.2),  # Returned 4 days late -> Fine
        (6, 3, 26, 14, 14, 29.8),
        (8, 4, 24, 14, 11, 36.4),
        (10, 5, 22, 14, 9, 34.0),
        (12, 6, 20, 14, 3, 44.5),  # Returned 3 days late -> Fine
        (14, 7, 18, 14, 6, 31.0),
        (16, 8, 15, 14, 3, 39.2),
        (18, 9, 12, 14, 2, 33.7),
        (20, 10, 10, 14, 1, 35.1),
        # Active Overdue loans (returned_days_ago=None)
        (1, 0, 19, 14, None, 40.0),  # 5 days overdue currently
        (3, 1, 17, 14, None, 37.5),  # 3 days overdue currently
        # Active On-Time loans
        (5, 2, 8, 14, None, 30.2),
        (7, 3, 6, 14, None, 33.8),
        (9, 4, 5, 14, None, 28.9),
        (11, 5, 4, 14, None, 36.0),
        (13, 6, 3, 14, None, 34.6),
        (15, 7, 2, 14, None, 31.4),
    ]

    for cp_idx, mem_idx, issued_ago, dur, ret_ago, proc_sec in loan_configs:
        if cp_idx >= len(all_copies) or mem_idx >= len(members):
            continue
        copy = all_copies[cp_idx]
        member = members[mem_idx]
        issue_dt = now - timedelta(days=issued_ago)
        due_dt = issue_dt + timedelta(days=dur)
        ret_dt = (now - timedelta(days=ret_ago)) if ret_ago is not None else None
        status = "Returned" if ret_dt else ("Overdue" if now > due_dt else "Active")

        if not ret_dt:
            copy.status = "Issued"

        ln = Loan(
            copy_id=copy.id,
            member_id=member.id,
            issued_by_id=admin_user.id,
            issue_date=issue_dt,
            due_date=due_dt,
            return_date=ret_dt,
            status=status,
            return_condition="Good" if ret_dt else None,
            processing_time_seconds=proc_sec,
            standardized_checklist_verified=True,
            notes="[DEMO] Standardized circulation record",
            is_demo=True,
        )
        db.session.add(ln)
        db.session.flush()

        if ret_dt and ret_dt > due_dt:
            overdue_days = (ret_dt - due_dt).days
            fine_amt = round(overdue_days * 2.0, 2)
            db.session.add(
                Fine(
                    loan_id=ln.id,
                    member_id=member.id,
                    amount=fine_amt,
                    reason=f"[DEMO] Overdue return ({overdue_days} days late)",
                    status="Unpaid" if cp_idx == 4 else "Paid",
                    created_at=ret_dt,
                    paid_at=ret_dt if cp_idx != 4 else None,
                    is_demo=True,
                )
            )

    # 8. Seed Sample Reservations
    res_specs = [
        (books[0].id, members[2].id, "Pending", 1, "[DEMO] Waiting for next copy of TQM textbook"),
        (books[5].id, members[4].id, "Ready", 1, "[DEMO] Reserved for database project"),
        (books[9].id, members[1].id, "Pending", 1, "[DEMO] Needed for neural networks lab"),
    ]
    for b_id, m_id, r_status, q_pos, r_notes in res_specs:
        db.session.add(
            Reservation(
                book_id=b_id,
                member_id=m_id,
                status=r_status,
                queue_position=q_pos,
                notes=r_notes,
                created_at=now - timedelta(days=4),
                is_demo=True,
            )
        )

    # 9. Seed Sample Customer Feedback (1-5 ratings across categories over time)
    feedback_specs = [
        (0, books[0].id, "Book Availability", 5, "[DEMO] Excellent TQM collection and quick shelf lookup.", False, 25),
        (1, books[5].id, "Staff Service", 5, "[DEMO] Librarian was very helpful with standardized checkout.", False, 22),
        (2, books[6].id, "Book Availability", 3, "[DEMO] High-demand CS books often run out during exam week.", True, 20),
        (3, books[1].id, "Digital Access", 4, "[DEMO] Online catalog search and copy tracking is very clear.", False, 18),
        (4, None, "Waiting Time", 4, "[DEMO] Issue desk queue moved quickly today (< 40 seconds).", False, 15),
        (5, books[9].id, "Book Availability", 2, "[DEMO] Needed more copies of Deep Learning Foundations.", True, 12),
        (6, None, "Cleanliness", 5, "[DEMO] Reading hall is spotless and well organized.", False, 10),
        (7, books[2].id, "Staff Service", 5, "[DEMO] Great guidance on statistical quality control references.", False, 8),
        (8, None, "Digital Access", 4, "[DEMO] Reservation alert notifications worked as expected.", False, 6),
        (9, books[3].id, "Study Environment", 5, "[DEMO] Quiet zones are well maintained.", False, 4),
        (10, books[7].id, "Waiting Time", 4, "[DEMO] Fast return inspection and instant receipt.", False, 2),
        (11, books[0].id, "Staff Service", 5, "[DEMO] Outstanding academic support.", False, 1),
    ]
    for m_idx, b_id, cat, rating, comment, recurring, days_ago in feedback_specs:
        db.session.add(
            Feedback(
                member_id=members[m_idx].id,
                book_id=b_id,
                category=cat,
                rating=rating,
                comments=comment,
                is_recurring_concern=recurring,
                created_at=now - timedelta(days=days_ago),
                is_demo=True,
            )
        )

    # 10. Seed Sample Complaints structured for clear 80/20 Pareto Analysis
    # Categories: Book Availability (6), Waiting Time (4), Digital Access (2), Damaged Book Copy (1), Environment & Noise (1) -> Total 14
    # Top 2 categories = 10/14 = 71.4% (Vital Few!)
    complaint_specs = [
        (0, "Shortage of Core AI & Database Textbooks During Midterms [DEMO]", "Book Availability", "High", "All copies of core CS textbooks are checked out with long waitlists.", "Resolved", 28, 18.5),
        (1, "Insufficient Copies of Deep Learning Reference [DEMO]", "Book Availability", "Medium", "Only 3 copies available for a class of 60 students.", "Resolved", 25, 24.0),
        (2, "High-Demand TQM Handbook Frequently Unavailable [DEMO]", "Book Availability", "Medium", "Need additional reserve copies for project groups.", "Resolved", 22, 30.0),
        (3, "Delayed Return of Reserved Algorithms Textbook [DEMO]", "Book Availability", "High", "Copy held overdue by previous borrower blocking reservation.", "Resolved", 19, 16.0),
        (4, "Misplaced Reference Copy on Shelf CS-202 [DEMO]", "Book Availability", "Medium", "Catalog showed Available but copy was reshelved on wrong row.", "Resolved", 15, 12.0),
        (5, "Request for Extra Exam-Week Reference Copies [DEMO]", "Book Availability", "Low", "Would like 2-hour reference-only copies during finals.", "In Progress", 5, None),
        (6, "Peak-Hour Queue at Circulation Desk at 1:00 PM [DEMO]", "Waiting Time", "Medium", "Lunch hour return and issue queue took over 8 minutes.", "Resolved", 24, 28.0),
        (7, "Slow Manual Verification Before Standardized Checklist [DEMO]", "Waiting Time", "Medium", "Checkout took longer when barcode label was smudged.", "Resolved", 20, 22.0),
        (8, "Wait Time for Reservation Pickup Confirmation [DEMO]", "Waiting Time", "Low", "Took several hours after book return to receive pickup alert.", "Resolved", 14, 14.5),
        (9, "Morning Rush Delay at Return Counter [DEMO]", "Waiting Time", "Low", "Single counter open at 9:00 AM caused minor bottleneck.", "Open", 3, None),
        (10, "Wi-Fi Drop in East Reading Wing [DEMO]", "Digital Access", "Medium", "Intermittent connectivity near shelf MA-601.", "Resolved", 17, 36.0),
        (11, "Catalog Terminal Timeout on Kiosk #2 [DEMO]", "Digital Access", "Low", "Search session resets too quickly.", "Resolved", 11, 20.0),
        (12, "Loose Binding on Thermodynamics Copy #2 [DEMO]", "Damaged Book Copy", "Low", "Pages 45-60 need rebinding by maintenance.", "Resolved", 9, 40.0),
        (13, "Group Discussion Noise Near Quiet Carrels [DEMO]", "Environment & Noise", "Low", "Need clearer quiet-zone signage on 2nd floor.", "Resolved", 7, 15.0),
    ]

    seeded_complaints = []
    for m_idx, title, cat, sev, desc, status, days_ago, res_hours in complaint_specs:
        created_dt = now - timedelta(days=days_ago)
        resolved_dt = (created_dt + timedelta(hours=res_hours)) if res_hours is not None else None
        cmp_obj = Complaint(
            member_id=members[m_idx % len(members)].id,
            title=title,
            category=cat,
            severity=sev,
            description=desc,
            status=status,
            resolution_notes="[DEMO] Addressed via TQM corrective action and standardized SOP update." if resolved_dt else None,
            created_at=created_dt,
            resolved_at=resolved_dt,
            resolved_by_id=qm_user.id if resolved_dt else None,
            is_demo=True,
        )
        db.session.add(cmp_obj)
        db.session.flush()
        seeded_complaints.append(cmp_obj)

    # 11. Seed Root-Cause Analyses (Fishbone 6 Categories + 5 Whys)
    rca1 = RootCauseAnalysis(
        complaint_id=seeded_complaints[0].id,
        problem_title="[DEMO] High Unavailability of Core Textbooks During Exam Weeks",
        fishbone_people="Students hold onto core textbooks until the final day; faculty syllabus demand spikes simultaneously.",
        fishbone_processes="No automated demand forecasting or exam-week short-loan rotation policy.",
        fishbone_technology="Reservation queue alerts were previously checked manually instead of triggered on return.",
        fishbone_materials="Only 2-3 physical copies stocked for courses with 60+ enrolled students.",
        fishbone_environment="Peak exam period creates concentrated demand within a 10-day window.",
        fishbone_policies="Flat 14-day loan duration applied even to high-demand exam reference titles.",
        why_1="Students cannot find available copies of core CS and TQM textbooks before exams.",
        why_2="All existing copies are checked out for full 14-day cycles with overdue delays.",
        why_3="Overdue notifications and reservation promotions were not triggered automatically upon return.",
        why_4="Circulation workflow lacked a standardized return-to-reservation promotion rule.",
        why_5="Absence of a closed-loop PDCA inventory utilization review prior to midterms.",
        identified_root_cause="[DEMO] Lack of automated reservation queue promotion upon return combined with static copy allocation for high-demand courses.",
        created_by_id=qm_user.id,
        created_at=now - timedelta(days=20),
        is_demo=True,
    )
    rca2 = RootCauseAnalysis(
        complaint_id=seeded_complaints[6].id,
        problem_title="[DEMO] Circulation Desk Waiting Time Spikes During Peak Hours",
        fishbone_people="Single librarian handling both new registrations, fine disputes, and book checkouts.",
        fishbone_processes="Issue and return steps were ad-hoc without a pre-verified 3-step checklist.",
        fishbone_technology="Manual copy lookup when copy code wasn't pre-filtered by availability.",
        fishbone_materials="Worn spine labels on older copies required manual ISBN entry.",
        fishbone_environment="12:30 PM - 1:30 PM class break creates 4x normal foot traffic.",
        fishbone_policies="Fine payment disputes handled at the same express checkout counter.",
        why_1="Member waiting time at the circulation desk exceeded 5 minutes during lunch hour.",
        why_2="Average transaction time spiked above 75 seconds during complex returns.",
        why_3="Staff spent time searching for available copy codes and resolving fine questions mid-queue.",
        why_4="No standardized checkout SOP checklist or pre-filtered available-copy selector existed.",
        why_5="Circulation process had not been standardized under TQM employee involvement guidelines.",
        identified_root_cause="[DEMO] Unstandardized circulation desk workflow and mixing fine dispute resolution with express book issue/return.",
        created_by_id=qm_user.id,
        created_at=now - timedelta(days=16),
        is_demo=True,
    )
    db.session.add_all([rca1, rca2])
    db.session.flush()

    # 12. Seed Kaizen Continuous Improvement Register (Completed on time, In Progress, Open, Overdue)
    kaizen_specs = [
        (
            rca1.id,
            "[DEMO] Delayed reservation fulfillment after book return",
            "Manual reservation matching caused 12-24h pickup delays",
            "Automate reservation queue promotion and member notification immediately inside the return transaction",
            "Prof. Hiroshi Tanaka",
            "High",
            now - timedelta(days=10),
            now - timedelta(days=12),
            "Completed",
            "Reduce reservation notification lag from 18 hours to 0 seconds (instant)",
            "Achieved instant 0-second automatic reservation promotion on book return.",
            "[DEMO] Standardized in library_service.return_book_copy().",
        ),
        (
            rca2.id,
            "[DEMO] High circulation desk service processing time (>60s)",
            "Ad-hoc checkout steps and manual copy availability checks",
            "Implement standardized 3-point TQM checkout checklist and pre-filtered Available Copy selector",
            "Dr. Eleanor Vance",
            "High",
            now - timedelta(days=5),
            now - timedelta(days=7),
            "Completed",
            "Bring average book issue processing time below 45.0 seconds",
            "Average processing time reduced to ~35.2 seconds across recorded loans.",
            "[DEMO] Verified via SPC Control Chart.",
        ),
        (
            rca1.id,
            "[DEMO] Shelf misplacement reducing inventory accuracy",
            "Unverified daily reshelving in CS and TQM sections",
            "Conduct weekly barcode shelf audit and track copy-level inventory_verified flag",
            "Aarav Sharma (Student Asst.)",
            "Medium",
            now + timedelta(days=7),
            None,
            "In Progress",
            "Maintain catalog Inventory Accuracy KPI >= 98.0%",
            "Currently at 98.6% verified across 70+ physical copies.",
            "[DEMO] Weekly Friday shelf audit active.",
        ),
        (
            None,
            "[DEMO] Exam-week shortage of high-demand AI & TQM titles",
            "Static copy count for courses with >50 students",
            "Procure 2 additional copies for top 3 Pareto-identified high-demand titles",
            "Library Acquisition Committee",
            "Medium",
            now + timedelta(days=14),
            None,
            "Open",
            "Increase Book Availability Rate above 80% during midterms",
            None,
            None,
        ),
        (
            None,
            "[DEMO] Replace worn spine labels on older Mechanical Engineering copies",
            "Thermal paper labels faded after 2 years of handling",
            "Apply laminated polyester copy code labels on ME-501 through ME-504",
            "Technical Services Team",
            "Low",
            now - timedelta(days=2),
            None,
            "Open",  # Past target date -> dynamically displays as Overdue!
            "Zero scanner read failures at circulation counter",
            None,
            "[DEMO] Waiting on laminated label stock delivery.",
        ),
    ]
    for r_id, prob, root, act, owner, prio, target_dt, comp_dt, st, exp, meas, notes in kaizen_specs:
        db.session.add(
            ImprovementAction(
                rca_id=r_id,
                problem_description=prob,
                identified_root_cause=root,
                proposed_corrective_action=act,
                assigned_owner=owner,
                priority=prio,
                target_completion_date=target_dt,
                completed_date=comp_dt,
                status=st,
                expected_result=exp,
                measured_result=meas,
                completion_notes=notes,
                created_at=now - timedelta(days=18),
                is_demo=True,
            )
        )

    # 13. Seed PDCA Cycles
    pdca1 = PDCACycle(
        title="[DEMO] Cycle 1: Circulation Checkout Time Reduction via Standardized SOP",
        current_phase="Act",
        problem_statement="Peak-hour book issue transactions averaged 68 seconds, causing student queues and complaints.",
        baseline_metric="68.0 seconds average issue processing time",
        target_metric="<= 45.0 seconds average issue processing time",
        measurement_method="Timestamped processing_time_seconds logged per Loan transaction in SPC chart",
        intervention_details="Deployed pre-filtered available copy dropdown and mandatory 3-point TQM checkout verification.",
        assigned_owner="Dr. Eleanor Vance",
        implementation_start_date=now - timedelta(days=25),
        implementation_end_date=now - timedelta(days=7),
        measured_outcome="35.2 seconds average processing time across 19 loan transactions (48% reduction).",
        target_achieved=True,
        comparison_analysis="Measured 35.2s beats the 45.0s target by 9.8s and remains within 3-sigma statistical control.",
        standardization_action="Embedded mandatory standardized_checklist_verified control into IssueBookForm and library_service.",
        next_cycle_recommendations="Initiate Cycle 2 focusing on automated overdue reminders to reduce overdue loan rate.",
        is_demo=True,
    )
    pdca2 = PDCACycle(
        title="[DEMO] Cycle 2: Overdue Loan Rate Reduction via Proactive Due-Date Notifications",
        current_phase="Check",
        problem_statement="Overdue loan rate reached 24% during the previous semester, blocking book reservations.",
        baseline_metric="24.0% historical overdue loan rate",
        target_metric="<= 12.0% overdue loan rate",
        measurement_method="Weekly cohort overdue percentage tracked on the Overdue-Loan Rate KPI and SPC chart",
        intervention_details="Automated instant due-date notification upon book issue and clear grace-period/fine policy visibility.",
        assigned_owner="Prof. Hiroshi Tanaka",
        implementation_start_date=now - timedelta(days=14),
        implementation_end_date=now - timedelta(days=1),
        measured_outcome="Current cumulative overdue rate reduced to 21.1% (4 overdue out of 19 total demo loans); recent cohorts trending lower.",
        target_achieved=False,
        comparison_analysis="Improved from 24.0% baseline to 21.1%, but still requires 48-hour pre-due reminder batch to reach <= 12.0% target.",
        standardization_action="Keep issue-time due date notifications active; expand to 2-day advance alerts in next iteration.",
        next_cycle_recommendations="Add SMS/Email 48h pre-due reminder hook in Cycle 3.",
        is_demo=True,
    )
    db.session.add_all([pdca1, pdca2])

    # 14. Seed Staff Suggestions (Standardization & Employee Involvement)
    db.session.add_all(
        [
            StaffSuggestion(
                submitted_by_id=admin_user.id,
                title="[DEMO] Color-Coded Shelf Tags by Academic Category",
                process_area="Inventory & Shelf Auditing",
                suggestion_details="Use distinct color spine bands for CSAI, TQMM, ELEC, and MECH so mis-shelved books are spotted immediately during walkthroughs.",
                expected_benefit="Cut weekly shelf audit time by 40% and keep Inventory Accuracy above 99%.",
                status="Approved & Standardized",
                review_notes="Approved by Quality Manager; rolled out across rows A-101 to RS-703.",
                is_demo=True,
            ),
            StaffSuggestion(
                submitted_by_id=qm_user.id,
                title="[DEMO] Express Return Drop-Box Inspection Checklist",
                process_area="Circulation & Issue/Return",
                suggestion_details="Standardize a 4-item physical condition check (cover, spine, water damage, markings) upon every book return.",
                expected_benefit="Early detection of damaged copies before they are re-issued to the next student.",
                status="Approved & Standardized",
                review_notes="Integrated into the ReturnBookForm condition selector and auto-maintenance routing.",
                is_demo=True,
            ),
        ]
    )

    # 15. Seed Audit Log entry for Demo Seeding
    db.session.add(
        AuditLog(
            actor_id=admin_user.id,
            actor_username=admin_user.username,
            action="SEED_DEMO_DATA",
            entity_type="System",
            entity_id="DEMO-BATCH",
            details="Populated labeled demonstration dataset (32 books, 12 members, 19 loans, 14 complaints, 12 feedbacks, 2 RCAs, 5 Kaizen actions, 2 PDCA cycles).",
            ip_address="127.0.0.1",
            is_demo=True,
        )
    )

    db.session.commit()
    return {
        "books": Book.query.filter_by(is_demo=True).count(),
        "copies": BookCopy.query.filter_by(is_demo=True).count(),
        "members": Member.query.filter_by(is_demo=True).count(),
        "loans": Loan.query.filter_by(is_demo=True).count(),
        "complaints": Complaint.query.filter_by(is_demo=True).count(),
        "feedbacks": Feedback.query.filter_by(is_demo=True).count(),
    }


if __name__ == "__main__":
    from app import create_app

    app = create_app()
    with app.app_context():
        db.create_all()
        summary = seed_demo_data(reset_existing_demo=True)
        print("Demo data seeded successfully:", summary)
