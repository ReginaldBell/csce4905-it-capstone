from pathlib import Path

from flask import Flask, abort, flash, redirect, request, url_for
from flask_login import current_user
from flask_wtf import CSRFProtect

from auth import auth_bp
from community import community_bp
from community_schema import upgrade_community_command
from config import Config
from contacts import contacts_bp
from extensions import db, login_manager
from models import Pet, Report, ReportPet, User
from outputs import outputs_bp
from pets import pets_bp
from reports import reports_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

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
    app.cli.add_command(upgrade_community_command)

    @app.before_request
    def protect_uploaded_photos():
        filename = (request.view_args or {}).get("filename", "")
        if request.endpoint != "static" or not filename.startswith("uploads/"):
            return None
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        pet = Pet.query.filter_by(photo_path=filename).first()
        if pet is None:
            abort(404)
        if pet.owner_id != current_user.id:
            shared = (
                Report.query.join(ReportPet)
                .filter(
                    ReportPet.pet_id == pet.id,
                    Report.owner_id == pet.owner_id,
                    Report.is_shared.is_(True),
                )
                .first()
            )
            if shared is None:
                abort(404)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

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
