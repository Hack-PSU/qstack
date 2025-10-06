import json
from os import environ as env

from authlib.integrations.flask_client import OAuth
from apiflask import APIFlask
from flask import redirect, render_template, session, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from server.config import APP_SECRET_KEY, FRONTEND_URL
import os

STATIC_FOLDER = "../client/dist"

app = APIFlask(
    __name__,
    docs_path=None,
    static_folder=STATIC_FOLDER,
    template_folder=STATIC_FOLDER,
    static_url_path="/",
)

db = SQLAlchemy()

app.secret_key = APP_SECRET_KEY
app.config.from_pyfile("config.py")

# Configure CORS for HackPSU auth integration
allowed_origins = [
    'https://auth.hackpsu.org',
    'https://hackpsu.org',
    'http://localhost:3000',  # Local HackPSU auth server
    FRONTEND_URL,
    os.environ.get('AUTH_SERVER_URL', '').replace('/api/sessionUser', '') if os.environ.get('AUTH_SERVER_URL') else None
]
allowed_origins = [origin for origin in allowed_origins if origin]  # Filter out None values

CORS(app,
     origins=allowed_origins,
     supports_credentials=True)


with app.app_context():
    from server.controllers import api

    app.register_blueprint(api)

    from server import models

    db.init_app(app)

    # Create tables using checkfirst to avoid conflicts
    # Wrapped in try/except to handle race conditions with multiple workers
    with app.app_context():
        try:
            db.create_all(checkfirst=True)
        except Exception as e:
            # Tables may already exist from another worker, continue
            app.logger.warning(f"Database tables may already exist: {e}")

    @app.errorhandler(404)
    def _default(_error):
        return render_template("index.html"), 200
