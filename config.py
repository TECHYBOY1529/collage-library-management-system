import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration with secure defaults."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-fallback-secret-key-change-in-production-987654321")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(basedir, "instance", "library_tqm.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session & CSRF Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    WTF_CSRF_ENABLED = True

    # Default Fine & Loan Policies
    DEFAULT_LOAN_DAYS = int(os.environ.get("DEFAULT_LOAN_DAYS", 14))
    DEFAULT_FINE_PER_DAY = float(os.environ.get("DEFAULT_FINE_PER_DAY", 2.00))


class TestingConfig(Config):
    """Testing configuration using isolated in-memory SQLite database."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret-key-only"
