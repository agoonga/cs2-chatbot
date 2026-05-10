"""
Launcher script for CS2 Chat Bot

This script allows you to run the client and server separately or together.

Usage:
    python launcher.py both          # Run both CS2 client and server (default)
    python launcher.py client        # Run only the CS2 client (connects to existing server)
    python launcher.py server        # Run only the server
    python launcher.py discord       # Run only the Discord bot (connects to existing server)
    python launcher.py all           # Run server with both CS2 and Discord clients
"""

import sys
import threading
import time


def start_server():
    """Start the backend server."""
    from server import run_server
    print("Starting backend server (language per-request, default: English)...")
    run_server(host='127.0.0.1', port=8080)


def start_client():
    """Start the CS2 client."""
    from client.adapters.cs2 import CS2Client
    print("Starting CS2 client...")
    try:
        client = CS2Client(server_url="http://127.0.0.1:8080")
    except RuntimeError as e:
        print(f"CS2 client not started: {e}")
        return
    
    try:
        client.run()
    except KeyboardInterrupt:
        print("Shutting down CS2 client...")
        client.stop()


def start_discord():
    """Start the Discord bot."""
    from client.adapters.discord import DiscordClient
    print("Starting Discord bot...")
    client = DiscordClient(server_url="http://127.0.0.1:8080")
    
    try:
        client.run_bot()
    except KeyboardInterrupt:
        print("Shutting down Discord bot...")


def run_both():
    """Run both server and CS2 client."""
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    print("Waiting for server to start...")
    time.sleep(2)
    
    # Run CS2 client on main thread
    start_client()


def run_all():
    """Run server with both CS2 and Discord clients."""
    # Start server in a separate thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Give the server a moment to start
    print("Waiting for server to start...")
    time.sleep(2)
    
    # Start CS2 client in a separate thread
    cs2_thread = threading.Thread(target=start_client, daemon=True)
    cs2_thread.start()
    
    # Run Discord bot on main thread (it will block)
    start_discord()


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"
    
    if mode == "server":
        start_server()
    elif mode == "client":
        start_client()
    elif mode == "discord":
        # Discord-only mode - connects to existing server (e.g., Docker)
        start_discord()
    elif mode == "both":
        run_both()
    elif mode == "all":
        run_all()
    else:
        print(f"Unknown mode: {mode}")
        print(__doc__)
        sys.exit(1)
