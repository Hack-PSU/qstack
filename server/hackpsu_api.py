# HackPSU API Client
# Replaces Plume for fetching user information

import requests
import os
from typing import Dict, List, Optional
from flask import request

HACKPSU_API_URL = os.environ.get('HACKPSU_API_URL', 'https://apiv3.hackpsu.org')
FIREBASE_API_KEY = os.environ.get('FIREBASE_API_KEY')


def get_firebase_id_token_from_session_cookie() -> Optional[str]:
    """Get Firebase ID token by exchanging session cookie with auth server

    The auth server's /api/sessionUser endpoint verifies the session cookie
    and returns a custom token. We then exchange this with Firebase Auth
    to get a proper ID token for API calls.
    """
    from server.config import AUTH_SERVER_URL

    session_cookie = request.cookies.get('__session')
    if not session_cookie:
        print("[DEBUG] No __session cookie found")
        return None

    try:
        # Step 1: Call auth server to get custom token
        auth_base_url = AUTH_SERVER_URL.replace('/api/sessionUser', '')
        session_user_url = f"{auth_base_url}/api/sessionUser"

        print(f"[DEBUG] Fetching custom token from {session_user_url}")
        response = requests.get(
            session_user_url,
            cookies={'__session': session_cookie},
            timeout=5
        )

        if not response.ok:
            print(f"[DEBUG] Auth server returned {response.status_code}: {response.text[:200]}")
            return None

        data = response.json()
        custom_token = data.get('customToken')
        if not custom_token:
            print("[DEBUG] No customToken in response")
            return None

        print(f"[DEBUG] Got custom token from auth server (length: {len(custom_token)})")

        # Step 2: Exchange custom token for ID token using Firebase Auth REST API
        if not FIREBASE_API_KEY:
            print("[ERROR] FIREBASE_API_KEY not set in environment")
            return None

        firebase_auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithCustomToken?key={FIREBASE_API_KEY}"

        print(f"[DEBUG] Exchanging custom token for ID token with Firebase")
        firebase_response = requests.post(
            firebase_auth_url,
            json={
                'token': custom_token,
                'returnSecureToken': True
            },
            timeout=5
        )

        if not firebase_response.ok:
            print(f"[DEBUG] Firebase auth returned {firebase_response.status_code}: {firebase_response.text[:200]}")
            return None

        firebase_data = firebase_response.json()
        id_token = firebase_data.get('idToken')

        if id_token:
            print(f"[DEBUG] Got Firebase ID token (length: {len(id_token)})")
            return id_token
        else:
            print("[DEBUG] No idToken in Firebase response")
            return None

    except Exception as e:
        print(f"[DEBUG] Failed to get Firebase ID token: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_bearer_token() -> Optional[str]:
    """Extract Firebase ID token for Bearer auth

    Priority:
    1. From Flask session (cached token)
    2. Get fresh token from auth server via session cookie
    """
    from flask import session as flask_session

    # Try session first (cached token)
    if 'firebase_id_token' in flask_session:
        token = flask_session['firebase_id_token']
        print(f"[DEBUG] Bearer token from session cache (length: {len(token)})")
        return token

    # Get fresh token from auth server
    token = get_firebase_id_token_from_session_cookie()
    if token:
        # Cache it in session for future requests
        flask_session['firebase_id_token'] = token
        print(f"[DEBUG] Cached new token in session")
        return token

    print("[DEBUG] No Firebase ID token available")
    return None


def get_user_info(user_ids: List[str], token: Optional[str] = None) -> Dict[str, Dict]:
    """
    Fetch user information from HackPSU API

    Args:
        user_ids: List of user IDs (Firebase UIDs)
        token: Optional Firebase ID token for Bearer authentication

    Returns:
        Dictionary mapping user_id -> user_info
    """
    if not user_ids:
        return {}

    # Use provided token or get from request
    if not token:
        token = get_bearer_token()

    print(f"[DEBUG] Token being used for get_user_info: {'Present' if token else 'None'}")

    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
        print(f"[DEBUG] Authorization header set with Bearer token")

    user_info_map = {}

    for user_id in user_ids:
        if not user_id or user_id == 'None':
            continue

        try:
            # Try organizer endpoint first (for admins)
            organizer_url = f"{HACKPSU_API_URL}/organizers/{user_id}"
            print(f"[DEBUG] Fetching organizer info from {organizer_url}")
            if headers.get('Authorization'):
                auth_header = headers['Authorization']
                print(f"[DEBUG] Authorization header: {auth_header[:20]}... (length: {len(auth_header)})")
            else:
                print(f"[DEBUG] No Authorization header!")
            response = requests.get(organizer_url, headers=headers, timeout=5)
            print(f"[DEBUG] Response status: {response.status_code}")

            if response.ok:
                organizer_data = response.json()
                user_info_map[user_id] = {
                    'name': f"{organizer_data.get('firstName', '')} {organizer_data.get('lastName', '')}".strip(),
                    'email': organizer_data.get('email', ''),
                    'firstName': organizer_data.get('firstName', ''),
                    'lastName': organizer_data.get('lastName', ''),
                    'privilege': organizer_data.get('privilege', 0),
                    'team': organizer_data.get('team', ''),
                    'isOrganizer': True
                }
                print(f"[DEBUG] Successfully fetched organizer info for {user_id}: {user_info_map[user_id]}")
                continue
            else:
                print(f"[DEBUG] Organizer endpoint returned {response.status_code} for {user_id}: {response.text[:200]}")
        except Exception as e:
            print(f"[DEBUG] Exception fetching organizer info for {user_id}: {e}")

        # If not an organizer or organizer fetch failed, try regular user endpoint
        try:
            # For regular users, we can't fetch by ID directly
            # We'll use the info from session if available
            # This is a limitation of the HackPSU API
            user_info_map[user_id] = {
                'name': 'User',
                'email': '',
                'firstName': 'User',
                'lastName': '',
                'privilege': 0,
                'isOrganizer': False
            }
            print(f"[DEBUG] Using default info for regular user {user_id}")
        except Exception as e:
            print(f"[DEBUG] Failed to fetch user info for {user_id}: {e}")
            user_info_map[user_id] = {
                'name': 'Unknown User',
                'email': '',
                'firstName': 'Unknown',
                'lastName': 'User',
                'privilege': 0,
                'isOrganizer': False
            }

    return user_info_map


def get_my_info(token: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch current user's information from HackPSU API

    Args:
        token: Optional Firebase ID token for Bearer authentication

    Returns:
        User information dict or None
    """
    # Use provided token or get from request
    if not token:
        token = get_bearer_token()

    print(f"[DEBUG] Token being used for get_my_info: {'Present' if token else 'None'}")

    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'
        print(f"[DEBUG] Authorization header set for /users/info/me")

    try:
        user_url = f"{HACKPSU_API_URL}/users/info/me"
        print(f"[DEBUG] Fetching user info from {user_url}")
        response = requests.get(user_url, headers=headers, timeout=5)
        print(f"[DEBUG] Response status for /users/info/me: {response.status_code}")

        if response.ok:
            user_data = response.json()
            print(f"[DEBUG] Successfully fetched /users/info/me: {user_data}")
            return {
                'name': f"{user_data.get('firstName', '')} {user_data.get('lastName', '')}".strip(),
                'email': user_data.get('email', ''),
                'firstName': user_data.get('firstName', ''),
                'lastName': user_data.get('lastName', ''),
                'phone': user_data.get('phone', ''),
                'university': user_data.get('university', ''),
                'major': user_data.get('major', ''),
                'privilege': 0,  # Regular users have privilege 0
                'isOrganizer': False
            }
        else:
            print(f"[DEBUG] /users/info/me returned {response.status_code}: {response.text[:200]}")
    except Exception as e:
        print(f"[DEBUG] Exception fetching /users/info/me: {e}")

    return None
