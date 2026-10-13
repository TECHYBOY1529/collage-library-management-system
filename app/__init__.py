import os
import click
from flask import Flask, render_template, redirect, url_for, flash
from config import Config
from app.extensions import db, migrate, csrf
from app.decorators import get_current_user, role_required
from app.models import Role, Notification


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    # Ensure instance folder exists for SQLite database
    os.makedirs(app.instance_path, exist_ok=True)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.member import member_bp
    from app.routes.quality import quality_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(quality_bp)
    app.register_blueprint(reports_bp)

    # Demo data management route for Admin
    @app.route("/admin/demo-data/<string:operation>", methods=["POST"])
    @role_required(Role.ADMIN)
    def manage_demo_data(operation):
        from seed import seed_demo_data, clear_demo_data_only

        if operation == "reseed":
            summary = seed_demo_data(reset_existing_demo=True)
            flash(
                f"Demo dataset regenerated safely ({summary['books']} demo books, {summary['members']} demo members, {summary['loans']} demo loans). Real user records were preserved.",
                "success",
            )
        elif operation == "clear":
            clear_demo_data_only()
            flash(
                "All labeled demonstration records removed safely. Real user data preserved.",
                "info",
            )
        return redirect(url_for("admin.audit_logs"))

    # Template context processor
    @app.context_processor
    def inject_globals():
        user = get_current_user()
        unread_count = 0
        if user:
            unread_count = Notification.query.filter_by(user_id=user.id, is_read=False).count()
        return {
            "current_user": user,
            "unread_notifications_count": unread_count,
            "Role": Role,
        }

    # Safe Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("errors/500.html"), 500

    # CLI Commands for Database Setup & Demo Seeding
    @app.cli.command("init-db")
    def init_db_command():
        """Create all database tables."""
        db.create_all()
        click.echo("Initialized the SQLite database tables.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Seed or reset labeled demonstration data safely."""
        db.create_all()
        from seed import seed_demo_data

        summary = seed_demo_data(reset_existing_demo=True)
        click.echo(f"Seeded demonstration data: {summary}")

    @app.cli.command("clear-demo")
    def clear_demo_command():
        """Remove only demonstration data while preserving real user records."""
        from seed import clear_demo_data_only

        clear_demo_data_only()
        click.echo("Cleared demonstration data safely.")

    return app
