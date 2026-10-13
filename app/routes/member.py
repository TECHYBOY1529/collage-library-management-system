from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from sqlalchemy import or_
from app.extensions import db
from app.models import (
    Role,
    Book,
    Author,
    Category,
    Loan,
    Reservation,
    Fine,
    Feedback,
    Complaint,
    Notification,
)
from app.decorators import role_required, get_current_user
from app.forms import FeedbackForm, ComplaintForm
from app.services.library_service import LibraryOperationError, create_reservation
from app.services.audit_service import log_audit

member_bp = Blueprint("member", __name__, url_prefix="/member")


def _get_current_member():
    user = get_current_user()
    if not user or not user.member_profile:
        abort(403)
    return user.member_profile


@member_bp.route("/dashboard")
@role_required(Role.MEMBER)
def dashboard():
    member = _get_current_member()
    active_loans = (
        Loan.query.filter(Loan.member_id == member.id, Loan.return_date.is_(None))
        .order_by(Loan.due_date.asc())
        .all()
    )
    overdue_count = sum(1 for ln in active_loans if ln.is_overdue)
    unpaid_fines = Fine.query.filter_by(member_id=member.id, status="Unpaid").all()
    total_unpaid = round(sum(f.amount for f in unpaid_fines), 2)

    active_reservations = (
        Reservation.query.filter(
            Reservation.member_id == member.id,
            Reservation.status.in_(["Pending", "Ready"]),
        )
        .order_by(Reservation.created_at.desc())
        .all()
    )
    notifications = (
        Notification.query.filter_by(user_id=member.user_id)
        .order_by(Notification.created_at.desc())
        .limit(6)
        .all()
    )
    my_complaints = (
        Complaint.query.filter_by(member_id=member.id)
        .order_by(Complaint.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template(
        "member/dashboard.html",
        member=member,
        active_loans=active_loans,
        overdue_count=overdue_count,
        total_unpaid=total_unpaid,
        active_reservations=active_reservations,
        notifications=notifications,
        my_complaints=my_complaints,
    )


@member_bp.route("/catalog")
@role_required(Role.MEMBER)
def catalog():
    member = _get_current_member()
    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    available_only = request.args.get("available", "0") == "1"
    sort_by = request.args.get("sort", "title")
    page = request.args.get("page", 1, type=int)

    query = Book.query.filter_by(is_archived=False)
    if q:
        query = query.join(Author).filter(
            or_(
                Book.title.ilike(f"%{q}%"),
                Book.isbn.ilike(f"%{q}%"),
                Author.name.ilike(f"%{q}%"),
            )
        )
    if category_id:
        query = query.filter(Book.category_id == category_id)

    if sort_by == "newest":
        query = query.order_by(Book.created_at.desc())
    elif sort_by == "year":
        query = query.order_by(Book.publication_year.desc())
    else:
        query = query.order_by(Book.title.asc())

    books_all = query.all()
    if available_only:
        books_all = [b for b in books_all if b.available_copies_count > 0]

    # Simple manual slice pagination after availability filter
    per_page = 9
    total = len(books_all)
    start = (page - 1) * per_page
    end = start + per_page
    books_page = books_all[start:end]
    total_pages = max(1, (total + per_page - 1) // per_page)

    categories = Category.query.order_by(Category.name).all()
    return render_template(
        "member/catalog.html",
        member=member,
        books=books_page,
        categories=categories,
        q=q,
        selected_category=category_id,
        available_only=available_only,
        sort_by=sort_by,
        page=page,
        total_pages=total_pages,
        total_results=total,
    )


@member_bp.route("/reserve/<int:book_id>", methods=["POST"])
@role_required(Role.MEMBER)
def reserve_book(book_id):
    member = _get_current_member()
    notes = request.form.get("notes", "").strip()
    try:
        res = create_reservation(book_id=book_id, member_id=member.id, notes=notes)
        flash(
            f"Reservation confirmed for '{res.book.title}' (Status: {res.status}, Queue #{res.queue_position}).",
            "success",
        )
    except LibraryOperationError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("member.reservations"))


@member_bp.route("/loans")
@role_required(Role.MEMBER)
def loans():
    member = _get_current_member()
    my_loans = (
        Loan.query.filter_by(member_id=member.id)
        .order_by(Loan.issue_date.desc())
        .all()
    )
    return render_template("member/loans.html", member=member, loans=my_loans)


@member_bp.route("/loans/<int:loan_id>")
@role_required(Role.MEMBER)
def loan_detail(loan_id):
    """Protected member loan receipt endpoint: prevents unauthorized access to other members' loans."""
    member = _get_current_member()
    loan = db.get_or_404(Loan, loan_id)
    if loan.member_id != member.id:
        abort(403)
    return render_template("member/loans.html", member=member, loans=[loan], single_loan=loan)


@member_bp.route("/reservations", methods=["GET", "POST"])
@role_required(Role.MEMBER)
def reservations():
    member = _get_current_member()
    if request.method == "POST":
        res_id = request.form.get("reservation_id", type=int)
        res = db.get_or_404(Reservation, res_id)
        if res.member_id != member.id:
            abort(403)
        if res.status in ("Pending", "Ready"):
            res.status = "Cancelled"
            db.session.commit()
            flash("Reservation cancelled.", "info")
        return redirect(url_for("member.reservations"))

    my_reservations = (
        Reservation.query.filter_by(member_id=member.id)
        .order_by(Reservation.created_at.desc())
        .all()
    )
    return render_template("member/reservations.html", member=member, reservations=my_reservations)


@member_bp.route("/fines")
@role_required(Role.MEMBER)
def fines():
    member = _get_current_member()
    my_fines = (
        Fine.query.filter_by(member_id=member.id)
        .order_by(Fine.created_at.desc())
        .all()
    )
    return render_template("member/fines.html", member=member, fines=my_fines)


@member_bp.route("/feedback-complaints", methods=["GET", "POST"])
@role_required(Role.MEMBER)
def feedback_complaints():
    member = _get_current_member()
    fb_form = FeedbackForm(prefix="fb")
    cmp_form = ComplaintForm(prefix="cmp")

    books = Book.query.filter_by(is_archived=False).order_by(Book.title).all()
    fb_form.book_id.choices = [(0, "General Library Service (No specific book)")] + [
        (b.id, b.title) for b in books
    ]

    form_type = request.form.get("form_type")
    if request.method == "POST" and form_type == "feedback":
        if fb_form.validate_on_submit():
            book_id = fb_form.book_id.data if fb_form.book_id.data and fb_form.book_id.data > 0 else None
            fb = Feedback(
                member_id=member.id,
                book_id=book_id,
                category=fb_form.category.data,
                rating=int(fb_form.rating.data),
                comments=fb_form.comments.data.strip(),
                is_recurring_concern=bool(fb_form.is_recurring_concern.data),
                is_demo=False,
            )
            db.session.add(fb)
            log_audit(
                "SUBMIT_FEEDBACK",
                "Feedback",
                member.membership_number,
                f"Submitted {fb.rating}/5 rating in category '{fb.category}'.",
                get_current_user(),
                commit=True,
            )
            flash("Thank you! Your quality feedback has been recorded in the TQM system.", "success")
            return redirect(url_for("member.feedback_complaints"))

    if request.method == "POST" and form_type == "complaint":
        if cmp_form.validate_on_submit():
            cmp_record = Complaint(
                member_id=member.id,
                title=cmp_form.title.data.strip(),
                category=cmp_form.category.data,
                severity=cmp_form.severity.data,
                description=cmp_form.description.data.strip(),
                status="Open",
                is_demo=False,
            )
            db.session.add(cmp_record)
            log_audit(
                "SUBMIT_COMPLAINT",
                "Complaint",
                member.membership_number,
                f"Submitted complaint '{cmp_record.title}' ({cmp_record.category}, {cmp_record.severity}).",
                get_current_user(),
                commit=True,
            )
            flash("Your complaint has been logged and routed to the Quality Management team.", "success")
            return redirect(url_for("member.feedback_complaints"))

    my_feedbacks = (
        Feedback.query.filter_by(member_id=member.id)
        .order_by(Feedback.created_at.desc())
        .all()
    )
    my_complaints = (
        Complaint.query.filter_by(member_id=member.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )
    return render_template(
        "member/feedback_complaints.html",
        member=member,
        fb_form=fb_form,
        cmp_form=cmp_form,
        my_feedbacks=my_feedbacks,
        my_complaints=my_complaints,
    )


@member_bp.route("/notifications", methods=["GET", "POST"])
@role_required(Role.MEMBER)
def notifications():
    member = _get_current_member()
    if request.method == "POST":
        Notification.query.filter_by(user_id=member.user_id, is_read=False).update({"is_read": True})
        db.session.commit()
        flash("All notifications marked as read.", "info")
        return redirect(url_for("member.notifications"))

    notifs = (
        Notification.query.filter_by(user_id=member.user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return render_template("member/notifications.html", member=member, notifications=notifs)
