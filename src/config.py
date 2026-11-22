import os


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Config:
    """Application configuration, read from environment variables so the
    same image runs in dev (docker compose) and later environments without
    code changes."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    # Explicit +psycopg2 dialect: SQLAlchemy's default driver for a bare
    # "postgresql://" URL depends on what's importable at runtime, and this
    # project installs psycopg2-binary, not psycopg (v3).
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://petfinder:petfinder@db:5432/petfinder"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Where pet photos are written to disk. Served back out via Flask's
    # static route, so this must stay inside static/.
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "uploads"),
    )

    # 5 MB cap on any uploaded file, enforced by Flask itself (returns 413
    # before the view even runs) as well as the explicit check in pets.py.
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png"}
    ALLOWED_PHOTO_MIMETYPES = {"image/jpeg", "image/png"}

    # Password reset. APP_BASE_URL (for example https://pets.example.test) is
    # required outside debug/testing, so links never trust the Host header.
    PASSWORD_RESET_TTL_MINUTES = _env_int("PASSWORD_RESET_TTL_MINUTES", 60)
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "")

    # Mail: console (default, debug/testing only), memory (tests), or smtp.
    MAIL_BACKEND = os.environ.get("MAIL_BACKEND") or "console"
    MAIL_HOST = os.environ.get("MAIL_HOST") or "localhost"
    MAIL_PORT = _env_int("MAIL_PORT", 587)
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM") or "no-reply@petfinder.example.test"
    MAIL_USE_TLS = (os.environ.get("MAIL_USE_TLS") or "true").lower() in (
        "1",
        "true",
        "yes",
    )

    # Request limits (NF14).
    LOGIN_LIMIT = _env_int("LOGIN_LIMIT", 5)
    LOGIN_WINDOW_SECONDS = _env_int("LOGIN_WINDOW_SECONDS", 900)
    RESET_LIMIT = _env_int("RESET_LIMIT", 3)
    RESET_WINDOW_SECONDS = _env_int("RESET_WINDOW_SECONDS", 3600)
