from datetime import timedelta
import pytest
from app.extensions import db
from app.models import Book, BookCopy, Member, Loan, Reservation, Fine, Author, Publisher, Category, utcnow
from app.services.library_service import (
    LibraryOperationError,
    create_book_with_copies,
    add_physical_copy,
    issue_book_copy,
    return_book_copy,
    create_reservation,
)
from tests.conftest import login_as


def test_book_creation_editing_and_inventory_management(client, app):
    login_as(client, "admin_test", "AdminPass123")

    with app.app_context():
        author = Author.query.first()
        pub = Publisher.query.first()
        cat = Category.query.first()

        # Create book via service with 3 physical copies
        book = create_book_with_copies(
            isbn="978-1-23456-789-0",
            title="Software Quality Engineering",
            author_id=author.id,
            publisher_id=pub.id,
            category_id=cat.id,
            shelf_location="Q-101",
            initial_copies=3,
        )
        assert book.total_copies_count == 3
        assert book.available_copies_count == 3
        book_id = book.id
        a_id, p_id, c_id = author.id, pub.id, cat.id

    # Edit book via admin route
    resp = client.post(
        f"/admin/books/{book_id}",
        data={
            "isbn": "978-1-23456-789-0",
            "title": "Software Quality Engineering (Revised 2nd Ed.)",
            "subtitle": "TQM in Practice",
            "author_id": a_id,
            "publisher_id": p_id,
            "category_id": c_id,
            "publication_year": 2025,
            "edition": "2nd",
            "shelf_location": "Q-202",
            "description": "Updated edition.",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Software Quality Engineering (Revised 2nd Ed.)" in resp.data

    # Prevent negative copy creation
    with app.app_context():
        with pytest.raises(LibraryOperationError, match="negative"):
            create_book_with_copies(
                isbn="978-9-99999-999-9",
                title="Invalid Negative Inventory",
                author_id=a_id,
                publisher_id=p_id,
                category_id=c_id,
                initial_copies=-2,
            )


def test_issue_return_duplicate_prevention_and_unavailable_copy(app):
    with app.app_context():
        author = Author.query.first()
        pub = Publisher.query.first()
        cat = Category.query.first()
        m1 = Member.query.filter_by(membership_number="MEM-TEST-001").first()
        m2 = Member.query.filter_by(membership_number="MEM-TEST-002").first()

        book = create_book_with_copies(
            isbn="978-0-11111-222-3",
            title="Statistical Process Control",
            author_id=author.id,
            publisher_id=pub.id,
            category_id=cat.id,
            initial_copies=2,
        )
        copies = book.copies.order_by(BookCopy.id).all()
        copy1, copy2 = copies[0], copies[1]

        # 1. Issue copy1 to m1
        loan1 = issue_book_copy(
            copy_id=copy1.id,
            member_id=m1.id,
            loan_days=14,
            processing_time_seconds=31.5,
            standardized_checklist_verified=True,
        )
        assert loan1.status == "Active"
        assert copy1.status == "Issued"
        assert book.available_copies_count == 1

        # 2. Prevent issuing an already-issued (unavailable) copy to another member
        with pytest.raises(LibraryOperationError, match="cannot be issued"):
            issue_book_copy(copy_id=copy1.id, member_id=m2.id)

        # 3. Prevent duplicate active loan of the same book (even a different available copy!) to m1
        with pytest.raises(LibraryOperationError, match="Duplicate active loans"):
            issue_book_copy(copy_id=copy2.id, member_id=m1.id)

        # 4. Return copy1 on time -> status becomes Available, no fine
        returned_loan = return_book_copy(loan_id=loan1.id, return_condition="Good")
        assert returned_loan.status == "Returned"
        assert copy1.status == "Available"
        assert returned_loan.fine is None
        assert book.available_copies_count == 2

        # 5. Prevent invalid duplicate return of the same loan
        with pytest.raises(LibraryOperationError, match="already been returned"):
            return_book_copy(loan_id=loan1.id)


def test_due_dates_overdue_tracking_and_fine_calculation(app):
    with app.app_context():
        author = Author.query.first()
        pub = Publisher.query.first()
        cat = Category.query.first()
        m1 = Member.query.filter_by(membership_number="MEM-TEST-001").first()

        book = create_book_with_copies(
            isbn="978-0-33333-444-5",
            title="Kaizen Gemba Handbook",
            author_id=author.id,
            publisher_id=pub.id,
            category_id=cat.id,
            initial_copies=1,
        )
        copy = book.copies.first()

        now = utcnow()
        issued_at = now - timedelta(days=20)
        # Loan duration 14 days -> due 6 days ago
        loan = issue_book_copy(
            copy_id=copy.id,
            member_id=m1.id,
            loan_days=14,
            issue_date=issued_at,
        )
        assert loan.is_overdue is True
        assert loan.days_overdue == 6

        # Return now -> 6 days overdue, policy is $2.50/day -> $15.00 fine
        return_book_copy(loan_id=loan.id, return_condition="Good", return_date=now)
        assert loan.fine is not None
        assert loan.fine.amount == 15.00
        assert loan.fine.status == "Unpaid"


def test_reservations_waiting_list_and_member_isolation(client, app):
    with app.app_context():
        author = Author.query.first()
        pub = Publisher.query.first()
        cat = Category.query.first()
        m1 = Member.query.filter_by(membership_number="MEM-TEST-001").first()
        m2 = Member.query.filter_by(membership_number="MEM-TEST-002").first()

        book = create_book_with_copies(
            isbn="978-0-55555-666-7",
            title="Deming System of Profound Knowledge",
            author_id=author.id,
            publisher_id=pub.id,
            category_id=cat.id,
            initial_copies=1,
        )
        copy = book.copies.first()

        # Issue the only copy to m1
        loan = issue_book_copy(copy_id=copy.id, member_id=m1.id)
        loan_id = loan.id

        # m2 reserves the book -> should enter Pending queue #1
        res = create_reservation(book_id=book.id, member_id=m2.id)
        assert res.status == "Pending"
        assert res.queue_position == 1

        # Duplicate reservation by m2 is blocked
        with pytest.raises(LibraryOperationError, match="already have an active reservation"):
            create_reservation(book_id=book.id, member_id=m2.id)

        # When m1 returns the copy, m2's reservation automatically promotes to Ready!
        return_book_copy(loan_id=loan.id, return_condition="Good")
        db.session.refresh(res)
        assert res.status == "Ready"

    # Verify Member 2 cannot view Member 1's loan record via /member/loans/<loan_id>
    login_as(client, "student2", "StudPass123")
    forbidden_resp = client.get(f"/member/loans/{loan_id}")
    assert forbidden_resp.status_code == 403


def test_database_transaction_rollback_on_error(app, monkeypatch):
    """Verify that if an unexpected database failure occurs mid-issue, copy status is rolled back to Available."""
    with app.app_context():
        author = Author.query.first()
        pub = Publisher.query.first()
        cat = Category.query.first()
        m1 = Member.query.filter_by(membership_number="MEM-TEST-001").first()

        book = create_book_with_copies(
            isbn="978-0-77777-888-9",
            title="Transactional Integrity Test Book",
            author_id=author.id,
            publisher_id=pub.id,
            category_id=cat.id,
            initial_copies=1,
        )
        copy = book.copies.first()
        copy_id = copy.id

        from sqlalchemy.exc import SQLAlchemyError

        orig_commit = db.session.commit

        def failing_commit():
            raise SQLAlchemyError("Simulated commit failure")

        monkeypatch.setattr(db.session, "commit", failing_commit)
        with pytest.raises(LibraryOperationError, match="Transaction failed"):
            issue_book_copy(copy_id=copy_id, member_id=m1.id)

        monkeypatch.setattr(db.session, "commit", orig_commit)
        refreshed_copy = db.session.get(BookCopy, copy_id)
        assert refreshed_copy.status == "Available"
        assert Loan.query.filter_by(copy_id=copy_id).count() == 0
