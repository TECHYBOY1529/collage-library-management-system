from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    PasswordField,
    SelectField,
    IntegerField,
    FloatField,
    TextAreaField,
    BooleanField,
    DateField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional, EqualTo, ValidationError
import re
from app.models import Feedback, Complaint


def validate_email_format(form, field):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    if not re.match(pattern, field.data or ""):
        raise ValidationError("Invalid email address format.")


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField("Password", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField("Email Address", validators=[DataRequired(), Length(max=120), validate_email_format])
    full_name = StringField("Full Name", validators=[DataRequired(), Length(min=2, max=120)])
    department = StringField("Department / Faculty", validators=[DataRequired(), Length(min=2, max=100)])
    member_type = SelectField(
        "Member Type",
        choices=[("Student", "Student"), ("Faculty", "Faculty"), ("Researcher", "Researcher")],
        validators=[DataRequired()],
    )
    phone = StringField("Phone Number", validators=[Optional(), Length(max=32)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class BookForm(FlaskForm):
    isbn = StringField("ISBN", validators=[DataRequired(), Length(min=5, max=32)])
    title = StringField("Title", validators=[DataRequired(), Length(min=2, max=200)])
    subtitle = StringField("Subtitle", validators=[Optional(), Length(max=255)])
    author_id = SelectField("Author", coerce=int, validators=[DataRequired()])
    publisher_id = SelectField("Publisher", coerce=int, validators=[DataRequired()])
    category_id = SelectField("Category", coerce=int, validators=[DataRequired()])
    publication_year = IntegerField(
        "Publication Year", validators=[Optional(), NumberRange(min=1800, max=2100)]
    )
    edition = StringField("Edition", validators=[Optional(), Length(max=32)], default="1st")
    shelf_location = StringField("Shelf Location", validators=[DataRequired(), Length(max=50)], default="A-101")
    initial_copies = IntegerField(
        "Initial Physical Copies",
        validators=[Optional(), NumberRange(min=0, max=50)],
        default=2,
    )
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])


class IssueBookForm(FlaskForm):
    copy_id = SelectField("Physical Book Copy", coerce=int, validators=[DataRequired()])
    member_id = SelectField("Library Member", coerce=int, validators=[DataRequired()])
    loan_days = IntegerField(
        "Loan Duration (Days)", validators=[DataRequired(), NumberRange(min=1, max=90)], default=14
    )
    processing_time_seconds = FloatField(
        "Service Processing Time (Seconds)",
        validators=[DataRequired(), NumberRange(min=1.0, max=3600.0)],
        default=35.0,
    )
    standardized_checklist_verified = BooleanField(
        "Standardized Issue Checklist Verified (ID Checked, Physical Condition Inspected, Due Date Stamped)",
        default=True,
        validators=[DataRequired(message="Standardized TQM checkout verification is required.")],
    )
    notes = StringField("Circulation Notes", validators=[Optional(), Length(max=255)])


class ReturnBookForm(FlaskForm):
    return_condition = SelectField(
        "Returned Copy Condition",
        choices=[
            ("New", "New"),
            ("Good", "Good"),
            ("Fair", "Fair"),
            ("Worn", "Worn"),
            ("Damaged", "Damaged"),
        ],
        validators=[DataRequired()],
    )
    notes = StringField("Return Inspection Notes", validators=[Optional(), Length(max=255)])


class FinePolicyForm(FlaskForm):
    loan_duration_days = IntegerField(
        "Default Loan Duration (Days)", validators=[DataRequired(), NumberRange(min=1, max=90)]
    )
    fine_per_day = FloatField(
        "Overdue Fine Per Day ($)", validators=[DataRequired(), NumberRange(min=0.0, max=100.0)]
    )
    grace_period_days = IntegerField(
        "Grace Period (Days)", validators=[Optional(), NumberRange(min=0, max=30)], default=0
    )
    max_fine_cap = FloatField(
        "Maximum Fine Cap ($)", validators=[DataRequired(), NumberRange(min=1.0, max=1000.0)]
    )


class FeedbackForm(FlaskForm):
    category = SelectField(
        "Quality Dimension / Category",
        choices=[(c, c) for c in Feedback.CATEGORIES],
        validators=[DataRequired()],
    )
    rating = SelectField(
        "Satisfaction Rating (1 = Poor, 5 = Excellent)",
        coerce=int,
        choices=[
            (5, "5 - Excellent"),
            (4, "4 - Very Good"),
            (3, "3 - Satisfactory"),
            (2, "2 - Needs Improvement"),
            (1, "1 - Dissatisfied"),
        ],
        validators=[DataRequired(), NumberRange(min=1, max=5)],
    )
    book_id = SelectField("Related Book (Optional)", coerce=int, validators=[Optional()])
    comments = TextAreaField("Detailed Feedback", validators=[DataRequired(), Length(min=5, max=1500)])
    is_recurring_concern = BooleanField("This is a recurring issue I have experienced multiple times")


class ComplaintForm(FlaskForm):
    title = StringField("Complaint Subject", validators=[DataRequired(), Length(min=5, max=160)])
    category = SelectField(
        "Complaint Category",
        choices=[(c, c) for c in Complaint.CATEGORIES],
        validators=[DataRequired()],
    )
    severity = SelectField(
        "Severity",
        choices=[("Low", "Low"), ("Medium", "Medium"), ("High", "High"), ("Critical", "Critical")],
        validators=[DataRequired()],
    )
    description = TextAreaField(
        "Detailed Description", validators=[DataRequired(), Length(min=10, max=2000)]
    )


class RootCauseAnalysisForm(FlaskForm):
    complaint_id = SelectField("Linked Complaint (Optional)", coerce=int, validators=[Optional()])
    problem_title = StringField("Problem Title", validators=[DataRequired(), Length(min=5, max=200)])
    fishbone_people = TextAreaField("People (Staffing, Training, Communication)", validators=[Optional()])
    fishbone_processes = TextAreaField("Processes (Workflow, Circulation Rules)", validators=[Optional()])
    fishbone_technology = TextAreaField("Technology (Catalog System, Network, Scanners)", validators=[Optional()])
    fishbone_materials = TextAreaField("Materials & Resources (Book Copies, Shelving, Signage)", validators=[Optional()])
    fishbone_environment = TextAreaField("Environment (Lighting, Noise, Seating, Climate)", validators=[Optional()])
    fishbone_policies = TextAreaField("Policies & Procedures (Loan Limits, Fine Rules, Holds)", validators=[Optional()])
    why_1 = StringField("1st Why (Immediate Symptom)", validators=[DataRequired(), Length(max=255)])
    why_2 = StringField("2nd Why", validators=[Optional(), Length(max=255)])
    why_3 = StringField("3rd Why", validators=[Optional(), Length(max=255)])
    why_4 = StringField("4th Why", validators=[Optional(), Length(max=255)])
    why_5 = StringField("5th Why (Deep Systemic Cause)", validators=[Optional(), Length(max=255)])
    identified_root_cause = TextAreaField(
        "Verified Root Cause Summary", validators=[DataRequired(), Length(min=5, max=1500)]
    )


class ImprovementActionForm(FlaskForm):
    rca_id = SelectField("Linked Root-Cause Analysis (Optional)", coerce=int, validators=[Optional()])
    problem_description = TextAreaField("Problem Description", validators=[DataRequired()])
    identified_root_cause = TextAreaField("Identified Root Cause", validators=[DataRequired()])
    proposed_corrective_action = TextAreaField("Proposed Corrective Action", validators=[DataRequired()])
    assigned_owner = StringField("Assigned Owner", validators=[DataRequired(), Length(max=120)])
    priority = SelectField(
        "Priority",
        choices=[("Low", "Low"), ("Medium", "Medium"), ("High", "High"), ("Critical", "Critical")],
        validators=[DataRequired()],
    )
    target_completion_date = DateField("Target Completion Date", validators=[DataRequired()])
    expected_result = TextAreaField("Expected Measurable Result", validators=[DataRequired()])


class PDCACycleForm(FlaskForm):
    title = StringField("PDCA Initiative Title", validators=[DataRequired(), Length(min=5, max=180)])
    current_phase = SelectField(
        "Current PDCA Phase",
        choices=[
            ("Plan", "PLAN - Define Problem & Baseline"),
            ("Do", "DO - Execute Intervention"),
            ("Check", "CHECK - Evaluate Outcomes vs Target"),
            ("Act", "ACT - Standardize Improvement"),
            ("Completed", "COMPLETED - Standardized & Closed"),
        ],
        validators=[DataRequired()],
    )
    problem_statement = TextAreaField("PLAN: Quality Problem Statement", validators=[DataRequired()])
    baseline_metric = StringField("PLAN: Baseline Measurement", validators=[DataRequired(), Length(max=160)])
    target_metric = StringField("PLAN: Target Goal", validators=[DataRequired(), Length(max=160)])
    measurement_method = StringField("PLAN: Measurement Method", validators=[DataRequired(), Length(max=200)])
    assigned_owner = StringField("DO: Assigned Owner", validators=[DataRequired(), Length(max=120)])
    intervention_details = TextAreaField("DO: Intervention & Action Executed", validators=[Optional()])
    measured_outcome = TextAreaField("CHECK: Measured Outcome", validators=[Optional()])
    comparison_analysis = TextAreaField("CHECK: Baseline vs Target Comparison", validators=[Optional()])
    target_achieved = BooleanField("CHECK: Target Metric Achieved")
    standardization_action = TextAreaField("ACT: Standardization & SOP Update", validators=[Optional()])
    next_cycle_recommendations = TextAreaField("ACT: Next Cycle Recommendations", validators=[Optional()])
