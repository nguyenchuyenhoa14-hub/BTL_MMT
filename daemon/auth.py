#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#

"""
daemon.auth
~~~~~~~~~~~~~~~~~

This module implements HTTP authentication mechanisms following:
- RFC 2617 - HTTP Authentication: Basic and Digest Access Authentication
- RFC 7235 - Hypertext Transfer Protocol (HTTP/1.1): Authentication
- RFC 6265 - HTTP State Management Mechanism (Cookies)

It provides:
- Basic HTTP Authentication (Authorization header)
- Session-based authentication via cookies (Set-Cookie / Cookie headers)
- User credential management from JSON database
"""

import json
import os
import base64
import hashlib
import time
import uuid

# Path to user database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "users.json")

# In-memory session store
# Format: {session_id: {"username": str, "role": str, "created_at": float, "expires_at": float}}
_sessions = {}

# Session timeout in seconds (30 minutes)
SESSION_TIMEOUT = 1800


def load_users():
    """Load user credentials from the JSON database file.

    :rtype: dict of user records.
    """
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print("[Auth] Error loading user database: {}".format(e))
        return {}


def save_users(users):
    """Save user credentials to the JSON database file.

    :param users (dict): User records to save.
    """
    try:
        with open(DB_PATH, 'w') as f:
            json.dump(users, f, indent=4)
    except Exception as e:
        print("[Auth] Error saving user database: {}".format(e))


def verify_credentials(username, password):
    """Verify username and password against the database.

    :param username (str): Username to verify.
    :param password (str): Password to verify.

    :rtype: dict or None - User record if valid, None otherwise.
    """
    users = load_users()
    user = users.get(username)
    if user and user.get("password") == password:
        return user
    return None


def register_user(username, password, role="user"):
    """Register a new user in the database.

    :param username (str): New username.
    :param password (str): New password.
    :param role (str): User role (default: "user").

    :rtype: bool - True if registration successful.
    """
    users = load_users()
    if username in users:
        return False
    users[username] = {"password": password, "role": role}
    save_users(users)
    return True


def create_session(username, role="user"):
    """Create a new session for an authenticated user.

    Implements session token generation per RFC 6265.

    :param username (str): Authenticated username.
    :param role (str): User role.

    :rtype: str - Session ID token.
    """
    session_id = str(uuid.uuid4())
    now = time.time()
    _sessions[session_id] = {
        "username": username,
        "role": role,
        "created_at": now,
        "expires_at": now + SESSION_TIMEOUT,
    }
    print("[Auth] Session created for user '{}': {}".format(username, session_id))
    return session_id


def validate_session(session_id):
    """Validate a session token.

    Checks if the session exists and has not expired.

    :param session_id (str): Session token to validate.

    :rtype: dict or None - Session data if valid, None otherwise.
    """
    session = _sessions.get(session_id)
    if not session:
        return None

    # Check expiration
    if time.time() > session["expires_at"]:
        # Session expired, remove it
        del _sessions[session_id]
        print("[Auth] Session expired: {}".format(session_id))
        return None

    return session


def destroy_session(session_id):
    """Destroy/invalidate a session.

    :param session_id (str): Session token to destroy.

    :rtype: bool - True if session was found and destroyed.
    """
    if session_id in _sessions:
        del _sessions[session_id]
        print("[Auth] Session destroyed: {}".format(session_id))
        return True
    return False


def parse_basic_auth(auth_header):
    """Parse HTTP Basic Authentication header.

    Per RFC 2617: Authorization: Basic base64(username:password)

    :param auth_header (str): Authorization header value.

    :rtype: tuple (username, password) or None.
    """
    try:
        if not auth_header:
            return None
        if auth_header.lower().startswith('basic '):
            encoded = auth_header.split(' ', 1)[1].strip()
            decoded = base64.b64decode(encoded).decode('utf-8')
            username, password = decoded.split(':', 1)
            return (username, password)
    except Exception as e:
        print("[Auth] Error parsing Basic auth: {}".format(e))
    return None


def check_auth(request):
    """Check if a request is authenticated.

    Checks in order:
    1. Session cookie (RFC 6265)
    2. Authorization header (RFC 2617 / RFC 7235)

    :param request: Request object with headers and cookies.

    :rtype: tuple (bool, str, str) - (is_authenticated, username, role)
    """
    # 1. Check session cookie
    if hasattr(request, 'cookies') and request.cookies:
        session_id = request.cookies.get('session_id', '')
        if session_id:
            session = validate_session(session_id)
            if session:
                print("[Auth] Authenticated via cookie: user={}".format(
                    session['username']
                ))
                return True, session['username'], session['role']

    # 2. Check Authorization header (Basic Auth - RFC 2617)
    if hasattr(request, 'headers') and request.headers:
        auth_header = request.headers.get('authorization', '')
        if auth_header:
            credentials = parse_basic_auth(auth_header)
            if credentials:
                username, password = credentials
                user = verify_credentials(username, password)
                if user:
                    print("[Auth] Authenticated via Basic Auth: user={}".format(
                        username
                    ))
                    return True, username, user.get('role', 'user')

    return False, None, None


def authenticate_and_create_session(username, password):
    """Authenticate user and create a session if credentials are valid.

    :param username (str): Username.
    :param password (str): Password.

    :rtype: tuple (bool, str) - (success, session_id or error message)
    """
    user = verify_credentials(username, password)
    if user:
        session_id = create_session(username, user.get('role', 'user'))
        return True, session_id
    return False, "Invalid credentials"


def get_active_sessions():
    """Get count of active sessions.

    :rtype: int - Number of active sessions.
    """
    # Clean expired sessions
    now = time.time()
    expired = [sid for sid, data in _sessions.items() if now > data["expires_at"]]
    for sid in expired:
        del _sessions[sid]
    return len(_sessions)
