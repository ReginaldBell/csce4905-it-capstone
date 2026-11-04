import os


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
