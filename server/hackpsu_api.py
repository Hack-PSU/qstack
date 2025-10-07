# HackPSU API Client
# Replaces Plume for fetching user information

import requests
import os
from typing import Dict, List, Optional
from flask import request

HACKPSU_API_URL = os.environ.get('HACKPSU_API_URL', 'https://apiv3.hackpsu.org')


def get_bearer_token() -> Optional[str]:
    """Extract Firebase ID token from __session cookie for Bearer auth"""
    session_token = request.cookies.get('__session')
    if session_token:
        return session_token
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

    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    user_info_map = {}

    for user_id in user_ids:
        if not user_id or user_id == 'None':
            continue

        try:
            # Try organizer endpoint first (for admins)
            organizer_url = f"{HACKPSU_API_URL}/organizers/{user_id}"
            response = requests.get(organizer_url, headers=headers, timeout=5)

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
                print(f"[DEBUG] Fetched organizer info for {user_id}")
                continue
        except Exception as e:
            print(f"[DEBUG] Failed to fetch organizer info for {user_id}: {e}")

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

    headers = {}
    if token:
        headers['Authorization'] = f'Bearer {token}'

    try:
        user_url = f"{HACKPSU_API_URL}/users/info/me"
        response = requests.get(user_url, headers=headers, timeout=5)

        if response.ok:
            user_data = response.json()
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
    except Exception as e:
        print(f"[DEBUG] Failed to fetch user info: {e}")

    return None
