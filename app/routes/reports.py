import csv
import io
from flask import Blueprint, render_template, Response
from app.models import Role, Book, BookCopy, Loan, Fine, Complaint
from app.decorators import role_required
from app.services.tqm_service import get_all_kpis, get_pareto_analysis

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


@reports_bp.route("/")
@role_required(Role.ADMIN, Role.QUALITY)
def index():
    books_count = Book.query.count()
    copies_count = BookCopy.query.count()
    loans_count = Loan.query.count()
    overdue_count = sum(1 for ln in Loan.query.all() if ln.is_overdue)
    fines_count = Fine.query.count()
    complaints_count = Complaint.query.count()
    return render_template(
        "reports/index.html",
        books_count=books_count,
        copies_count=copies_count,
        loans_count=loans_count,
        overdue_count=overdue_count,
        fines_count=fines_count,
        complaints_count=complaints_count,
    )


def _csv_response(rows: list[list], headers: list[str], filename: str) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    output = buf.getvalue()
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@reports_bp.route("/export/inventory.csv")
@role_required(Role.ADMIN, Role.QUALITY)
def export_inventory_csv():
    headers = [
        "Copy Code",
        "ISBN",
        "Title",
        "Author",
        "Category",
        "Shelf Location",
        "Status",
        "Condition",
        "Inventory Verified",
        "Is Demo Data",
    ]
    copies = BookCopy.query.join(Book).order_by(Book.title.asc(), BookCopy.copy_code.asc()).all()
    rows = [
        [
            c.copy_code,
            c.book.isbn,
            c.book.title,
            c.book.author.name,
            c.book.category.name,
            c.book.shelf_location,
            c.status,
            c.condition,
            "Yes" if c.inventory_verified else "No",
            "DEMO" if c.is_demo else "LIVE",
        ]
        for c in copies
    ]
    return _csv_response(rows, headers, "library_inventory_report.csv")


@reports_bp.route("/export/loans.csv")
@role_required(Role.ADMIN, Role.QUALITY)
def export_loans_csv():
    headers = [
        "Loan ID",
        "Copy Code",
        "Book Title",
        "Member ID",
        "Member Name",
        "Issue Date",
        "Due Date",
        "Return Date",
        "Status",
        "Overdue",
        "Processing Time (s)",
        "Data Tag",
    ]
    loans = Loan.query.order_by(Loan.issue_date.desc()).all()
    rows = [
        [
            ln.id,
            ln.copy.copy_code,
            ln.copy.book.title,
            ln.member.membership_number,
            ln.member.user.full_name,
            ln.issue_date.strftime("%Y-%m-%d %H:%M"),
            ln.due_date.strftime("%Y-%m-%d %H:%M"),
            ln.return_date.strftime("%Y-%m-%d %H:%M") if ln.return_date else "",
            ln.status,
            "Yes" if ln.is_overdue else "No",
            ln.processing_time_seconds,
            "DEMO" if ln.is_demo else "LIVE",
        ]
        for ln in loans
    ]
    return _csv_response(rows, headers, "borrowing_history_report.csv")


@reports_bp.route("/export/overdue.csv")
@role_required(Role.ADMIN, Role.QUALITY)
def export_overdue_csv():
    headers = [
        "Loan ID",
        "Copy Code",
        "Book Title",
        "Membership Number",
        "Member Name",
        "Department",
        "Issue Date",
        "Due Date",
        "Days Overdue",
        "Current Status",
    ]
    overdue_loans = [ln for ln in Loan.query.order_by(Loan.due_date.asc()).all() if ln.is_overdue]
    rows = [
        [
            ln.id,
            ln.copy.copy_code,
            ln.copy.book.title,
            ln.member.membership_number,
            ln.member.user.full_name,
            ln.member.department,
            ln.issue_date.strftime("%Y-%m-%d"),
            ln.due_date.strftime("%Y-%m-%d"),
            ln.days_overdue,
            "Returned Late" if ln.return_date else "Active Overdue",
        ]
        for ln in overdue_loans
    ]
    return _csv_response(rows, headers, "overdue_loans_report.csv")


@reports_bp.route("/export/fines.csv")
@role_required(Role.ADMIN, Role.QUALITY)
def export_fines_csv():
    headers = [
        "Fine ID",
        "Loan ID",
        "Membership Number",
        "Member Name",
        "Book Title",
        "Amount ($)",
        "Reason",
        "Status",
        "Assessed Date",
        "Paid/Settled Date",
    ]
    fines = Fine.query.order_by(Fine.created_at.desc()).all()
    rows = [
        [
            f.id,
            f.loan_id,
            f.member.membership_number,
            f.member.user.full_name,
            f.loan.copy.book.title,
            f"{f.amount:.2f}",
            f.reason,
            f.status,
            f.created_at.strftime("%Y-%m-%d"),
            f.paid_at.strftime("%Y-%m-%d") if f.paid_at else "",
        ]
        for f in fines
    ]
    return _csv_response(rows, headers, "fines_financial_report.csv")


@reports_bp.route("/export/tqm_kpis.csv")
@role_required(Role.ADMIN, Role.QUALITY)
def export_tqm_kpis_csv():
    headers = [
        "KPI #",
        "Indicator Name",
        "Measured Value",
        "Target",
        "Status",
        "Formula",
        "Measurement Period",
        "Data Source",
    ]
    kpis = get_all_kpis()
    rows = [
        [
            k["id"],
            k["name"],
            k["value"],
            k["target"],
            k["status"],
            k["formula"],
            k["measurement_period"],
            k["data_source"],
        ]
        for k in kpis
    ]
    return _csv_response(rows, headers, "tqm_kpi_performance_report.csv")


@reports_bp.route("/export/complaints.csv")
@role_required(Role.ADMIN, Role.QUALITY)
def export_complaints_csv():
    headers = [
        "Complaint ID",
        "Member ID",
        "Category",
        "Severity",
        "Subject",
        "Status",
        "Created Date",
        "Resolved Date",
        "Resolution Time (Hours)",
        "Data Tag",
    ]
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    rows = [
        [
            c.id,
            c.member.membership_number,
            c.category,
            c.severity,
            c.title,
            c.status,
            c.created_at.strftime("%Y-%m-%d %H:%M"),
            c.resolved_at.strftime("%Y-%m-%d %H:%M") if c.resolved_at else "",
            c.resolution_hours if c.resolution_hours is not None else "",
            "DEMO" if c.is_demo else "LIVE",
        ]
        for c in complaints
    ]
    return _csv_response(rows, headers, "tqm_complaints_pareto_report.csv")
