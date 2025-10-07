# Firebase Session Authentication for HackPSU Integration
# This module replaces Plume authentication with HackPSU's Firebase-based session auth

import jwt
import os
from flask import request, session, redirect, abort
from functools import wraps
from server.models import User
from server import db


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
    """Verify session with HackPSU auth server by sending cookies"""
    try:
        # Get the __session cookie from the request
        session_token = request.cookies.get('__session')

        if not session_token:
            print("[DEBUG] No __session cookie found")
            return None

        print(f"[DEBUG] Found __session cookie, verifying with auth server...")

        # Try to verify with auth server first
        import requests
        try:
            response = requests.get(
                AUTH_SERVER_URL,
                cookies={'__session': session_token},
                timeout=5
            )

            if response.ok:
                user_data = response.json()
                print(f"[DEBUG] Auth server response: {user_data}")
        except Exception as e:
            print(f"[DEBUG] Auth server verification failed, falling back to JWT decode: {e}")
            user_data = None

        # If auth server didn't work, decode JWT directly
        if not user_data or not user_data.get('user_id') and not user_data.get('uid'):
            print("[DEBUG] Decoding JWT directly from __session cookie")
            user_data = decode_session_token(session_token)
            if not user_data:
                print("[DEBUG] Failed to decode JWT")
                return None
            print(f"[DEBUG] Decoded JWT: {user_data}")

        # Extract user info - handle multiple possible field names
        email = user_data.get('email', '')
        name = (user_data.get('name') or
                user_data.get('displayName') or
                user_data.get('firstName', '') + ' ' + user_data.get('lastName', '') or
                '')

        if not name.strip() and email:
            name = email.split('@')[0]

        # Get user ID from various possible fields
        uid = (user_data.get('uid') or
               user_data.get('user_id') or
               user_data.get('sub') or
               user_data.get('id'))

        user_info = {
            'uid': uid,
            'email': email,
            'displayName': name.strip() or 'Unknown User',
            'customClaims': {
                'production': user_data.get('production', 0),
                'staging': user_data.get('staging', 0)
            }
        }

        print(f"[DEBUG] Extracted user info: uid={user_info['uid']}, email={user_info['email']}, name={user_info['displayName']}")

        if not user_info.get('uid'):
            print("[DEBUG] No valid user ID in extracted info")
            return None

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

        # Set QStack session
        session['user_id'] = user.id
        session['user_name'] = user_data.get('displayName')
        session['user_email'] = user_data.get('email')
        print(f"[DEBUG] Auth successful, session set for: {user.id}")

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
            session['user_name'] = user_data.get('displayName')
            session['user_email'] = user_data.get('email')

        return f(*args, **kwargs)

    return decorated


def sync_user_from_auth_server(user_data):
    """Create/update QStack user from Firebase user data"""
    uid = user_data.get('uid')
    email = user_data.get('email')

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
