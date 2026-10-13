from functools import wraps
from flask import session, redirect, url_for, flash, abort, g
from app.extensions import db
from app.models import User, Role


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    user = db.session.get(User, user_id)
    if user and not user.is_active:
        session.clear()
        return None
    return user


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if user is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)

    return decorated_function


def role_required(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if user is None:
                flash("Please log in to access this page.", "warning")
                return redirect(url_for("auth.login"))
            if user.role not in allowed_roles:
                abort(403)
            return f(*args, **kwargs)

        return decorated_function

    return decorator
