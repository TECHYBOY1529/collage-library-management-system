from tests.conftest import login_as
from app.models import User, Member, AuditLog


def test_member_registration_and_login_logout(client, app):
    # Register a new member
    resp = client.post(
        "/register",
        data={
            "username": "new_scholar",
            "email": "scholar@college.edu",
            "full_name": "New Scholar",
            "department": "Physics",
            "member_type": "Researcher",
            "phone": "1234567890",
            "password": "SecurePassword9",
            "confirm_password": "SecurePassword9",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Registration successful" in resp.data

    with app.app_context():
        u = User.query.filter_by(username="new_scholar").first()
        assert u is not None
        assert u.password_hash != "SecurePassword9"
        assert u.check_password("SecurePassword9")
        assert u.member_profile is not None
        assert u.member_profile.max_books_allowed == 6

    # Login as the newly registered member
    login_resp = login_as(client, "new_scholar", "SecurePassword9")
    assert login_resp.status_code == 200
    assert b"Member Portal" in login_resp.data

    # Logout
    logout_resp = client.get("/logout", follow_redirects=True)
    assert b"logged out safely" in logout_resp.data


def test_role_based_access_control_enforcement(client):
    # Unauthenticated user redirected to login
    resp = client.get("/admin/dashboard", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    # Member cannot access Admin or Quality Manager routes
    login_as(client, "student1", "StudPass123")
    assert client.get("/admin/dashboard").status_code == 403
    assert client.get("/admin/books").status_code == 403
    assert client.get("/quality/dashboard").status_code == 403
    assert client.get("/reports/").status_code == 403
    client.get("/logout")

    # Quality Manager can access Quality and Reports, but NOT Admin-only routes
    login_as(client, "qm_test", "QmPass123")
    assert client.get("/quality/dashboard").status_code == 200
    assert client.get("/reports/").status_code == 200
    assert client.get("/admin/dashboard").status_code == 403
    assert client.get("/admin/fines").status_code == 403
    client.get("/logout")

    # Admin can access Admin, Quality, and Reports
    login_as(client, "admin_test", "AdminPass123")
    assert client.get("/admin/dashboard").status_code == 200
    assert client.get("/quality/dashboard").status_code == 200
    assert client.get("/reports/").status_code == 200


def test_input_validation_and_audit_password_redaction(client, app):
    # Invalid registration email & mismatched passwords
    resp = client.post(
        "/register",
        data={
            "username": "ab",
            "email": "not-an-email",
            "full_name": "X",
            "department": "",
            "member_type": "Student",
            "password": "123",
            "confirm_password": "456",
        },
        follow_redirects=True,
    )
    assert b"Invalid email address format" in resp.data
    assert b"Passwords must match" in resp.data

    # Verify audit logs never store raw passwords
    login_as(client, "admin_test", "AdminPass123")
    with app.app_context():
        logs = AuditLog.query.all()
        assert len(logs) > 0
        for log in logs:
            assert "AdminPass123" not in log.details
