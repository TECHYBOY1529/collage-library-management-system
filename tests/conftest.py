import pytest
from app import create_app
from app.extensions import db
from app.models import Role, User, Member, Author, Publisher, Category, FinePolicy
from config import TestingConfig


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()

        # Default Fine Policy
        policy = FinePolicy(
            name="Test Policy",
            loan_duration_days=14,
            fine_per_day=2.50,
            grace_period_days=1,
            max_fine_cap=50.00,
            is_active=True,
        )
        db.session.add(policy)

        # Admin User
        admin = User(
            username="admin_test",
            email="admin@test.edu",
            full_name="Test Librarian",
            role=Role.ADMIN,
            is_active=True,
        )
        admin.set_password("AdminPass123")
        db.session.add(admin)

        # Quality Manager User
        qm = User(
            username="qm_test",
            email="qm@test.edu",
            full_name="Test Quality Manager",
            role=Role.QUALITY,
            is_active=True,
        )
        qm.set_password("QmPass123")
        db.session.add(qm)

        # Two Member Users
        m1_user = User(
            username="student1",
            email="s1@test.edu",
            full_name="Student One",
            role=Role.MEMBER,
            is_active=True,
        )
        m1_user.set_password("StudPass123")
        db.session.add(m1_user)

        m2_user = User(
            username="student2",
            email="s2@test.edu",
            full_name="Student Two",
            role=Role.MEMBER,
            is_active=True,
        )
        m2_user.set_password("StudPass123")
        db.session.add(m2_user)
        db.session.flush()

        m1 = Member(
            user_id=m1_user.id,
            membership_number="MEM-TEST-001",
            department="Computer Science",
            member_type="Student",
            max_books_allowed=3,
            status="Active",
        )
        m2 = Member(
            user_id=m2_user.id,
            membership_number="MEM-TEST-002",
            department="Mathematics",
            member_type="Student",
            max_books_allowed=3,
            status="Active",
        )
        db.session.add_all([m1, m2])

        # Base Author, Publisher, Category
        author = Author(name="Dr. Alan Turing")
        pub = Publisher(name="University Press")
        cat = Category(name="Computer Science", code="CS")
        db.session.add_all([author, pub, cat])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_as(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )
