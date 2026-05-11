"""
Manual smoke test for client-server communication.

This script tests communication by sending sample messages to a running server.
"""

import sys
import time

import requests


def test_server_health():
    """Test if the server is running and responding."""
    try:
        response = requests.get("http://localhost:8080/health", timeout=2)
        if response.status_code == 200:
            print("Server is running and healthy")
            return True
        print(f"Server returned unexpected status: {response.status_code}")
        return False
    except requests.exceptions.RequestException as error:
        print(f"Cannot connect to server: {error}")
        return False


def test_message_processing():
    """Test processing messages through the server."""
    test_messages = [
        {"is_team": False, "playername": "TestPlayer", "chattext": "@help"},
        {"is_team": True, "playername": "TestPlayer", "chattext": "Hello world"},
    ]

    for index, message in enumerate(test_messages, 1):
        print(f"\nTest {index}: Sending message: {message['chattext']}")
        try:
            response = requests.post(
                "http://localhost:8080/process_message",
                json=message,
                timeout=5,
            )
            if response.status_code == 200:
                payload = response.json()
                responses = payload.get("responses", [])
                print("Message processed successfully")
                print(f"Received {len(responses)} response(s):")
                for item in responses:
                    scope = "[TEAM]" if item["is_team"] else "[ALL]"
                    print(f"  - {scope} {item['text']}")
            else:
                print(f"Server returned error: {response.status_code}")
                print(f"Response: {response.text}")
        except requests.exceptions.RequestException as error:
            print(f"Request failed: {error}")


def start_test_server():
    """Start the server for testing."""
    from server import run_server

    print("Starting test server...")
    run_server(host="127.0.0.1", port=8080)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "test"

    if mode == "start-server":
        start_test_server()
    else:
        print("=" * 60)
        print("CS2 Chat Bot - Client/Server Communication Smoke Test")
        print("=" * 60)
        print("\nNote: make sure the server is running before running this script.")
        print("Run 'python test_communication.py start-server' in another terminal.\n")

        time.sleep(1)

        print("\n1. Testing server health endpoint...")
        if not test_server_health():
            print("\nServer is not running. Start it with:")
            print("python launcher.py server")
            sys.exit(1)

        print("\n2. Testing message processing...")
        test_message_processing()

        print("\n" + "=" * 60)
        print("Smoke tests completed")
        print("=" * 60)
