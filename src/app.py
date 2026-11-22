import posixpath
from pathlib import Path

from flask import Flask, abort, flash, redirect, request, url_for
from flask_login import current_user
from flask_wtf import CSRFProtect

from auth import auth_bp
from community import community_bp
from community_schema import upgrade_community_command
from config import Config
from contacts import contacts_bp
from demo_data import seed_community_demo_command
from extensions import db, login_manager
from models import Pet, Report, ReportPet, User
from outputs import outputs_bp
from pets import pets_bp
from reports import reports_bp
from settings import settings_bp
from sprint3_schema import upgrade_sprint3_command


def _normalized_upload_path(filename):
    """Return "uploads/<file>" if a static filename resolves inside uploads/.

    Authorization must use this form: "./uploads/a.png", "x/../uploads/a.png",
    and backslash or repeated-slash spellings all reach the same file. Case and
    trailing dots or spaces are ignored on the folder name because some
    filesystems (Windows, Docker Desktop mounts) treat those as the same folder.
    """
    normalized = posixpath.normpath(filename.replace("\\", "/")).lstrip("/")
    folder, _, rest = normalized.partition("/")
    if folder.rstrip(". ").casefold() != "uploads":
        return None
    return f"uploads/{rest}"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    app.extensions.setdefault("mail_outbox", [])

    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Log in to continue."
    login_manager.login_message_category = "info"

    CSRFProtect(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(pets_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(contacts_bp)
    app.register_blueprint(outputs_bp)
    app.register_blueprint(community_bp)
    app.register_blueprint(settings_bp)
    app.cli.add_command(upgrade_community_command)
    app.cli.add_command(seed_community_demo_command)
    app.cli.add_command(upgrade_sprint3_command)

    @app.before_request
    def protect_uploaded_photos():
        if request.endpoint != "static":
            return None
        photo_path = _normalized_upload_path(
            (request.view_args or {}).get("filename", "")
        )
        if photo_path is None:
            return None
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        pet = Pet.query.filter_by(photo_path=photo_path).first()
        if pet is None:
            abort(404)
        if pet.owner_id != current_user.id:
            shared = (
                Report.query.join(ReportPet)
                .filter(
                    ReportPet.pet_id == pet.id,
                    Report.owner_id == pet.owner_id,
                    Report.is_shared.is_(True),
                    Report.status == "open",
                )
                .first()
            )
            if shared is None:
                abort(404)

    @login_manager.user_loader
    def load_user(user_id):
        # "<id>:<version>", or a legacy "<id>" session, which counts as version 1.
        raw_id, _, raw_version = str(user_id).partition(":")
        try:
            user = db.session.get(User, int(raw_id))
            version = int(raw_version) if raw_version else 1
        except ValueError:
            return None
        if user is None or user.session_version != version:
            return None
        return user

    @app.errorhandler(413)
    def photo_too_large(_error):
        # MAX_CONTENT_LENGTH rejects an oversized upload before the view
        # (and its inline field-error handling) ever runs. Surface the same
        # message as a flash instead of Werkzeug's bare error page.
        flash("Photo must be 5 MB or smaller.", "error")
        return redirect(request.referrer or url_for("pets.list_pets"))

    @app.cli.command("init-db")
    def init_db():
        """Create all tables. Run once against a fresh database:
        docker compose exec web flask init-db
        """
        db.create_all()
        print("Database tables created.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0")
