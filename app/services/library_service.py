from datetime import timedelta
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models import (
    Book,
    BookCopy,
    Member,
    Loan,
    Reservation,
    Fine,
    FinePolicy,
    Notification,
    utcnow,
)
from app.services.audit_service import log_audit


class LibraryOperationError(Exception):
    """Domain exception for invalid library operations."""
    pass


def get_active_fine_policy() -> FinePolicy:
    policy = FinePolicy.query.filter_by(is_active=True).first()
    if not policy:
        policy = FinePolicy(
            name="Standard Academic Policy",
            loan_duration_days=14,
            fine_per_day=2.00,
            grace_period_days=0,
            max_fine_cap=100.00,
            is_active=True,
        )
        db.session.add(policy)
        db.session.commit()
    return policy


def create_book_with_copies(
    isbn: str,
    title: str,
    author_id: int,
    publisher_id: int,
    category_id: int,
    shelf_location: str = "A-101",
    subtitle: str = None,
    publication_year: int = 2024,
    edition: str = "1st",
    description: str = None,
    initial_copies: int = 2,
    actor=None,
    is_demo: bool = False,
) -> Book:
    """Create a book and generate unique physical BookCopy records transactionally."""
    if initial_copies < 0:
        raise LibraryOperationError("Initial copy count cannot be negative.")
    if Book.query.filter_by(isbn=isbn.strip()).first():
        raise LibraryOperationError(f"A book with ISBN '{isbn}' already exists.")

    try:
        book = Book(
            isbn=isbn.strip(),
            title=title.strip(),
            subtitle=subtitle.strip() if subtitle else None,
            author_id=author_id,
            publisher_id=publisher_id,
            category_id=category_id,
            publication_year=publication_year,
            edition=edition,
            shelf_location=shelf_location.strip(),
            description=description,
            is_demo=is_demo,
        )
        db.session.add(book)
        db.session.flush()

        for i in range(1, initial_copies + 1):
            copy_code = f"CP-{book.id:04d}-{i:02d}"
            copy = BookCopy(
                book_id=book.id,
                copy_code=copy_code,
                status="Available",
                condition="Good",
                inventory_verified=True,
                is_demo=is_demo,
            )
            db.session.add(copy)

        log_audit(
            action="CREATE_BOOK",
            entity_type="Book",
            entity_id=book.id,
            details=f"Created book '{book.title}' (ISBN: {book.isbn}) with {initial_copies} physical copies.",
            actor=actor,
            is_demo=is_demo,
        )
        db.session.commit()
        return book
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LibraryOperationError(f"Database error creating book: {str(exc)}") from exc


def add_physical_copy(
    book_id: int, condition: str = "Good", copy_code: str = None, actor=None, is_demo: bool = False
) -> BookCopy:
    book = db.session.get(Book, book_id)
    if not book:
        raise LibraryOperationError("Book not found.")
    existing_count = BookCopy.query.filter_by(book_id=book.id).count()
    if not copy_code:
        copy_code = f"CP-{book.id:04d}-{existing_count + 1:02d}"
        while BookCopy.query.filter_by(copy_code=copy_code).first():
            existing_count += 1
            copy_code = f"CP-{book.id:04d}-{existing_count + 1:02d}"

    try:
        copy = BookCopy(
            book_id=book.id,
            copy_code=copy_code,
            status="Available",
            condition=condition,
            inventory_verified=True,
            is_demo=is_demo,
        )
        db.session.add(copy)
        log_audit(
            action="ADD_BOOK_COPY",
            entity_type="BookCopy",
            entity_id=copy_code,
            details=f"Added physical copy {copy_code} for '{book.title}'.",
            actor=actor,
            is_demo=is_demo,
        )
        db.session.commit()
        return copy
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LibraryOperationError(f"Failed to add copy: {str(exc)}") from exc


def issue_book_copy(
    copy_id: int,
    member_id: int,
    loan_days: int = None,
    processing_time_seconds: float = 35.0,
    standardized_checklist_verified: bool = True,
    notes: str = None,
    actor=None,
    issue_date=None,
    is_demo: bool = False,
) -> Loan:
    """Issue a specific physical copy to a member with strict invariant checks."""
    if not standardized_checklist_verified:
        raise LibraryOperationError(
            "Standardized TQM checkout checklist must be verified before issuing a book."
        )
    if processing_time_seconds is not None and processing_time_seconds <= 0:
        raise LibraryOperationError("Processing time must be a positive number of seconds.")

    copy = db.session.get(BookCopy, copy_id)
    if not copy:
        raise LibraryOperationError("Physical book copy not found.")
    if copy.book.is_archived:
        raise LibraryOperationError("Cannot issue a copy of an archived book.")
    if copy.status != "Available":
        raise LibraryOperationError(
            f"Copy '{copy.copy_code}' is currently '{copy.status}' and cannot be issued."
        )

    member = db.session.get(Member, member_id)
    if not member:
        raise LibraryOperationError("Library member not found.")
    if member.status != "Active":
        raise LibraryOperationError(f"Member '{member.membership_number}' account is {member.status}.")

    # Check active loan count for member
    active_loans_count = Loan.query.filter(
        Loan.member_id == member.id, Loan.return_date.is_(None)
    ).count()
    if active_loans_count >= member.max_books_allowed:
        raise LibraryOperationError(
            f"Member has reached the maximum allowed active loans ({member.max_books_allowed})."
        )

    # Prevent duplicate active loan of the same book title by the same member
    existing_book_loan = (
        Loan.query.join(BookCopy)
        .filter(
            Loan.member_id == member.id,
            Loan.return_date.is_(None),
            BookCopy.book_id == copy.book_id,
        )
        .first()
    )
    if existing_book_loan:
        raise LibraryOperationError(
            f"Member already has an active loan for '{copy.book.title}' (Copy {existing_book_loan.copy.copy_code}). Duplicate active loans are not permitted."
        )

    policy = get_active_fine_policy()
    days = loan_days if (loan_days and loan_days > 0) else policy.loan_duration_days
    now = issue_date or utcnow()
    due_date = now + timedelta(days=days)

    try:
        copy.status = "Issued"
        loan = Loan(
            copy_id=copy.id,
            member_id=member.id,
            issued_by_id=actor.id if actor else None,
            issue_date=now,
            due_date=due_date,
            status="Active",
            processing_time_seconds=processing_time_seconds or 35.0,
            standardized_checklist_verified=True,
            notes=notes,
            is_demo=is_demo,
        )
        db.session.add(loan)

        # Fulfill any pending/ready reservation this member had for this book
        reservation = Reservation.query.filter(
            Reservation.book_id == copy.book_id,
            Reservation.member_id == member.id,
            Reservation.status.in_(["Pending", "Ready"]),
        ).first()
        if reservation:
            reservation.status = "Fulfilled"
            reservation.fulfilled_at = now

        # Create due-date notification for member
        notif = Notification(
            user_id=member.user_id,
            title="Book Issued - Due Date Reminder",
            message=f"You borrowed '{copy.book.title}' (Copy {copy.copy_code}). Due date: {due_date.strftime('%Y-%m-%d')}.",
            notification_type="due_date",
            is_demo=is_demo,
        )
        db.session.add(notif)

        log_audit(
            action="ISSUE_BOOK",
            entity_type="Loan",
            entity_id=copy.copy_code,
            details=f"Issued copy {copy.copy_code} ('{copy.book.title}') to member {member.membership_number}. Due: {due_date.strftime('%Y-%m-%d')}.",
            actor=actor,
            is_demo=is_demo,
        )
        db.session.commit()
        return loan
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LibraryOperationError(f"Transaction failed while issuing book: {str(exc)}") from exc


def calculate_fine_amount(due_date, return_date, policy: FinePolicy = None) -> float:
    """Calculate overdue fine based on active FinePolicy."""
    if not policy:
        policy = get_active_fine_policy()
    if return_date <= due_date:
        return 0.0
    delta = return_date - due_date
    overdue_days = delta.days + (1 if delta.seconds > 0 and delta.days == 0 else 0)
    if overdue_days <= policy.grace_period_days:
        return 0.0
    chargeable_days = overdue_days
    fine = round(chargeable_days * policy.fine_per_day, 2)
    return min(fine, policy.max_fine_cap)


def return_book_copy(
    loan_id: int,
    return_condition: str = "Good",
    notes: str = None,
    return_date=None,
    actor=None,
    is_demo: bool = False,
) -> Loan:
    """Process a book return, synchronize copy status, calculate fines, and notify next reservation."""
    loan = db.session.get(Loan, loan_id)
    if not loan:
        raise LibraryOperationError("Loan record not found.")
    if loan.return_date is not None or loan.status == "Returned":
        raise LibraryOperationError(f"Loan #{loan.id} has already been returned.")

    now = return_date or utcnow()
    if now < loan.issue_date:
        raise LibraryOperationError("Return date cannot be earlier than the issue date.")

    policy = get_active_fine_policy()
    copy = loan.copy

    try:
        loan.return_date = now
        loan.status = "Returned"
        loan.return_condition = return_condition
        if notes:
            loan.notes = (loan.notes + " | " if loan.notes else "") + notes

        copy.condition = return_condition
        if return_condition == "Damaged":
            copy.status = "Maintenance"
        else:
            copy.status = "Available"

        # Calculate overdue fine if applicable
        fine_amount = calculate_fine_amount(loan.due_date, now, policy)
        if fine_amount > 0 and not loan.fine:
            fine = Fine(
                loan_id=loan.id,
                member_id=loan.member_id,
                amount=fine_amount,
                reason=f"Overdue return ({loan.days_overdue} days past due date)",
                status="Unpaid",
                is_demo=is_demo or loan.is_demo,
            )
            db.session.add(fine)
            db.session.add(
                Notification(
                    user_id=loan.member.user_id,
                    title="Overdue Fine Assessed",
                    message=f"A fine of ${fine_amount:.2f} was assessed for late return of '{copy.book.title}'.",
                    notification_type="fine",
                    is_demo=is_demo or loan.is_demo,
                )
            )

        # Check waiting list / reservations for this book if copy is Available
        if copy.status == "Available":
            next_res = (
                Reservation.query.filter_by(book_id=copy.book_id, status="Pending")
                .order_by(Reservation.queue_position.asc(), Reservation.created_at.asc())
                .first()
            )
            if next_res:
                next_res.status = "Ready"
                db.session.add(
                    Notification(
                        user_id=next_res.member.user_id,
                        title="Reserved Book Ready for Pickup",
                        message=f"Good news! A copy of '{copy.book.title}' is now available for your reservation.",
                        notification_type="reservation",
                        is_demo=is_demo or next_res.is_demo,
                    )
                )

        log_audit(
            action="RETURN_BOOK",
            entity_type="Loan",
            entity_id=loan.id,
            details=f"Returned copy {copy.copy_code} ('{copy.book.title}') from member {loan.member.membership_number}. Condition: {return_condition}. Fine: ${fine_amount:.2f}.",
            actor=actor,
            is_demo=is_demo or loan.is_demo,
        )
        db.session.commit()
        return loan
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LibraryOperationError(f"Transaction failed while returning book: {str(exc)}") from exc


def create_reservation(book_id: int, member_id: int, notes: str = None, is_demo: bool = False) -> Reservation:
    """Create a reservation for a book if the member does not already have one or an active loan."""
    book = db.session.get(Book, book_id)
    if not book or book.is_archived:
        raise LibraryOperationError("Book is not available for reservation.")

    member = db.session.get(Member, member_id)
    if not member or member.status != "Active":
        raise LibraryOperationError("Active membership required to reserve books.")

    existing_res = Reservation.query.filter(
        Reservation.book_id == book_id,
        Reservation.member_id == member_id,
        Reservation.status.in_(["Pending", "Ready"]),
    ).first()
    if existing_res:
        raise LibraryOperationError("You already have an active reservation for this book.")

    existing_loan = (
        Loan.query.join(BookCopy)
        .filter(
            Loan.member_id == member_id,
            Loan.return_date.is_(None),
            BookCopy.book_id == book_id,
        )
        .first()
    )
    if existing_loan:
        raise LibraryOperationError("You already have an active loan for this book.")

    queue_count = Reservation.query.filter(
        Reservation.book_id == book_id,
        Reservation.status.in_(["Pending", "Ready"]),
    ).count()

    status = "Ready" if book.available_copies_count > 0 and queue_count == 0 else "Pending"

    try:
        res = Reservation(
            book_id=book_id,
            member_id=member_id,
            status=status,
            queue_position=queue_count + 1,
            notes=notes,
            is_demo=is_demo,
        )
        db.session.add(res)
        db.session.add(
            Notification(
                user_id=member.user_id,
                title="Book Reservation Confirmed",
                message=f"Reservation placed for '{book.title}' (Queue position #{queue_count + 1}, Status: {status}).",
                notification_type="reservation",
                is_demo=is_demo,
            )
        )
        db.session.commit()
        return res
    except SQLAlchemyError as exc:
        db.session.rollback()
        raise LibraryOperationError(f"Could not create reservation: {str(exc)}") from exc
