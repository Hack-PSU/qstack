import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(os.path.dirname(__file__) / Path("../.env"))

# from flaskenv
FLASK_RUN_PORT = 3001
DEBUG = True

# CORS configuration
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:6001")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:3001")
ALLOWED_DOMAINS = [BACKEND_URL]

SQLALCHEMY_DATABASE_URI = os.environ.get(
    "SQLALCHEMY_DATABASE_URI", "postgresql://postgres:password@database/qstackdb"
)

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
