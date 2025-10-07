import functools
from urllib.parse import quote_plus, urlencode
import os

from apiflask import APIBlueprint, abort
from flask import current_app as app
from flask import redirect, request, session
from authlib.integrations.flask_client import OAuth


from server import db
from server.config import (
    FRONTEND_URL,
    BACKEND_URL,
    MENTOR_PASS,
    # AUTH0_CLIENT_ID,
    # AUTH0_CLIENT_SECRET,
    # AUTH0_DOMAIN,
    # AUTH_USERNAME,
    # AUTH_PASSWORD,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    AUTH_LOGIN_URL,
    AUTH_LOGOUT_URL
)
# Plume removed - using HackPSU Firebase auth
from server.models import User
from server.firebase_session_auth import (
    hackpsu_auth_required,
    hackpsu_admin_required,
    verify_hackpsu_session,
    sync_user_from_auth_server,
    check_access_permission
)
from server.hackpsu_api import get_user_info, get_my_info

auth = APIBlueprint("auth", __name__, url_prefix="/auth")
oauth = OAuth(app)

def is_user_valid(user, valid_roles):
    if not user or not user.role:
        return False
    elif user.role not in valid_roles:
        return False
    return True

oauth.register(
    "discord",
    client_id=DISCORD_CLIENT_ID,
    client_secret=DISCORD_CLIENT_SECRET,
    access_token_url="https://discord.com/api/oauth2/token",
    authorize_url="https://discord.com/api/oauth2/authorize",
    api_base_url="https://discord.com/api/",
    client_kwargs={"scope": "identify email"},
)

def auth_required_decorator(roles):
    """
    middleware for protected routes
    """

    def auth_required(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return abort(401)

            user = User.query.filter_by(id=session["user_id"]).first()
            if not user or not user.role:
                return abort(401)
            elif user.role not in roles:
                return abort(401)
            return func(*args, **kwargs)

        return wrapper

    return auth_required


@auth.route("/login")
def login():
    """Redirect to HackPSU Firebase auth login - or home if already logged in"""
    return_url = request.args.get("return_url", FRONTEND_URL + "/home")

    print(f"[DEBUG LOGIN] All cookies: {dict(request.cookies)}")
    print(f"[DEBUG LOGIN] Flask session: {dict(session)}")

    # Check if user is already logged in via Flask session
    if "user_id" in session:
        user = User.query.filter_by(id=session["user_id"]).first()
        if user:
            print(f"[DEBUG] User already logged in via session, redirecting to: {return_url}")
            return redirect(return_url)

    # Check if __session cookie exists and is valid
    session_cookie = request.cookies.get('__session')
    print(f"[DEBUG LOGIN] __session cookie exists: {session_cookie is not None}")

    if session_cookie:
        print(f"[DEBUG] __session cookie found (first 20 chars): {session_cookie[:20]}...")
        user_data = verify_hackpsu_session()
        print(f"[DEBUG] verify_hackpsu_session returned: {user_data}")

        if user_data:
            has_access = check_access_permission(user_data)
            print(f"[DEBUG] check_access_permission returned: {has_access}")

            if has_access:
                print("[DEBUG] Valid __session cookie, syncing user and redirecting")
                # Sync user and set session
                user = sync_user_from_auth_server(user_data)
                if user:
                    session["user_id"] = user.id
                    session["user_name"] = user_data.get("displayName", "User")
                    session["user_email"] = user_data.get("email", "")
                    print(f"[DEBUG] Session created for user {user.id}, redirecting to: {return_url}")
                    return redirect(return_url)
                else:
                    print("[DEBUG] Failed to sync user from auth server")
            else:
                print("[DEBUG] User does not have access permission")
        else:
            print("[DEBUG] verify_hackpsu_session returned None")

    # No valid session, redirect to auth login
    print("[DEBUG] No valid session, redirecting to auth server login")
    callback_url = f"{BACKEND_URL}/api/auth/callback?return_url={quote_plus(return_url)}"
    return redirect(f"{AUTH_LOGIN_URL}?returnTo={quote_plus(callback_url)}")


@auth.route("/callback", methods=["GET", "POST"])
def callback():
    """Handle Firebase auth callback - verify session and create/update user"""
    # Verify Firebase session
    user_data = verify_hackpsu_session()

    if not user_data:
        # Redirect to front page with login error
        return redirect(f"{FRONTEND_URL}/?error=login_failed&message=Authentication failed")

    # Create or update user in database
    user = sync_user_from_auth_server(user_data)

    if not user:
        return redirect(f"{FRONTEND_URL}/?error=login_failed&message=Failed to create user")

    # Set session variables
    session["user_id"] = user.id

    # Set name and email from JWT data (verified by auth server)
    session["user_name"] = user_data.get("displayName", "User")
    session["user_email"] = user_data.get("email", "")

    # Store the session token for API calls (this is the Firebase session JWT)
    # The client should send Firebase ID token separately for HackPSU API calls
    if 'session_token' in user_data:
        session['firebase_session_token'] = user_data['session_token']

    print(f"[DEBUG] Session set: name={session['user_name']}, email={session['user_email']}")

    # Get the return URL from query params, default to FRONTEND_URL/home
    return_url = request.args.get("return_url", FRONTEND_URL + "/home")
    return redirect(return_url)


@auth.route("/logout")
def logout():
    """Logout - call HackPSU auth logout endpoint and clear session"""
    import requests

    # Get the __session cookie to send to auth server
    session_cookie = request.cookies.get('__session')

    # Call HackPSU auth server to revoke Firebase session
    if session_cookie:
        try:
            response = requests.post(
                AUTH_LOGOUT_URL,
                cookies={'__session': session_cookie},
                timeout=5
            )
            print(f"[DEBUG] Auth server logout response: {response.status_code}")
        except Exception as e:
            print(f"[ERROR] Failed to call auth server logout: {e}")

    # Clear Flask session
    session.clear()

    # Redirect to frontend home
    qstack_url = os.environ.get('QSTACK_URL', FRONTEND_URL)
    return redirect(qstack_url)

@auth.route("/discord/login")
def discord_login():
    if "user_id" not in session:
        print("in here")
        return redirect(FRONTEND_URL + "/api/auth/login")

    return oauth.discord.authorize_redirect(
        redirect_uri=BACKEND_URL + "/api/auth/discord/callback"
    )

@auth.route("/discord/callback")
def discord_callback():
    """Handle Discord OAuth callback"""
    if "user_id" not in session:
        return redirect(FRONTEND_URL + "/api/auth/login")

    try:
        # Exchange authorization code for access token
        token = oauth.discord.authorize_access_token()

        # Get Discord user profile
        resp = oauth.discord.get("users/@me", token=token)
        profile = resp.json()

        # Extract Discord info
        discord_username = profile.get('username', '')
        discord_discriminator = profile.get('discriminator', '0')

        # Discord removed discriminators for most users, use new format
        if discord_discriminator == '0':
            discord_tag = discord_username
        else:
            discord_tag = f"{discord_username}#{discord_discriminator}"

        # Update user with Discord info
        user = User.query.filter_by(id=session["user_id"]).first()
        if user:
            user.discord = discord_tag
            db.session.commit()

        # Redirect back to home
        return redirect(FRONTEND_URL + "/home")

    except Exception as e:
        print(f"Discord OAuth error: {e}")
        return redirect(FRONTEND_URL + "/home?error=discord_failed")

@auth.route("/discord/exchange-token", methods=["POST"])
def discord_exchange_token():
    data = request.get_json()
    code = data.get("code")
    print("code", code)

    if not code:
        return abort(400, "Missing authorization code")

    # Check if user is logged in via Auth0 first
    if "user_id" not in session:
        return {"success": False, "error": "Must be logged first"}

    try:
        # Exchange code for token using the Discord OAuth client
        token = oauth.discord.fetch_access_token(
            code=code,
            redirect_uri=BACKEND_URL + "/api/auth/discord/callback"
        )
        print("got token", token)
        # Get Discord user profile
        resp = oauth.discord.get("users/@me", token=token)
        print("resp", resp)
        profile = resp.json()

        # Extract Discord info
        discord_username = profile.get('username', '')
        discord_discriminator = profile.get('discriminator', '0')

        # Discord removed discriminators for most users
        if discord_discriminator == '0':
            discord_tag = discord_username
        else:
            discord_tag = f"{discord_username}#{discord_discriminator}"

        user = User.query.filter_by(id=session["user_id"]).first()

        print("user", user)

        if not user:
            return {"success": False, "error": "User not found"}

        user.discord = discord_tag
        db.session.commit()
        print("user.discord", user.discord)
        return {"success": True, "discord_tag": discord_tag}

    except Exception as e:
        return {"success": False, "error": str(e)}



@auth.route("/set-firebase-token", methods=["POST"])
def set_firebase_token():
    """Store Firebase ID token in session for HackPSU API calls"""
    if "user_id" not in session:
        return {"error": "Not logged in"}, 401

    data = request.get_json()
    firebase_id_token = data.get("idToken")

    if not firebase_id_token:
        return {"error": "Missing idToken"}, 400

    # Store the Firebase ID token in session
    session["firebase_id_token"] = firebase_id_token
    print(f"[DEBUG] Stored Firebase ID token in session (length: {len(firebase_id_token)})")

    return {"success": True}


@auth.route("/whoami")
def whoami():
    """Get current user info - uses Firebase session verification"""
    # First check Flask session
    if "user_id" in session:
        user = User.query.filter_by(id=session["user_id"]).first()
        if user:
            return dict(user.map(), loggedIn=True)

    # Check if __session cookie exists
    if not request.cookies.get('__session'):
        return {"loggedIn": False}

    # Verify __session cookie with auth server
    user_data = verify_hackpsu_session()
    if user_data:
        # Check if user has access
        if not check_access_permission(user_data):
            return {"loggedIn": False, "error": "Insufficient permissions"}

        # Sync user and set session
        user = sync_user_from_auth_server(user_data)
        if user:
            session["user_id"] = user.id
            session["user_name"] = user_data.get("displayName", "User")
            session["user_email"] = user_data.get("email", "")

            return dict(user.map(), loggedIn=True)

    return {"loggedIn": False}


@auth.route("/update", methods=["POST"])
def update():
    if "user_id" not in session:
        return abort(401)

    user = User.query.filter_by(id=session["user_id"]).first()
    if not user:
        return abort(401)

    data = request.get_json()

    if data["role"] == "mentor" and user.role == "hacker":
        if "password" not in data:
            return abort(403, "Missing password!")
        elif data["password"] != MENTOR_PASS:
            return abort(403, "Incorrect password!")
        user.role = "mentor"

    if data["role"] == "hacker":
        user.role = "hacker"

    # if len(data["name"]) == 0:
    #     return abort(400, "Missing name!")
    # session["user_name"] = data["name"]

    if data["location"] == "virtual" and len(data["zoomlink"]) == 0:
        return abort(400, "Missing video call link!")

    if len(data["discord"]) == 0:
        return abort(400, "Missing discord!")

    user.location = data["location"]
    user.zoomlink = data["zoomlink"]
    user.discord = data["discord"]
    db.session.commit()
    return {"message": "Your information has been updated!"}
