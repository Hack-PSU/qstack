import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.dirname(__file__) / Path("../.env"))

# from flaskenv
#
# PORT is what Cloud Run injects and routes to; 3001 stays the local default.
FLASK_RUN_PORT = int(os.environ.get("PORT", 3001))

# DEBUG was unconditionally True, and this file is loaded straight into the app
# config, so production ran with debug on: exceptions propagate instead of being
# handled, template auto-reload stays active, and caching is disabled. Default
# off and opt in locally.
DEBUG = os.environ.get("DEBUG", "false").lower() in ("1", "true", "yes")

# CORS configuration
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:6001")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:3001")
ALLOWED_DOMAINS = [BACKEND_URL]

def _mysql_uri_from_parts():
    """
    Build a database URI from the MYSQL_* variables, the way apiv3 does.

    Cloud Run injects each from its own Secret Manager entry, so the database
    password lives in exactly one secret shared by every service rather than
    being duplicated into a second secret holding a whole URL -- which would
    then have to be rotated in two places.

    Returns None unless all the parts are present, so an explicit
    SQLALCHEMY_DATABASE_URI still wins everywhere else.
    """
    user = os.environ.get("MYSQL_USER")
    password = os.environ.get("MYSQL_PASSWORD")
    database = os.environ.get("MYSQL_DATABASE")
    if not (user and password and database):
        return None

    from urllib.parse import quote_plus

    credentials = "%s:%s" % (quote_plus(user), quote_plus(password))

    socket_path = os.environ.get("MYSQL_SOCKET_PATH")
    if socket_path:
        # Cloud Run mounts the Cloud SQL socket rather than exposing a host, so
        # there is no netloc -- the path goes in a query parameter.
        return "mysql+pymysql://%s@/%s?unix_socket=%s" % (
            credentials, database, quote_plus(socket_path))

    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    port = os.environ.get("MYSQL_PORT", "3306")
    return "mysql+pymysql://%s@%s:%s/%s" % (credentials, host, port, database)


SQLALCHEMY_DATABASE_URI = (
    os.environ.get("SQLALCHEMY_DATABASE_URI")
    or _mysql_uri_from_parts()
    or "postgresql://postgres:password@database/qstackdb"
)

SQLALCHEMY_TRACK_MODIFICATIONS = False

# Connection pooling, sized against the database rather than the app.
#
# The shared Cloud SQL instance allows 280 connections in total and already
# serves apiv3 and gavel. Each gunicorn worker keeps its own pool, so the
# ceiling is (instances x workers x (pool_size + max_overflow)); keeping the
# per-worker figure small bounds the total. SQLAlchemy's defaults (5 + 10)
# would let a handful of workers monopolise the instance.
SQLALCHEMY_ENGINE_OPTIONS = {
    "pool_size": int(os.environ.get("DB_POOL_SIZE", 5)),
    "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", 2)),
    # Cloud SQL drops idle connections, and a pooled connection that died while
    # idle surfaces as a failed request.
    "pool_pre_ping": True,
    "pool_recycle": int(os.environ.get("DB_POOL_RECYCLE", 1800)),
}

# AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID")
# AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET")
# AUTH_USERNAME = os.environ.get("AUTH_USERNAME")
# AUTH_PASSWORD = os.environ.get("AUTH_PASSWORD")
# AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN")
APP_SECRET_KEY = os.environ.get("APP_SECRET_KEY")
MENTOR_PASS = os.environ.get("MENTOR_PASS")
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")

# HackPSU Firebase Authentication Configuration
AUTH_ENVIRONMENT = os.environ.get("AUTH_ENVIRONMENT", "production")
MIN_ACCESS_ROLE = int(os.environ.get("MIN_ACCESS_ROLE", "2"))
MIN_ADMIN_ROLE = int(os.environ.get("MIN_ADMIN_ROLE", "4"))
AUTH_SERVER_URL = os.environ.get("AUTH_SERVER_URL", "http://localhost:3000/api/sessionUser")
AUTH_LOGIN_URL = os.environ.get("AUTH_LOGIN_URL", "http://localhost:3000/login")
AUTH_LOGOUT_URL = os.environ.get("AUTH_LOGOUT_URL", "http://localhost:3000/api/sessionLogout")

ENV = os.environ.get("ENVIRONMENT", "development")

AUTH_ADMINS = [
    {"name": "HackPSU", "email": "admin@hackpsu.org"},
    {"name": "HackPSU", "email": "team@hackpsu.org"},
]
