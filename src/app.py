from pathlib import Path

from flask import Flask, flash, redirect, request, url_for
from flask_wtf import CSRFProtect

from auth import auth_bp
from config import Config
from extensions import db, login_manager
from models import User
from pets import pets_bp


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
