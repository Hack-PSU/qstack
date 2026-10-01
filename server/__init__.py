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

    # Create tables if they don't exist.
    #
    # Every gunicorn worker runs this, so concurrent CREATE TABLE statements
    # race on boot -- hence the try/except. It is also only ever additive:
    # create_all never alters an existing table, so a column added to a model
    # later will not appear on a database that already has the table. Schema
    # changes beyond the first boot need applying by hand.
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            # Tables may already exist from another worker, continue
            app.logger.warning(f"Database tables may already exist: {e}")

    @app.route("/health")
    def _health():
        """
        Health check -- no auth required.

        Reports whether the database is reachable. The connection pool is lazy,
        so a misconfigured DATABASE_URL does not stop the container starting; it
        first shows up when a hacker tries to open a ticket. Surfacing it here
        lets a deploy refuse to send traffic to such a revision.

        Always returns 200: Cloud Run restarts instances that fail their probe,
        so reporting a transient database blip as unhealthy would turn a brief
        outage into a restart loop.
        """
        from sqlalchemy import text

        database = "ok"
        try:
            db.session.execute(text("SELECT 1"))
        except Exception as exc:
            database = "error: %s" % type(exc).__name__
            app.logger.warning("health check could not reach the database: %s", exc)
        finally:
            db.session.remove()

        return {"status": "ok", "service": "qstack", "database": database}, 200

    @app.errorhandler(404)
    def _default(_error):
        return render_template("index.html"), 200
