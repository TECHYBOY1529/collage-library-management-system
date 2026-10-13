from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role:
    ADMIN = "admin"
    MEMBER = "member"
    QUALITY = "quality_manager"
    ALL = [ADMIN, MEMBER, QUALITY]


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(32), nullable=False, default=Role.MEMBER, index=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    member_profile = db.relationship(
        "Member", backref="user", uselist=False, cascade="all, delete-orphan"
    )
    notifications = db.relationship(
        "Notification", backref="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Member(db.Model):
    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    membership_number = db.Column(db.String(32), unique=True, nullable=False, index=True)
    department = db.Column(db.String(100), nullable=False, default="General")
    member_type = db.Column(db.String(32), nullable=False, default="Student")  # Student, Faculty, Researcher
    phone = db.Column(db.String(32), nullable=True)
    max_books_allowed = db.Column(db.Integer, default=4, nullable=False)
    status = db.Column(db.String(24), default="Active", nullable=False, index=True)  # Active, Suspended
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    joined_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    loans = db.relationship("Loan", backref="member", lazy="dynamic")
    reservations = db.relationship("Reservation", backref="member", lazy="dynamic")
    fines = db.relationship("Fine", backref="member", lazy="dynamic")
    feedbacks = db.relationship("Feedback", backref="member", lazy="dynamic")
    complaints = db.relationship("Complaint", backref="member", lazy="dynamic")


class Author(db.Model):
    __tablename__ = "authors"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    biography = db.Column(db.Text, nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    books = db.relationship("Book", backref="author", lazy="dynamic")


class Publisher(db.Model):
    __tablename__ = "publishers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    website = db.Column(db.String(200), nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    books = db.relationship("Book", backref="publisher", lazy="dynamic")


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    books = db.relationship("Book", backref="category", lazy="dynamic")


class Book(db.Model):
    __tablename__ = "books"

    id = db.Column(db.Integer, primary_key=True)
    isbn = db.Column(db.String(32), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False, index=True)
    subtitle = db.Column(db.String(255), nullable=True)
    author_id = db.Column(db.Integer, db.ForeignKey("authors.id"), nullable=False, index=True)
    publisher_id = db.Column(db.Integer, db.ForeignKey("publishers.id"), nullable=False, index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False, index=True)
    publication_year = db.Column(db.Integer, nullable=True)
    edition = db.Column(db.String(32), nullable=True, default="1st")
    shelf_location = db.Column(db.String(50), nullable=False, default="A-101")
    description = db.Column(db.Text, nullable=True)
    is_archived = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    copies = db.relationship(
        "BookCopy", backref="book", lazy="dynamic", cascade="all, delete-orphan"
    )
    reservations = db.relationship(
        "Reservation", backref="book", lazy="dynamic", cascade="all, delete-orphan"
    )
    feedbacks = db.relationship("Feedback", backref="book", lazy="dynamic")

    @property
    def total_copies_count(self) -> int:
        return self.copies.filter(BookCopy.status != "Archived").count()

    @property
    def available_copies_count(self) -> int:
        return self.copies.filter_by(status="Available").count()


class BookCopy(db.Model):
    __tablename__ = "book_copies"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(
        db.Integer, db.ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    copy_code = db.Column(db.String(64), unique=True, nullable=False, index=True)
    status = db.Column(
        db.String(24), default="Available", nullable=False, index=True
    )  # Available, Issued, Reserved, Maintenance, Lost, Archived
    condition = db.Column(db.String(32), default="Good", nullable=False)  # New, Good, Fair, Worn, Damaged
    inventory_verified = db.Column(db.Boolean, default=True, nullable=False)
    last_audit_date = db.Column(db.DateTime, default=utcnow, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    loans = db.relationship("Loan", backref="copy", lazy="dynamic")


class FinePolicy(db.Model):
    __tablename__ = "fine_policies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False, default="Standard Policy")
    loan_duration_days = db.Column(db.Integer, default=14, nullable=False)
    fine_per_day = db.Column(db.Float, default=2.00, nullable=False)
    grace_period_days = db.Column(db.Integer, default=0, nullable=False)
    max_fine_cap = db.Column(db.Float, default=100.00, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class Loan(db.Model):
    __tablename__ = "loans"

    id = db.Column(db.Integer, primary_key=True)
    copy_id = db.Column(db.Integer, db.ForeignKey("book_copies.id"), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, index=True)
    issued_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    issue_date = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    due_date = db.Column(db.DateTime, nullable=False, index=True)
    return_date = db.Column(db.DateTime, nullable=True, index=True)
    status = db.Column(
        db.String(24), default="Active", nullable=False, index=True
    )  # Active, Returned, Overdue
    return_condition = db.Column(db.String(32), nullable=True)
    processing_time_seconds = db.Column(db.Float, default=42.0, nullable=False)
    standardized_checklist_verified = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)

    fine = db.relationship("Fine", backref="loan", uselist=False, cascade="all, delete-orphan")
    issued_by = db.relationship("User", foreign_keys=[issued_by_id])

    @property
    def is_overdue(self) -> bool:
        now = utcnow()
        if self.status in ("Active", "Overdue") and self.return_date is None:
            return now > self.due_date
        if self.return_date is not None:
            return self.return_date > self.due_date
        return False

    @property
    def days_overdue(self) -> int:
        ref_date = self.return_date or utcnow()
        if ref_date > self.due_date:
            delta = ref_date - self.due_date
            return max(1, delta.days + (1 if delta.seconds > 0 and delta.days == 0 else 0))
        return 0


class Reservation(db.Model):
    __tablename__ = "reservations"

    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, index=True)
    status = db.Column(
        db.String(24), default="Pending", nullable=False, index=True
    )  # Pending, Ready, Fulfilled, Cancelled
    queue_position = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    fulfilled_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)


class Fine(db.Model):
    __tablename__ = "fines"

    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey("loans.id"), unique=True, nullable=False, index=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, index=True)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    reason = db.Column(db.String(120), nullable=False, default="Overdue Return")
    status = db.Column(
        db.String(24), default="Unpaid", nullable=False, index=True
    )  # Unpaid, Paid, Waived
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    paid_at = db.Column(db.DateTime, nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)


class Feedback(db.Model):
    __tablename__ = "feedbacks"

    CATEGORIES = [
        "Book Availability",
        "Staff Service",
        "Waiting Time",
        "Digital Access",
        "Cleanliness",
        "Study Environment",
        "Other",
    ]

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, index=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=True, index=True)
    category = db.Column(db.String(64), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # 1 to 5
    comments = db.Column(db.Text, nullable=False)
    is_recurring_concern = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)


class Complaint(db.Model):
    __tablename__ = "complaints"

    CATEGORIES = [
        "Book Availability",
        "Staff Service",
        "Waiting Time",
        "Digital Access",
        "Cleanliness",
        "Fine Dispute",
        "Damaged Book Copy",
        "Environment & Noise",
    ]

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    category = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(
        db.String(24), default="Medium", nullable=False
    )  # Low, Medium, High, Critical
    description = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.String(32), default="Open", nullable=False, index=True
    )  # Open, In Progress, Resolved, Closed
    resolution_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True, index=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)

    root_cause_analyses = db.relationship(
        "RootCauseAnalysis", backref="complaint", lazy="dynamic", cascade="all, delete-orphan"
    )

    @property
    def resolution_hours(self):
        if self.resolved_at and self.created_at:
            delta = self.resolved_at - self.created_at
            return round(max(0.1, delta.total_seconds() / 3600.0), 2)
        return None


class RootCauseAnalysis(db.Model):
    __tablename__ = "root_cause_analyses"

    id = db.Column(db.Integer, primary_key=True)
    complaint_id = db.Column(db.Integer, db.ForeignKey("complaints.id"), nullable=True, index=True)
    problem_title = db.Column(db.String(200), nullable=False)
    # Fishbone (Ishikawa) 6M / Library Categories
    fishbone_people = db.Column(db.Text, nullable=True)
    fishbone_processes = db.Column(db.Text, nullable=True)
    fishbone_technology = db.Column(db.Text, nullable=True)
    fishbone_materials = db.Column(db.Text, nullable=True)
    fishbone_environment = db.Column(db.Text, nullable=True)
    fishbone_policies = db.Column(db.Text, nullable=True)
    # 5 Whys Workflow
    why_1 = db.Column(db.String(255), nullable=False)
    why_2 = db.Column(db.String(255), nullable=True)
    why_3 = db.Column(db.String(255), nullable=True)
    why_4 = db.Column(db.String(255), nullable=True)
    why_5 = db.Column(db.String(255), nullable=True)
    identified_root_cause = db.Column(db.Text, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)

    created_by = db.relationship("User", foreign_keys=[created_by_id])
    improvement_actions = db.relationship("ImprovementAction", backref="rca", lazy="dynamic")


class ImprovementAction(db.Model):
    """Kaizen Continuous Improvement Register."""
    __tablename__ = "improvement_actions"

    id = db.Column(db.Integer, primary_key=True)
    rca_id = db.Column(db.Integer, db.ForeignKey("root_cause_analyses.id"), nullable=True)
    problem_description = db.Column(db.Text, nullable=False)
    identified_root_cause = db.Column(db.Text, nullable=False)
    proposed_corrective_action = db.Column(db.Text, nullable=False)
    assigned_owner = db.Column(db.String(120), nullable=False)
    priority = db.Column(
        db.String(24), default="Medium", nullable=False
    )  # Low, Medium, High, Critical
    target_completion_date = db.Column(db.DateTime, nullable=False, index=True)
    completed_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(
        db.String(32), default="Open", nullable=False, index=True
    )  # Open, In Progress, Completed
    expected_result = db.Column(db.Text, nullable=False)
    measured_result = db.Column(db.Text, nullable=True)
    completion_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)

    @property
    def computed_display_status(self) -> str:
        if self.status == "Completed":
            return "Completed"
        if utcnow() > self.target_completion_date:
            return "Overdue"
        return self.status

    @property
    def is_completed_on_time(self):
        if self.status == "Completed" and self.completed_date:
            return self.completed_date <= self.target_completion_date
        return None


class PDCACycle(db.Model):
    """Dedicated Plan-Do-Check-Act (Deming Cycle) Quality Module."""
    __tablename__ = "pdca_cycles"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    current_phase = db.Column(
        db.String(16), default="Plan", nullable=False, index=True
    )  # Plan, Do, Check, Act, Completed
    # PLAN
    problem_statement = db.Column(db.Text, nullable=False)
    baseline_metric = db.Column(db.String(160), nullable=False)
    target_metric = db.Column(db.String(160), nullable=False)
    measurement_method = db.Column(db.String(200), nullable=False)
    # DO
    intervention_details = db.Column(db.Text, nullable=True)
    assigned_owner = db.Column(db.String(120), nullable=False)
    implementation_start_date = db.Column(db.DateTime, nullable=True)
    implementation_end_date = db.Column(db.DateTime, nullable=True)
    # CHECK
    measured_outcome = db.Column(db.Text, nullable=True)
    target_achieved = db.Column(db.Boolean, nullable=True)
    comparison_analysis = db.Column(db.Text, nullable=True)
    # ACT
    standardization_action = db.Column(db.Text, nullable=True)
    next_cycle_recommendations = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)


class StaffSuggestion(db.Model):
    """Employee Involvement & Standardization Suggestions (Phase 5H)."""
    __tablename__ = "staff_suggestions"

    id = db.Column(db.Integer, primary_key=True)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    process_area = db.Column(
        db.String(80), nullable=False, default="Circulation & Issue/Return"
    )
    suggestion_details = db.Column(db.Text, nullable=False)
    expected_benefit = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.String(32), default="Submitted", nullable=False
    )  # Submitted, Under Review, Approved & Standardized, Deferred
    review_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)

    submitted_by = db.relationship("User", foreign_keys=[submitted_by_id])


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(
        db.String(32), default="info", nullable=False
    )  # due_date, complaint_update, reservation, fine, system
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    actor_username = db.Column(db.String(64), nullable=False, default="system")
    action = db.Column(db.String(80), nullable=False, index=True)
    entity_type = db.Column(db.String(64), nullable=False, index=True)
    entity_id = db.Column(db.String(64), nullable=True)
    details = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    is_demo = db.Column(db.Boolean, default=False, nullable=False, index=True)

    actor = db.relationship("User", foreign_keys=[actor_id])
