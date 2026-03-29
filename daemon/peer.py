#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#

"""
daemon.peer
~~~~~~~~~~~~~~~~~

This module implements the peer-to-peer communication node for the hybrid
chat application. Each peer can:
- Connect directly to other peers via TCP sockets
- Send and receive messages without routing through the central server
- Broadcast messages to all connected peers

The P2P communication uses non-blocking (multi-threaded) socket connections.
"""

import socket
import threading
import json
import time

# Connected peers
# Format: {peer_id: {"ip": str, "port": int, "socket": socket, "username": str}}
_connected_peers = {}
_peers_lock = threading.Lock()

# Message callback function (set by the app)
_message_callback = None

# Local peer info
_local_info = {
    "peer_id": None,
    "ip": None,
    "port": None,
    "username": None,
}

# Message queue for incoming P2P messages
_message_queue = []
_queue_lock = threading.Lock()


def set_local_info(peer_id, ip, port, username):
    """Set the local peer's information.

    :param peer_id (str): Local peer ID.
    :param ip (str): Local IP address.
    :param port (int): Local listening port for P2P.
    :param username (str): Local username.
    """
    _local_info["peer_id"] = peer_id
    _local_info["ip"] = ip
    _local_info["port"] = port
    _local_info["username"] = username


def set_message_callback(callback):
    """Set a callback function for incoming messages.

    :param callback (function): Function to call with (sender, message, channel).
    """
    global _message_callback
    _message_callback = callback


def start_p2p_listener(ip, port):
    """Start a TCP server to listen for incoming P2P connections.

    Runs in a separate daemon thread to accept connections from other peers.

    :param ip (str): IP address to bind.
    :param port (int): Port to listen on.
    """
    def listener_thread():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((ip, port))
            server.listen(10)
            print("[Peer] P2P listener started on {}:{}".format(ip, port))

            while True:
                conn, addr = server.accept()
                print("[Peer] Incoming P2P connection from {}".format(addr))

                # Handle each P2P connection in a separate thread
                handler = threading.Thread(
                    target=handle_p2p_connection,
                    args=(conn, addr)
                )
                handler.daemon = True
                handler.start()
        except socket.error as e:
            print("[Peer] Listener error: {}".format(e))

    t = threading.Thread(target=listener_thread)
    t.daemon = True
    t.start()
    return t


def handle_p2p_connection(conn, addr):
    """Handle an incoming P2P connection.

    Continuously reads messages from the connected peer.

    :param conn (socket.socket): Connection socket.
    :param addr (tuple): Remote address.
    """
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            try:
                msg = json.loads(data.decode('utf-8'))
                print("[Peer] Received P2P message from {}: {}".format(
                    addr, msg.get("message", "")[:50]
                ))

                # Store in message queue
                with _queue_lock:
                    _message_queue.append(msg)

                # Call callback if set
                if _message_callback:
                    _message_callback(
                        msg.get("sender", "unknown"),
                        msg.get("message", ""),
                        msg.get("channel", "general"),
                    )

                # Send acknowledgment
                ack = json.dumps({"status": "received", "timestamp": time.time()})
                conn.sendall(ack.encode('utf-8'))

            except json.JSONDecodeError:
                print("[Peer] Invalid message format from {}".format(addr))
    except socket.error as e:
        print("[Peer] P2P connection error: {}".format(e))
    finally:
        conn.close()


def connect_to_peer(peer_id, ip, port, username="unknown"):
    """Establish a direct TCP connection to another peer.

    :param peer_id (str): Remote peer's ID.
    :param ip (str): Remote peer's IP address.
    :param port (int): Remote peer's P2P listening port.
    :param username (str): Remote peer's username.

    :rtype: bool - True if connection established.
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, int(port)))
        sock.settimeout(None)

        with _peers_lock:
            _connected_peers[peer_id] = {
                "ip": ip,
                "port": port,
                "socket": sock,
                "username": username,
            }

        print("[Peer] Connected to peer {} ({}:{})".format(peer_id, ip, port))

        # Start a listener thread for this connection
        listener = threading.Thread(
            target=_listen_peer_messages,
            args=(peer_id, sock)
        )
        listener.daemon = True
        listener.start()

        return True
    except socket.error as e:
        print("[Peer] Failed to connect to {}:{} - {}".format(ip, port, e))
        return False


def _listen_peer_messages(peer_id, sock):
    """Listen for messages from a connected peer.

    :param peer_id (str): Remote peer ID.
    :param sock (socket.socket): Connection socket.
    """
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                break

            try:
                msg = json.loads(data.decode('utf-8'))
                # Store in message queue
                with _queue_lock:
                    _message_queue.append(msg)

                if _message_callback:
                    _message_callback(
                        msg.get("sender", "unknown"),
                        msg.get("message", ""),
                        msg.get("channel", "general"),
                    )
            except json.JSONDecodeError:
                pass
    except socket.error:
        pass
    finally:
        # Remove disconnected peer
        with _peers_lock:
            if peer_id in _connected_peers:
                del _connected_peers[peer_id]
        print("[Peer] Disconnected from peer {}".format(peer_id))


def send_message(peer_id, message, channel="general"):
    """Send a message to a specific connected peer.

    :param peer_id (str): Target peer ID.
    :param message (str): Message content.
    :param channel (str): Channel name.

    :rtype: bool - True if message sent successfully.
    """
    with _peers_lock:
        peer = _connected_peers.get(peer_id)
        if not peer:
            print("[Peer] Peer {} not connected".format(peer_id))
            return False

    try:
        msg = json.dumps({
            "type": "message",
            "sender": _local_info.get("username", "unknown"),
            "sender_id": _local_info.get("peer_id", ""),
            "message": message,
            "channel": channel,
            "timestamp": time.time(),
        })
        peer["socket"].sendall(msg.encode('utf-8'))
        print("[Peer] Message sent to peer {}".format(peer_id))
        return True
    except socket.error as e:
        print("[Peer] Error sending to {}: {}".format(peer_id, e))
        # Remove disconnected peer
        with _peers_lock:
            if peer_id in _connected_peers:
                del _connected_peers[peer_id]
        return False


def broadcast_message(message, channel="general"):
    """Broadcast a message to all connected peers.

    :param message (str): Message content.
    :param channel (str): Channel name.

    :rtype: int - Number of peers message was sent to.
    """
    sent_count = 0
    with _peers_lock:
        peer_ids = list(_connected_peers.keys())

    for peer_id in peer_ids:
        if send_message(peer_id, message, channel):
            sent_count += 1

    print("[Peer] Broadcast sent to {} peers".format(sent_count))
    return sent_count


def get_connected_peers():
    """Get list of currently connected peers.

    :rtype: list of peer info dicts (without socket objects).
    """
    with _peers_lock:
        result = []
        for pid, data in _connected_peers.items():
            result.append({
                "peer_id": pid,
                "ip": data["ip"],
                "port": data["port"],
                "username": data.get("username", "unknown"),
            })
        return result


def get_messages(since=0):
    """Get messages from the queue.

    :param since (float): Only return messages after this timestamp.

    :rtype: list of message dicts.
    """
    with _queue_lock:
        if since > 0:
            return [m for m in _message_queue if m.get("timestamp", 0) > since]
        return list(_message_queue)


def disconnect_peer(peer_id):
    """Disconnect from a peer.

    :param peer_id (str): Peer ID to disconnect.

    :rtype: bool - True if disconnected.
    """
    with _peers_lock:
        peer = _connected_peers.get(peer_id)
        if peer:
            try:
                peer["socket"].close()
            except Exception:
                pass
            del _connected_peers[peer_id]
            return True
    return False


def disconnect_all():
    """Disconnect from all peers."""
    with _peers_lock:
        for pid, data in _connected_peers.items():
            try:
                data["socket"].close()
            except Exception:
                pass
        _connected_peers.clear()
    print("[Peer] Disconnected from all peers")
