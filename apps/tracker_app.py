#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#

"""
apps.tracker_app
~~~~~~~~~~~~~~~~~

Standalone Tracker server — the Client-Server component.
Provides REST APIs for peer registration, discovery, and channel management.
"""

import json
import uuid
import time

from daemon import AsynapRous
from daemon.auth import (
    authenticate_and_create_session, register_user
)
from daemon.tracker import (
    register_peer, unregister_peer, get_peer_list, get_peer_info,
    update_heartbeat, create_channel, join_channel,
    add_message, get_channel_messages, get_channel_list
)

app = AsynapRous()


@app.route('/login', methods=['POST'])
def login(headers="", body=""):
    print("[Tracker] POST /login")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {}
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return json.dumps({"error": "Missing username or password"}).encode()
    success, session_id = authenticate_and_create_session(username, password)
    if success:
        return json.dumps({"message": "Login successful", "username": username, "session_id": session_id}).encode()
    return json.dumps({"error": "Invalid credentials"}).encode()


@app.route('/register', methods=['POST'])
def register(headers="", body=""):
    print("[Tracker] POST /register")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()
    u, p = data.get("username", ""), data.get("password", "")
    if not u or not p:
        return json.dumps({"error": "Missing fields"}).encode()
    if register_user(u, p):
        return json.dumps({"message": "Registered"}).encode()
    return json.dumps({"error": "Username exists"}).encode()


@app.route('/submit-info', methods=['POST'])
def submit_info(headers="", body=""):
    """Peer registers its IP + P2P port with the tracker."""
    print("[Tracker] POST /submit-info")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()
    peer_id = data.get("peer_id", str(uuid.uuid4())[:8])
    ip = data.get("ip", "127.0.0.1")
    port = data.get("port", 0)
    username = data.get("username", "anonymous")
    register_peer(peer_id, ip, port, username)
    return json.dumps({"message": "Registered", "peer_id": peer_id}).encode()


@app.route('/get-list', methods=['GET'])
def get_list(headers="", body=""):
    """Return list of all online peers."""
    print("[Tracker] GET /get-list")
    peers = get_peer_list()
    peer_list = [{"peer_id": pid, "ip": info["ip"], "port": info["port"],
                  "username": info["username"], "status": info["status"]}
                 for pid, info in peers.items()]
    return json.dumps({"peers": peer_list}).encode()


@app.route('/heartbeat', methods=['POST'])
def heartbeat(headers="", body=""):
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {}
    peer_id = data.get("peer_id", "")
    if peer_id:
        update_heartbeat(peer_id)
    return json.dumps({"status": "alive"}).encode()


@app.route('/logout', methods=['POST'])
def logout(headers="", body=""):
    print("[Tracker] POST /logout")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {}
    peer_id = data.get("peer_id", "")
    if peer_id:
        unregister_peer(peer_id)
    return json.dumps({"message": "Logged out"}).encode()


# Channel management
@app.route('/get-channels', methods=['GET'])
def get_channels(headers="", body=""):
    return json.dumps({"channels": get_channel_list()}).encode()


@app.route('/create-channel', methods=['POST'])
def create_channel_route(headers="", body=""):
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()
    name = data.get("channel", "")
    by = data.get("username", "anonymous")
    if not name:
        return json.dumps({"error": "Missing channel name"}).encode()
    if create_channel(name, by):
        return json.dumps({"message": "Created"}).encode()
    return json.dumps({"error": "Already exists"}).encode()


@app.route('/send-channel', methods=['POST'])
def send_channel(headers="", body=""):
    """Store a channel message (Client-Server paradigm)."""
    print("[Tracker] POST /send-channel (Client-Server message)")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()
    channel = data.get("channel", "general")
    sender = data.get("username", "anonymous")
    message = data.get("message", "")
    if not message:
        return json.dumps({"error": "Empty message"}).encode()
    add_message(channel, sender, message, msg_type="channel")
    print("[Server] Channel msg from '{}' in #{}: {}".format(sender, channel, message[:50]))
    return json.dumps({"message": "Stored"}).encode()


@app.route('/get-messages', methods=['POST'])
def get_messages(headers="", body=""):
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {}
    channel = data.get("channel", "general")
    since = data.get("since", 0)
    messages = get_channel_messages(channel, since)
    return json.dumps({"messages": messages}).encode()


def create_tracker(ip, port):
    app.prepare_address(ip, port)
    app.run()
