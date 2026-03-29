#!/usr/bin/env python3
#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#

"""
start_chatapp
~~~~~~~~~~~~~~~~~

Starts a Peer node for the hybrid chat application.
Each peer has:
  - An HTTP server (serves the chat web UI)
  - A TCP P2P listener (for direct peer-to-peer messaging)
  - Connection to the central Tracker for registration/discovery

Usage:
    # Terminal 1: Start tracker first
    python3 start_tracker.py --port 8000

    # Terminal 2: Start peer A
    python3 start_chatapp.py --port 8001 --p2p-port 5001 --tracker http://localhost:8000

    # Terminal 3: Start peer B
    python3 start_chatapp.py --port 8002 --p2p-port 5002 --tracker http://localhost:8000
"""

import argparse
from apps.chatapp import create_chatapp

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='ChatApp Peer',
        description='Start a peer node for the hybrid P2P chat',
    )
    parser.add_argument('--ip', default='0.0.0.0',
                        help='IP to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8001,
                        help='HTTP port for web UI (default: 8001)')
    parser.add_argument('--p2p-port', type=int, default=5001,
                        help='TCP port for P2P listener (default: 5001)')
    parser.add_argument('--tracker', default='http://localhost:8000',
                        help='Tracker URL (default: http://localhost:8000)')

    args = parser.parse_args()

    print("=" * 60)
    print("  AsynapRous Peer Node")
    print("  HTTP (Web UI):  http://{}:{}".format(args.ip, args.port))
    print("  P2P Listener:   port {}".format(args.p2p_port))
    print("  Tracker:        {}".format(args.tracker))
    print("  Chat UI:        http://{}:{}/chat.html".format(
        "127.0.0.1" if args.ip == "0.0.0.0" else args.ip, args.port
    ))
    print("=" * 60)

    create_chatapp(args.ip, args.port, args.p2p_port, args.tracker)
