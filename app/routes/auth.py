import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models import User, Member, Role
from app.forms import LoginForm, RegisterForm
from app.decorators import get_current_user
from app.services.audit_service import log_audit

auth_bp = Blueprint("auth", __name__)


def _redirect_for_role(user: User):
    if user.role == Role.ADMIN:
        return redirect(url_for("admin.dashboard"))
    if user.role == Role.QUALITY:
        return redirect(url_for("quality.dashboard"))
    return redirect(url_for("member.dashboard"))


@auth_bp.route("/")
def index():
    user = get_current_user()
    if user:
        return _redirect_for_role(user)
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    user = get_current_user()
    if user:
        return _redirect_for_role(user)

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        candidate = User.query.filter_by(username=username).first()
        if candidate and candidate.is_active and candidate.check_password(form.password.data):
            session.clear()
            session["user_id"] = candidate.id
            session["role"] = candidate.role
            session.permanent = True
            log_audit(
                action="USER_LOGIN",
                entity_type="User",
                entity_id=candidate.id,
                details=f"User '{candidate.username}' logged in with role '{candidate.role}'.",
                actor=candidate,
                is_demo=candidate.is_demo,
                commit=True,
            )
            flash(f"Welcome back, {candidate.full_name}!", "success")
            return _redirect_for_role(candidate)
        flash("Invalid username or password, or account is inactive.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    user = get_current_user()
    if user:
        return _redirect_for_role(user)

    form = RegisterForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        email = form.email.data.strip().lower()

        if User.query.filter_by(username=username).first():
            flash("Username is already taken. Please choose another.", "danger")
            return render_template("auth/register.html", form=form)
        if User.query.filter_by(email=email).first():
            flash("Email address is already registered.", "danger")
            return render_template("auth/register.html", form=form)

        try:
            new_user = User(
                username=username,
                email=email,
                full_name=form.full_name.data.strip(),
                role=Role.MEMBER,
                is_active=True,
                is_demo=False,
            )
            new_user.set_password(form.password.data)
            db.session.add(new_user)
            db.session.flush()

            membership_number = f"MEM-{new_user.id:04d}-{uuid.uuid4().hex[:4].upper()}"
            max_books = 6 if form.member_type.data in ("Faculty", "Researcher") else 4
            member = Member(
                user_id=new_user.id,
                membership_number=membership_number,
                department=form.department.data.strip(),
                member_type=form.member_type.data,
                phone=form.phone.data.strip() if form.phone.data else None,
                max_books_allowed=max_books,
                status="Active",
                is_demo=False,
            )
            db.session.add(member)
            log_audit(
                action="MEMBER_REGISTER",
                entity_type="Member",
                entity_id=membership_number,
                details=f"Registered new member '{new_user.full_name}' ({membership_number}).",
                actor=new_user,
                is_demo=False,
            )
            db.session.commit()
            flash(
                f"Registration successful! Your Membership ID is {membership_number}. Please log in.",
                "success",
            )
            return redirect(url_for("auth.login"))
        except SQLAlchemyError:
            db.session.rollback()
            flash("An unexpected database error occurred during registration.", "danger")

    return render_template("auth/register.html", form=form)


@auth_bp.route("/logout", methods=["POST", "GET"])
def logout():
    user = get_current_user()
    if user:
        log_audit(
            action="USER_LOGOUT",
            entity_type="User",
            entity_id=user.id,
            details=f"User '{user.username}' logged out.",
            actor=user,
            is_demo=user.is_demo,
            commit=True,
        )
    session.clear()
    flash("You have been logged out safely.", "info")
    return redirect(url_for("auth.login"))
