#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#

"""
daemon.tracker
~~~~~~~~~~~~~~~~~

This module implements a centralized tracker server for the P2P chat system.
The tracker maintains a registry of active peers, facilitates peer discovery,
and supports the initialization phase of the hybrid chat application.

The tracker follows the Client-Server paradigm where peers register their
information and query for other active peers.
"""

import json
import time
import threading

# In-memory peer registry
# Format: {peer_id: {"ip": str, "port": int, "username": str, "status": str, "last_seen": float}}
_peers = {}
_peers_lock = threading.Lock()

# Channel registry
# Format: {channel_name: {"members": [peer_id, ...], "messages": [msg_dict, ...], "created_by": str}}
_channels = {
    "general": {
        "members": [],
        "messages": [],
        "created_by": "system",
    }
}
_channels_lock = threading.Lock()

# Heartbeat timeout (seconds) - peer is considered dead if no heartbeat in this time
HEARTBEAT_TIMEOUT = 60


def register_peer(peer_id, ip, port, username):
    """Register a new peer with the tracker.

    :param peer_id (str): Unique peer identifier.
    :param ip (str): Peer's IP address.
    :param port (int): Peer's listening port.
    :param username (str): Peer's username.

    :rtype: bool - True if registration successful.
    """
    with _peers_lock:
        _peers[peer_id] = {
            "ip": ip,
            "port": port,
            "username": username,
            "status": "online",
            "last_seen": time.time(),
        }
    print("[Tracker] Peer registered: {} ({}:{}) user={}".format(
        peer_id, ip, port, username
    ))

    # Automatically join general channel
    join_channel("general", peer_id, username)
    return True


def unregister_peer(peer_id):
    """Remove a peer from the tracker registry.

    :param peer_id (str): Peer identifier to remove.

    :rtype: bool - True if peer was found and removed.
    """
    with _peers_lock:
        if peer_id in _peers:
            del _peers[peer_id]
            print("[Tracker] Peer unregistered: {}".format(peer_id))
            return True
    return False


def update_heartbeat(peer_id):
    """Update the last_seen timestamp for a peer.

    :param peer_id (str): Peer identifier.

    :rtype: bool - True if peer exists and was updated.
    """
    with _peers_lock:
        if peer_id in _peers:
            _peers[peer_id]["last_seen"] = time.time()
            return True
    return False


def get_peer_list():
    """Get the list of all active peers.

    Automatically removes peers that have exceeded the heartbeat timeout.

    :rtype: dict - Dictionary of active peers.
    """
    now = time.time()
    with _peers_lock:
        # Clean expired peers
        expired = [pid for pid, data in _peers.items()
                   if now - data["last_seen"] > HEARTBEAT_TIMEOUT]
        for pid in expired:
            print("[Tracker] Peer timed out: {}".format(pid))
            del _peers[pid]

        # Return copy of active peers
        return dict(_peers)


def get_peer_info(peer_id):
    """Get information about a specific peer.

    :param peer_id (str): Peer identifier.

    :rtype: dict or None.
    """
    with _peers_lock:
        return _peers.get(peer_id)


def create_channel(channel_name, created_by):
    """Create a new chat channel.

    :param channel_name (str): Name of the channel.
    :param created_by (str): Username of the creator.

    :rtype: bool - True if channel created successfully.
    """
    with _channels_lock:
        if channel_name in _channels:
            return False
        _channels[channel_name] = {
            "members": [],
            "messages": [],
            "created_by": created_by,
        }
    print("[Tracker] Channel created: {} by {}".format(channel_name, created_by))
    return True


def join_channel(channel_name, peer_id, username):
    """Add a peer to a channel.

    :param channel_name (str): Channel to join.
    :param peer_id (str): Peer identifier.
    :param username (str): Peer's username.

    :rtype: bool - True if joined successfully.
    """
    with _channels_lock:
        if channel_name not in _channels:
            return False
        member_entry = {"peer_id": peer_id, "username": username}
        # Check if already a member
        existing = [m for m in _channels[channel_name]["members"]
                    if m["peer_id"] == peer_id]
        if not existing:
            _channels[channel_name]["members"].append(member_entry)
    return True


def leave_channel(channel_name, peer_id):
    """Remove a peer from a channel.

    :param channel_name (str): Channel to leave.
    :param peer_id (str): Peer identifier.

    :rtype: bool - True if left successfully.
    """
    with _channels_lock:
        if channel_name not in _channels:
            return False
        _channels[channel_name]["members"] = [
            m for m in _channels[channel_name]["members"]
            if m["peer_id"] != peer_id
        ]
    return True


def add_message(channel_name, sender, message, msg_type="text"):
    """Add a message to a channel.

    Messages are immutable once sent (as per assignment requirements).

    :param channel_name (str): Target channel.
    :param sender (str): Sender username.
    :param message (str): Message content.
    :param msg_type (str): Message type.

    :rtype: bool - True if message added.
    """
    with _channels_lock:
        if channel_name not in _channels:
            return False
        msg = {
            "sender": sender,
            "message": message,
            "type": msg_type,
            "timestamp": time.time(),
        }
        _channels[channel_name]["messages"].append(msg)
    return True


def get_channel_messages(channel_name, since=0):
    """Get messages from a channel.

    :param channel_name (str): Channel name.
    :param since (float): Only return messages after this timestamp.

    :rtype: list of message dicts.
    """
    with _channels_lock:
        if channel_name not in _channels:
            return []
        messages = _channels[channel_name]["messages"]
        if since > 0:
            return [m for m in messages if m["timestamp"] > since]
        return list(messages)


def get_channel_list():
    """Get list of all channels.

    :rtype: list of channel info dicts.
    """
    with _channels_lock:
        result = []
        for name, data in _channels.items():
            result.append({
                "name": name,
                "member_count": len(data["members"]),
                "message_count": len(data["messages"]),
                "created_by": data["created_by"],
            })
        return result


def get_channel_members(channel_name):
    """Get members of a channel.

    :param channel_name (str): Channel name.

    :rtype: list of member dicts.
    """
    with _channels_lock:
        if channel_name not in _channels:
            return []
        return list(_channels[channel_name]["members"])
