"""Extension instances, created here (not in app.py) so blueprints and
models can import them without a circular import on the Flask app itself."""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
