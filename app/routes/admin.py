from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models import (
    Role,
    User,
    Member,
    Book,
    BookCopy,
    Author,
    Publisher,
    Category,
    Loan,
    Reservation,
    Fine,
    Complaint,
    Feedback,
    ImprovementAction,
    Notification,
    AuditLog,
    utcnow,
)
from app.decorators import role_required, get_current_user
from app.forms import BookForm, IssueBookForm, ReturnBookForm, FinePolicyForm
from app.services.library_service import (
    LibraryOperationError,
    create_book_with_copies,
    add_physical_copy,
    issue_book_copy,
    return_book_copy,
    get_active_fine_policy,
)
from app.services.tqm_service import get_customer_satisfaction_metrics, get_borrowing_trend_chart
from app.services.audit_service import log_audit

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@role_required(Role.ADMIN)
def dashboard():
    total_books = Book.query.filter_by(is_archived=False).count()
    available_copies = BookCopy.query.filter_by(status="Available").count()
    total_copies = BookCopy.query.filter(BookCopy.status != "Archived").count()
    registered_members = Member.query.count()

    active_loans_list = Loan.query.filter(Loan.return_date.is_(None)).all()
    active_loans_count = len(active_loans_list)
    overdue_loans_count = sum(1 for ln in active_loans_list if ln.is_overdue)

    pending_complaints = Complaint.query.filter(
        Complaint.status.in_(["Open", "In Progress"])
    ).count()

    sat_metrics = get_customer_satisfaction_metrics()
    avg_satisfaction = sat_metrics["average_score"]

    open_actions = ImprovementAction.query.filter(
        ImprovementAction.status != "Completed"
    ).count()

    recent_loans = Loan.query.order_by(Loan.issue_date.desc()).limit(8).all()
    recent_logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    borrowing_chart = get_borrowing_trend_chart()

    return render_template(
        "admin/dashboard.html",
        total_books=total_books,
        available_copies=available_copies,
        total_copies=total_copies,
        registered_members=registered_members,
        active_loans=active_loans_count,
        overdue_loans=overdue_loans_count,
        pending_complaints=pending_complaints,
        avg_satisfaction=avg_satisfaction,
        open_actions=open_actions,
        recent_loans=recent_loans,
        recent_logs=recent_logs,
        borrowing_chart=borrowing_chart,
    )


def _populate_book_form_choices(form: BookForm):
    form.author_id.choices = [(a.id, a.name) for a in Author.query.order_by(Author.name).all()]
    form.publisher_id.choices = [
        (p.id, p.name) for p in Publisher.query.order_by(Publisher.name).all()
    ]
    form.category_id.choices = [
        (c.id, f"{c.name} ({c.code})") for c in Category.query.order_by(Category.name).all()
    ]


@admin_bp.route("/books", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def books():
    form = BookForm()
    _populate_book_form_choices(form)

    if form.validate_on_submit():
        try:
            book = create_book_with_copies(
                isbn=form.isbn.data,
                title=form.title.data,
                subtitle=form.subtitle.data,
                author_id=form.author_id.data,
                publisher_id=form.publisher_id.data,
                category_id=form.category_id.data,
                publication_year=form.publication_year.data,
                edition=form.edition.data,
                shelf_location=form.shelf_location.data,
                description=form.description.data,
                initial_copies=form.initial_copies.data if form.initial_copies.data is not None else 2,
                actor=get_current_user(),
            )
            flash(f"Book '{book.title}' created with {book.total_copies_count} copies.", "success")
            return redirect(url_for("admin.books"))
        except LibraryOperationError as exc:
            flash(str(exc), "danger")

    q = request.args.get("q", "").strip()
    category_id = request.args.get("category_id", type=int)
    show_archived = request.args.get("archived", "0") == "1"
    sort_by = request.args.get("sort", "title")
    page = request.args.get("page", 1, type=int)

    query = Book.query
    if not show_archived:
        query = query.filter_by(is_archived=False)
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
    elif sort_by == "isbn":
        query = query.order_by(Book.isbn.asc())
    else:
        query = query.order_by(Book.title.asc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "admin/books.html",
        form=form,
        books=pagination.items,
        pagination=pagination,
        categories=categories,
        q=q,
        selected_category=category_id,
        show_archived=show_archived,
        sort_by=sort_by,
    )


@admin_bp.route("/books/<int:book_id>", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def book_detail(book_id):
    book = db.get_or_404(Book, book_id)
    form = BookForm(obj=book)
    _populate_book_form_choices(form)

    if form.validate_on_submit():
        existing_isbn = Book.query.filter(
            Book.isbn == form.isbn.data.strip(), Book.id != book.id
        ).first()
        if existing_isbn:
            flash("Another book already uses that ISBN.", "danger")
        else:
            try:
                book.isbn = form.isbn.data.strip()
                book.title = form.title.data.strip()
                book.subtitle = form.subtitle.data.strip() if form.subtitle.data else None
                book.author_id = form.author_id.data
                book.publisher_id = form.publisher_id.data
                book.category_id = form.category_id.data
                book.publication_year = form.publication_year.data
                book.edition = form.edition.data
                book.shelf_location = form.shelf_location.data.strip()
                book.description = form.description.data
                log_audit(
                    action="UPDATE_BOOK",
                    entity_type="Book",
                    entity_id=book.id,
                    details=f"Updated book '{book.title}' (ISBN: {book.isbn}).",
                    actor=get_current_user(),
                )
                db.session.commit()
                flash("Book details updated.", "success")
                return redirect(url_for("admin.book_detail", book_id=book.id))
            except SQLAlchemyError:
                db.session.rollback()
                flash("Error updating book.", "danger")

    copies = book.copies.order_by(BookCopy.copy_code.asc()).all()
    return render_template("admin/book_detail.html", book=book, form=form, copies=copies)


@admin_bp.route("/books/<int:book_id>/add-copy", methods=["POST"])
@role_required(Role.ADMIN)
def add_copy_route(book_id):
    condition = request.form.get("condition", "Good")
    try:
        copy = add_physical_copy(book_id=book_id, condition=condition, actor=get_current_user())
        flash(f"Added physical copy {copy.copy_code}.", "success")
    except LibraryOperationError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.book_detail", book_id=book_id))


@admin_bp.route("/books/<int:book_id>/toggle-archive", methods=["POST"])
@role_required(Role.ADMIN)
def toggle_archive_book(book_id):
    book = db.get_or_404(Book, book_id)
    active_loans = (
        Loan.query.join(BookCopy)
        .filter(BookCopy.book_id == book.id, Loan.return_date.is_(None))
        .count()
    )
    if not book.is_archived and active_loans > 0:
        flash("Cannot archive a book while physical copies are actively loaned.", "danger")
        return redirect(url_for("admin.book_detail", book_id=book.id))

    book.is_archived = not book.is_archived
    for copy in book.copies:
        if book.is_archived and copy.status == "Available":
            copy.status = "Archived"
        elif not book.is_archived and copy.status == "Archived":
            copy.status = "Available"

    log_audit(
        action="ARCHIVE_BOOK" if book.is_archived else "RESTORE_BOOK",
        entity_type="Book",
        entity_id=book.id,
        details=f"{'Archived' if book.is_archived else 'Restored'} book '{book.title}'.",
        actor=get_current_user(),
        commit=True,
    )
    flash(f"Book {'archived' if book.is_archived else 'restored'} successfully.", "info")
    return redirect(url_for("admin.book_detail", book_id=book.id))


@admin_bp.route("/copies/<int:copy_id>/verify-audit", methods=["POST"])
@role_required(Role.ADMIN)
def verify_copy_audit(copy_id):
    copy = db.get_or_404(BookCopy, copy_id)
    copy.inventory_verified = not copy.inventory_verified
    copy.last_audit_date = utcnow()
    log_audit(
        action="AUDIT_BOOK_COPY",
        entity_type="BookCopy",
        entity_id=copy.copy_code,
        details=f"Shelf audit for {copy.copy_code}: verified={copy.inventory_verified}.",
        actor=get_current_user(),
        commit=True,
    )
    flash(
        f"Copy {copy.copy_code} marked as {'Verified Accurate' if copy.inventory_verified else 'Discrepant / Missing'}.",
        "info",
    )
    return redirect(url_for("admin.book_detail", book_id=copy.book_id))


@admin_bp.route("/metadata", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def metadata():
    if request.method == "POST":
        entity_kind = request.form.get("entity_kind")
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "danger")
            return redirect(url_for("admin.metadata"))
        try:
            if entity_kind == "author":
                bio = request.form.get("biography", "").strip()
                db.session.add(Author(name=name, biography=bio))
                log_audit("CREATE_AUTHOR", "Author", name, f"Added author '{name}'", get_current_user())
            elif entity_kind == "publisher":
                website = request.form.get("website", "").strip()
                db.session.add(Publisher(name=name, website=website))
                log_audit("CREATE_PUBLISHER", "Publisher", name, f"Added publisher '{name}'", get_current_user())
            elif entity_kind == "category":
                code = request.form.get("code", "").strip().upper() or name[:4].upper()
                desc = request.form.get("description", "").strip()
                db.session.add(Category(name=name, code=code, description=desc))
                log_audit("CREATE_CATEGORY", "Category", code, f"Added category '{name}' ({code})", get_current_user())
            db.session.commit()
            flash(f"Added {entity_kind} '{name}'.", "success")
        except SQLAlchemyError:
            db.session.rollback()
            flash(f"Could not create {entity_kind} (may already exist).", "danger")
        return redirect(url_for("admin.metadata"))

    authors = Author.query.order_by(Author.name).all()
    publishers = Publisher.query.order_by(Publisher.name).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template(
        "admin/metadata.html", authors=authors, publishers=publishers, categories=categories
    )


@admin_bp.route("/members", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def members():
    if request.method == "POST":
        member_id = request.form.get("member_id", type=int)
        action = request.form.get("action")
        member = db.get_or_404(Member, member_id)
        if action == "toggle_status":
            member.status = "Suspended" if member.status == "Active" else "Active"
            log_audit(
                "UPDATE_MEMBER_STATUS",
                "Member",
                member.membership_number,
                f"Changed member {member.membership_number} status to {member.status}.",
                get_current_user(),
                commit=True,
            )
            flash(f"Member {member.membership_number} status updated to {member.status}.", "info")
        return redirect(url_for("admin.members"))

    q = request.args.get("q", "").strip()
    query = Member.query.join(User)
    if q:
        query = query.filter(
            or_(
                Member.membership_number.ilike(f"%{q}%"),
                User.full_name.ilike(f"%{q}%"),
                User.email.ilike(f"%{q}%"),
                Member.department.ilike(f"%{q}%"),
            )
        )
    members_list = query.order_by(Member.joined_at.desc()).all()
    return render_template("admin/members.html", members=members_list, q=q)


@admin_bp.route("/loans", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def loans():
    form = IssueBookForm()
    available_copies = (
        BookCopy.query.join(Book)
        .filter(BookCopy.status == "Available", Book.is_archived == False)
        .order_by(Book.title.asc(), BookCopy.copy_code.asc())
        .all()
    )
    form.copy_id.choices = [
        (c.id, f"{c.copy_code} — {c.book.title} ({c.condition})") for c in available_copies
    ]
    active_members = (
        Member.query.join(User)
        .filter(Member.status == "Active")
        .order_by(User.full_name.asc())
        .all()
    )
    form.member_id.choices = [
        (m.id, f"{m.user.full_name} ({m.membership_number} - {m.member_type})")
        for m in active_members
    ]

    if form.validate_on_submit():
        try:
            loan = issue_book_copy(
                copy_id=form.copy_id.data,
                member_id=form.member_id.data,
                loan_days=form.loan_days.data,
                processing_time_seconds=form.processing_time_seconds.data,
                standardized_checklist_verified=form.standardized_checklist_verified.data,
                notes=form.notes.data,
                actor=get_current_user(),
            )
            flash(
                f"Issued copy {loan.copy.copy_code} to {loan.member.user.full_name}. Due: {loan.due_date.strftime('%Y-%m-%d')}.",
                "success",
            )
            return redirect(url_for("admin.loans"))
        except LibraryOperationError as exc:
            flash(str(exc), "danger")

    filter_status = request.args.get("status", "all")
    loans_query = Loan.query.order_by(Loan.issue_date.desc())
    all_loans = loans_query.all()
    if filter_status == "active":
        all_loans = [ln for ln in all_loans if ln.return_date is None]
    elif filter_status == "overdue":
        all_loans = [ln for ln in all_loans if ln.is_overdue and ln.return_date is None]
    elif filter_status == "returned":
        all_loans = [ln for ln in all_loans if ln.return_date is not None]

    return_form = ReturnBookForm()
    return render_template(
        "admin/loans.html",
        form=form,
        return_form=return_form,
        loans=all_loans,
        filter_status=filter_status,
    )


@admin_bp.route("/loans/<int:loan_id>/return", methods=["POST"])
@role_required(Role.ADMIN)
def return_loan_route(loan_id):
    return_condition = request.form.get("return_condition", "Good")
    notes = request.form.get("notes", "")
    try:
        loan = return_book_copy(
            loan_id=loan_id,
            return_condition=return_condition,
            notes=notes,
            actor=get_current_user(),
        )
        fine_msg = f" Fine assessed: ${loan.fine.amount:.2f}." if loan.fine else ""
        flash(f"Copy {loan.copy.copy_code} returned successfully.{fine_msg}", "success")
    except LibraryOperationError as exc:
        flash(str(exc), "danger")
    return redirect(url_for("admin.loans"))


@admin_bp.route("/reservations", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def reservations():
    if request.method == "POST":
        res_id = request.form.get("reservation_id", type=int)
        new_status = request.form.get("status")
        res = db.get_or_404(Reservation, res_id)
        if new_status in ("Ready", "Fulfilled", "Cancelled"):
            res.status = new_status
            if new_status == "Fulfilled":
                res.fulfilled_at = utcnow()
            db.session.add(
                Notification(
                    user_id=res.member.user_id,
                    title=f"Reservation {new_status}",
                    message=f"Your reservation for '{res.book.title}' is now marked as {new_status}.",
                    notification_type="reservation",
                )
            )
            log_audit(
                "UPDATE_RESERVATION",
                "Reservation",
                res.id,
                f"Updated reservation #{res.id} status to {new_status}.",
                get_current_user(),
                commit=True,
            )
            flash(f"Reservation #{res.id} marked as {new_status}.", "info")
        return redirect(url_for("admin.reservations"))

    reservations_list = Reservation.query.order_by(Reservation.created_at.desc()).all()
    return render_template("admin/reservations.html", reservations=reservations_list)


@admin_bp.route("/fines", methods=["GET", "POST"])
@role_required(Role.ADMIN)
def fines():
    policy = get_active_fine_policy()
    form = FinePolicyForm(obj=policy)

    if form.validate_on_submit():
        policy.loan_duration_days = form.loan_duration_days.data
        policy.fine_per_day = form.fine_per_day.data
        policy.grace_period_days = form.grace_period_days.data or 0
        policy.max_fine_cap = form.max_fine_cap.data
        log_audit(
            "UPDATE_FINE_POLICY",
            "FinePolicy",
            policy.id,
            f"Updated fine policy: ${policy.fine_per_day}/day, loan={policy.loan_duration_days}d, grace={policy.grace_period_days}d.",
            get_current_user(),
            commit=True,
        )
        flash("Fine policy updated successfully.", "success")
        return redirect(url_for("admin.fines"))

    fines_list = Fine.query.order_by(Fine.created_at.desc()).all()
    return render_template("admin/fines.html", form=form, policy=policy, fines=fines_list)


@admin_bp.route("/fines/<int:fine_id>/status", methods=["POST"])
@role_required(Role.ADMIN)
def update_fine_status(fine_id):
    fine = db.get_or_404(Fine, fine_id)
    new_status = request.form.get("status")
    if new_status in ("Paid", "Waived"):
        fine.status = new_status
        fine.paid_at = utcnow()
        log_audit(
            "SETTLE_FINE",
            "Fine",
            fine.id,
            f"Marked fine #{fine.id} (${fine.amount:.2f}) as {new_status}.",
            get_current_user(),
            commit=True,
        )
        flash(f"Fine #{fine.id} marked as {new_status}.", "success")
    return redirect(url_for("admin.fines"))


@admin_bp.route("/complaints", methods=["GET", "POST"])
@role_required(Role.ADMIN, Role.QUALITY)
def complaints():
    if request.method == "POST":
        complaint_id = request.form.get("complaint_id", type=int)
        new_status = request.form.get("status")
        resolution_notes = request.form.get("resolution_notes", "").strip()
        complaint = db.get_or_404(Complaint, complaint_id)

        complaint.status = new_status
        if resolution_notes:
            complaint.resolution_notes = resolution_notes
        if new_status in ("Resolved", "Closed") and not complaint.resolved_at:
            complaint.resolved_at = utcnow()
            complaint.resolved_by_id = get_current_user().id

        db.session.add(
            Notification(
                user_id=complaint.member.user_id,
                title=f"Complaint #{complaint.id} Updated: {new_status}",
                message=f"Your complaint '{complaint.title}' is now '{new_status}'. Notes: {resolution_notes or 'Under review'}",
                notification_type="complaint_update",
            )
        )
        log_audit(
            "UPDATE_COMPLAINT",
            "Complaint",
            complaint.id,
            f"Updated complaint #{complaint.id} to '{new_status}'.",
            get_current_user(),
            commit=True,
        )
        flash(f"Complaint #{complaint.id} updated to {new_status}.", "success")
        return redirect(url_for("admin.complaints"))

    complaints_list = Complaint.query.order_by(Complaint.created_at.desc()).all()
    feedbacks_list = Feedback.query.order_by(Feedback.created_at.desc()).all()
    return render_template(
        "admin/complaints.html", complaints=complaints_list, feedbacks=feedbacks_list
    )


@admin_bp.route("/audit-logs")
@role_required(Role.ADMIN)
def audit_logs():
    page = request.args.get("page", 1, type=int)
    action_filter = request.args.get("action", "").strip()
    query = AuditLog.query
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f"%{action_filter}%"))
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    return render_template(
        "admin/audit_logs.html",
        logs=pagination.items,
        pagination=pagination,
        action_filter=action_filter,
    )
