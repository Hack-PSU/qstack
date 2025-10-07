# Firebase Session Authentication for HackPSU Integration
# This module replaces Plume authentication with HackPSU's Firebase-based session auth

import jwt
import os
from flask import request, session, redirect, abort
from functools import wraps
from server.models import User
from server import db
from server.hackpsu_api import get_user_info, get_my_info


AUTH_SERVER_URL = os.environ.get('AUTH_SERVER_URL', 'http://localhost:3000/api/sessionUser')
MIN_JUDGE_ROLE = 2  # Minimum role for basic access
MIN_ADMIN_ROLE = 4  # Minimum role for admin access

"""
Role Levels (from HackPSU NestJS backend):
0 = NONE (no access)
1 = HACKER (participant)
2 = ORGANIZER (can judge/help) ← Minimum for QStack access
3 = EXECUTIVE (can judge + more admin features)
4 = ADMIN (full access) ← Minimum for admin panel
"""


def decode_session_token(token_string):
    """Decode Firebase session JWT token without verification"""
    try:
        # Decode without verification (we trust the session cookie from our auth server)
        decoded = jwt.decode(token_string, options={"verify_signature": False})
        print(f"[DEBUG] Decoded token: {decoded}")
        return decoded
    except Exception as e:
        print(f"[ERROR] Failed to decode token: {e}")
        return None


def verify_hackpsu_session():
    """Verify session with HackPSU auth server and decode JWT for uid"""
    try:
        # Get the __session cookie from the request
        session_token = request.cookies.get('__session')

        if not session_token:
            print("[DEBUG] No __session cookie found")
            return None

        print(f"[DEBUG] Found __session cookie, verifying with auth server...")

        # First, verify with auth server to ensure session is valid
        import requests
        try:
            response = requests.get(
                AUTH_SERVER_URL,
                cookies={'__session': session_token},
                timeout=5
            )

            if not response.ok:
                print(f"[DEBUG] Auth server returned {response.status_code}")
                return None

            auth_server_data = response.json()
            print(f"[DEBUG] Auth server validation successful")
        except Exception as e:
            print(f"[DEBUG] Auth server verification failed: {e}")
            return None

        # Decode JWT to get uid and custom claims (auth server doesn't return these)
        jwt_data = decode_session_token(session_token)
        if not jwt_data:
            print("[DEBUG] Failed to decode JWT")
            return None

        print(f"[DEBUG] Decoded JWT: {jwt_data}")

        # Extract user ID from JWT (uid field is the Firebase UID)
        uid = jwt_data.get('uid') or jwt_data.get('user_id') or jwt_data.get('sub')

        if not uid:
            print("[DEBUG] No uid found in JWT")
            return None

        # Extract user info from JWT
        email = jwt_data.get('email', '')
        name = (jwt_data.get('name') or
                jwt_data.get('displayName') or
                '')

        if not name.strip() and email:
            name = email.split('@')[0]

        # Extract custom claims for role/privilege
        user_info = {
            'uid': uid,
            'email': email,
            'displayName': name.strip() or 'Unknown User',
            'customClaims': {
                'production': jwt_data.get('production', 0),
                'staging': jwt_data.get('staging', 0)
            },
            'session_token': session_token  # Store session token for later use
        }

        print(f"[DEBUG] Extracted user info: uid={user_info['uid']}, email={user_info['email']}, name={user_info['displayName']}, claims={user_info['customClaims']}")

        return user_info

    except Exception as e:
        print(f"[ERROR] Session verification failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_user_privilege(user_data):
    """Extract role level from Firebase custom claims"""
    # Get AUTH_ENVIRONMENT from config (production or staging)
    auth_env = os.environ.get('AUTH_ENVIRONMENT', 'production')

    # Custom claims are in the user data
    custom_claims = user_data.get('customClaims', {})

    # Extract privilege for current environment
    privilege = custom_claims.get(auth_env, 0)

    return privilege


def check_access_permission(user_data):
    """Check if user has sufficient privileges to access QStack (role >= 2)"""
    privilege = extract_user_privilege(user_data)
    min_role = int(os.environ.get('MIN_ACCESS_ROLE', MIN_JUDGE_ROLE))
    return privilege >= min_role


def check_admin_permission(user_data):
    """Check if user has admin privileges (role >= 4)"""
    privilege = extract_user_privilege(user_data)
    min_role = int(os.environ.get('MIN_ADMIN_ROLE', MIN_ADMIN_ROLE))
    return privilege >= min_role


def hackpsu_auth_required(f):
    """Require HackPSU authentication with basic access permissions"""
    @wraps(f)
    def decorated(*args, **kwargs):
        print(f"[DEBUG] Auth required for route: {request.path}")
        print(f"[DEBUG] Cookies: {list(request.cookies.keys())}")

        # Check if already authenticated in Flask session
        if 'user_id' in session:
            user = User.query.filter_by(id=session['user_id']).first()
            if user:
                print(f"[DEBUG] User already authenticated via Flask session: {user.id}")
                return f(*args, **kwargs)

        # Check if __session cookie exists
        if not request.cookies.get('__session'):
            print("[DEBUG] No __session cookie, redirecting to login")
            auth_login_url = os.environ.get('AUTH_LOGIN_URL', 'http://localhost:3000/login')
            from server.config import FRONTEND_URL
            redirect_url = f'{auth_login_url}?returnTo={FRONTEND_URL}'
            return redirect(redirect_url)

        # Verify __session cookie with auth server
        print("[DEBUG] __session cookie found, verifying with auth server...")
        user_data = verify_hackpsu_session()

        if not user_data:
            print("[DEBUG] __session cookie invalid or expired, redirecting to login")
            auth_login_url = os.environ.get('AUTH_LOGIN_URL', 'http://localhost:3000/login')
            from server.config import FRONTEND_URL
            redirect_url = f'{auth_login_url}?returnTo={FRONTEND_URL}'
            return redirect(redirect_url)

        print(f"[DEBUG] User data received: {user_data.get('email')}")

        # Check if user has sufficient privileges
        if not check_access_permission(user_data):
            privilege = extract_user_privilege(user_data)
            print(f"[DEBUG] Insufficient privileges: {privilege} < {os.environ.get('MIN_ACCESS_ROLE', MIN_JUDGE_ROLE)}")
            return {
                'error': f'You need organizer permissions (level 2+) to access QStack. Your current level: {privilege}'
            }, 403

        # Get or create QStack user
        user = sync_user_from_auth_server(user_data)
        if not user:
            print(f"[DEBUG] User creation failed")
            return {
                'error': 'Failed to create user account. Please contact an admin.'
            }, 403

        # Set QStack session with data from JWT
        session['user_id'] = user.id
        session['user_name'] = user_data.get('displayName', 'User')
        session['user_email'] = user_data.get('email', '')

        print(f"[DEBUG] Auth successful, session set for: {user.id}")

        # Check if Discord is connected
        if not user.discord or user.discord.strip() == '':
            print(f"[DEBUG] User {user.id} has no Discord connected, needs to connect")
            from server.config import FRONTEND_URL
            # Return JSON response indicating Discord is required
            # Frontend will handle showing the connect screen
            return {
                'error': 'discord_required',
                'message': 'Please connect your Discord account to continue',
                'redirect': f'{FRONTEND_URL}/connect-discord'
            }, 403

        return f(*args, **kwargs)

    return decorated


def hackpsu_admin_required(f):
    """Require HackPSU authentication with admin permissions"""
    @wraps(f)
    def decorated(*args, **kwargs):
        user_data = verify_hackpsu_session()

        if not user_data:
            auth_login_url = os.environ.get('AUTH_LOGIN_URL', 'http://localhost:3000/login')
            return redirect(f'{auth_login_url}?returnTo={request.url}')

        # Check admin permissions
        if not check_admin_permission(user_data):
            return {
                'error': 'Admin access required. You need permission level 4+.'
            }, 403

        # Still set user session for admin
        user = sync_user_from_auth_server(user_data)
        if user:
            session['user_id'] = user.id
            session['user_name'] = user_data.get('displayName', 'User')
            session['user_email'] = user_data.get('email', '')

        return f(*args, **kwargs)

    return decorated


def sync_user_from_auth_server(user_data):
    """Create/update QStack user from Firebase user data"""
    uid = user_data.get('uid')

    if not uid:
        return None

    # Map role level to QStack role
    privilege = extract_user_privilege(user_data)

    # Default role mapping
    if privilege >= 3:
        role = 'admin'
    elif privilege >= 2:
        role = 'mentor'  # Organizers can help others
    else:
        role = 'hacker'

    # Find existing user by ID
    user = User.query.filter_by(id=uid).first()

    if not user:
        # Create new user
        user = User(
            id=uid,
            role=role,
            location='in person',
            zoomlink='',
            discord=''
        )
        db.session.add(user)
        db.session.commit()
        print(f"[DEBUG] Created new user: {uid} with role {role}")
    else:
        # Update existing user role if privilege changed
        if user.role != role:
            user.role = role
            db.session.commit()
            print(f"[DEBUG] Updated user role: {uid} -> {role}")

    return user
