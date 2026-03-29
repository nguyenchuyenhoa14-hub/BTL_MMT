#!/usr/bin/env python3
#
# Copyright (C) 2026 pdnguyen of HCMC University of Technology VNU-HCM.
# All rights reserved.
# This file is part of the CO3093/CO3094 course.
#
# AsynapRous release
#

"""
start_tracker
~~~~~~~~~~~~~~~~~

Starts the centralized Tracker server for peer registration and discovery.
This is the Client-Server component of the hybrid chat architecture.

The Tracker handles:
- Peer registration/unregistration
- Peer discovery (get-list)
- Channel management and message storage
- Heartbeat monitoring

Usage:
    python3 start_tracker.py --port 8000

Other peers connect to this tracker to register and discover each other.
"""

import argparse
from apps.tracker_app import create_tracker

PORT = 8000

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='Tracker',
        description='Start the centralized tracker server',
    )
    parser.add_argument('--ip', default='0.0.0.0',
                        help='IP address to bind (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=PORT,
                        help='Tracker HTTP port (default: {})'.format(PORT))

    args = parser.parse_args()

    print("=" * 60)
    print("  AsynapRous Tracker (Central Server)")
    print("  Listening:  http://{}:{}".format(args.ip, args.port))
    print("  Role:       Peer registration + discovery")
    print("=" * 60)

    create_tracker(args.ip, args.port)
