#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#

"""
apps.chatapp
~~~~~~~~~~~~~~~~~

Peer node for the hybrid chat application.

Architecture:
  - Each peer runs its own HTTP server (web UI) + TCP P2P listener
  - Peers register with a central Tracker (Client-Server paradigm)
  - Peers message each other directly via TCP sockets (P2P paradigm)

Client-Server flow (via Tracker):
  login → register with tracker → discover peers → channel messages

P2P flow (direct TCP):
  connect to peer's TCP port → send/receive messages directly
"""

import json
import time
import threading
import urllib.request
import urllib.error

from daemon import AsynapRous
from daemon.auth import authenticate_and_create_session, register_user
from daemon.peer import (
    set_local_info, start_p2p_listener, connect_to_peer,
    send_message as p2p_send_message, broadcast_message as p2p_broadcast,
    get_connected_peers, get_messages as p2p_get_messages, set_message_callback
)

app = AsynapRous()

# Tracker URL (set at startup)
_tracker_url = "http://localhost:8000"

# Local peer info
_local_info = {
    "peer_id": None,
    "username": None,
    "p2p_port": None,
}


def _tracker_request(path, method="GET", data=None):
    """Make an HTTP request to the Tracker server.

    :param path: API path (e.g., '/get-list')
    :param method: HTTP method
    :param data: dict to send as JSON body
    :rtype: dict - parsed JSON response
    """
    url = _tracker_url + path
    try:
        if data:
            body = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=body, method=method)
            req.add_header('Content-Type', 'application/json')
        else:
            req = urllib.request.Request(url, method=method)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print("[Peer] Tracker request failed ({}): {}".format(path, e))
        return {"error": str(e)}


# ============================================================
# Authentication (local check + forward to tracker)
# ============================================================

@app.route('/login', methods=['POST'])
def login(headers="", body=""):
    print("[Peer] POST /login")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()
    username = data.get("username", "")
    password = data.get("password", "")
    if not username or not password:
        return json.dumps({"error": "Missing username or password"}).encode()

    # Forward login to tracker
    result = _tracker_request('/login', 'POST', {"username": username, "password": password})
    if result.get("error"):
        return json.dumps(result).encode()

    _local_info["username"] = username
    _local_info["peer_id"] = result.get("session_id", username)[:8]

    # Register this peer with tracker (IP + P2P port)
    _tracker_request('/submit-info', 'POST', {
        "peer_id": _local_info["peer_id"],
        "ip": "127.0.0.1",  # In real deployment, use actual IP
        "port": _local_info["p2p_port"],
        "username": username,
    })

    result["peer_id"] = _local_info["peer_id"]
    result["p2p_port"] = _local_info["p2p_port"]
    print("[Peer] Logged in as '{}', peer_id={}, P2P port={}".format(
        username, _local_info["peer_id"], _local_info["p2p_port"]))
    return json.dumps(result).encode()


@app.route('/register', methods=['POST'])
def register(headers="", body=""):
    print("[Peer] POST /register")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()
    # Forward to tracker
    result = _tracker_request('/register', 'POST', data)
    return json.dumps(result).encode()


@app.route('/logout', methods=['POST'])
def logout(headers="", body=""):
    print("[Peer] POST /logout")
    if _local_info["peer_id"]:
        _tracker_request('/logout', 'POST', {"peer_id": _local_info["peer_id"]})
    return json.dumps({"message": "Logged out"}).encode()


# ============================================================
# Peer Discovery (proxy to Tracker — Client-Server)
# ============================================================

@app.route('/get-list', methods=['GET'])
def get_list(headers="", body=""):
    """Get online peers from Tracker (Client-Server)."""
    result = _tracker_request('/get-list', 'GET')
    return json.dumps(result).encode()


@app.route('/get-channels', methods=['GET'])
def get_channels(headers="", body=""):
    result = _tracker_request('/get-channels', 'GET')
    return json.dumps(result).encode()


@app.route('/create-channel', methods=['POST'])
def create_channel_route(headers="", body=""):
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()
    result = _tracker_request('/create-channel', 'POST', data)
    return json.dumps(result).encode()


@app.route('/heartbeat', methods=['POST'])
def heartbeat(headers="", body=""):
    if _local_info["peer_id"]:
        _tracker_request('/heartbeat', 'POST', {"peer_id": _local_info["peer_id"]})
    return json.dumps({"status": "alive"}).encode()


# ============================================================
# Channel Messages (Client-Server — through Tracker)
# ============================================================

@app.route('/send-channel', methods=['POST'])
def send_channel(headers="", body=""):
    """Send a message to a channel (Client-Server paradigm).
    This goes THROUGH the tracker — everyone in the channel sees it.
    """
    print("[Peer] POST /send-channel (Client-Server → Tracker)")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()

    # Forward to tracker
    result = _tracker_request('/send-channel', 'POST', data)
    print("[Server] Channel msg forwarded to Tracker")
    return json.dumps(result).encode()


@app.route('/get-messages', methods=['POST'])
def get_messages(headers="", body=""):
    """Get channel messages from Tracker."""
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {}
    result = _tracker_request('/get-messages', 'POST', data)
    return json.dumps(result).encode()


# ============================================================
# P2P Direct Messaging (Real TCP sockets!)
# ============================================================

@app.route('/connect-peer', methods=['POST'])
def connect_peer_route(headers="", body=""):
    """Connect to another peer's TCP P2P listener (Real P2P!).

    This creates an actual TCP socket connection to the target peer.
    """
    print("[Peer] POST /connect-peer")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()

    peer_id = data.get("peer_id", "")
    ip = data.get("ip", "127.0.0.1")
    port = data.get("port", 0)
    username = data.get("username", "unknown")

    if not peer_id or not port:
        return json.dumps({"error": "Missing peer_id or port"}).encode()

    # Establish REAL TCP connection to peer's P2P listener
    success = connect_to_peer(peer_id, ip, int(port), username)

    if success:
        print("[Peer] ✓ TCP P2P connection established to {} ({}:{})".format(username, ip, port))
        return json.dumps({"message": "P2P connected to {}".format(username)}).encode()
    else:
        print("[Peer] ✗ TCP P2P connection failed to {}:{}}".format(ip, port))
        return json.dumps({"error": "TCP connection failed to {}:{}".format(ip, port)}).encode()


@app.route('/send-peer', methods=['POST'])
def send_peer(headers="", body=""):
    """Send a direct message via TCP P2P socket (Real P2P!).

    This message goes DIRECTLY to the target peer via TCP socket,
    NOT through the tracker/server!
    """
    print("[Peer] POST /send-peer (P2P Direct TCP)")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()

    peer_id = data.get("peer_id", "")
    message = data.get("message", "")
    channel = data.get("channel", "p2p")

    if not peer_id or not message:
        return json.dumps({"error": "Missing peer_id or message"}).encode()

    # Send via REAL TCP socket (P2P!)
    success = p2p_send_message(peer_id, message, channel)

    if success:
        print("[Peer] ✓ P2P message sent via TCP to {}: {}".format(peer_id, message[:50]))
        return json.dumps({"message": "DM sent via P2P TCP"}).encode()
    else:
        print("[Peer] ✗ P2P send failed to {}".format(peer_id))
        return json.dumps({"error": "Peer not connected"}).encode()


@app.route('/broadcast-peer', methods=['POST'])
def broadcast_peer(headers="", body=""):
    """Broadcast a message to ALL connected peers via TCP (P2P!).
    """
    print("[Peer] POST /broadcast-peer (P2P Broadcast)")
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        return json.dumps({"error": "Invalid JSON"}).encode()

    message = data.get("message", "")
    channel = data.get("channel", "general")
    if not message:
        return json.dumps({"error": "Empty message"}).encode()

    count = p2p_broadcast(message, channel)
    print("[Peer] ✓ P2P broadcast to {} peers via TCP".format(count))
    return json.dumps({"message": "Broadcast sent", "recipients": count}).encode()


@app.route('/connected-peers', methods=['GET'])
def connected_peers(headers="", body=""):
    """Get list of peers with active TCP P2P connections."""
    peers = get_connected_peers()
    return json.dumps({"connected_peers": peers}).encode()


@app.route('/get-p2p-messages', methods=['POST'])
def get_p2p_messages(headers="", body=""):
    """Get messages received via P2P TCP connections."""
    try:
        data = json.loads(body) if body else {}
    except json.JSONDecodeError:
        data = {}
    since = data.get("since", 0)
    messages = p2p_get_messages(since)
    return json.dumps({"messages": messages}).encode()


# ============================================================
# Startup
# ============================================================

def _on_p2p_message(sender, message, channel):
    """Callback when a P2P message is received via TCP."""
    print("[Peer] ← P2P message received from '{}': {}".format(sender, message[:80]))


def create_chatapp(ip, port, p2p_port, tracker_url):
    """Initialize and start the peer node.

    :param ip: IP to bind
    :param port: HTTP server port (web UI)
    :param p2p_port: TCP P2P listener port
    :param tracker_url: URL of the central tracker
    """
    global _tracker_url
    _tracker_url = tracker_url

    _local_info["p2p_port"] = p2p_port

    # Setup P2P module
    set_local_info("peer", ip if ip != "0.0.0.0" else "127.0.0.1", p2p_port, "peer")
    set_message_callback(_on_p2p_message)

    # Start real TCP P2P listener
    start_p2p_listener(ip if ip != "0.0.0.0" else "0.0.0.0", p2p_port)
    print("[Peer] TCP P2P listener started on port {}".format(p2p_port))

    # Start HTTP server for web UI
    app.prepare_address(ip, port)
    print("[Peer] HTTP server starting on {}:{}".format(ip, port))
    app.run()
