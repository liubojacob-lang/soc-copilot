#!/usr/bin/env python3
"""
WebSocket Connection Test

Test WebSocket connection, authentication, and basic functionality.
"""

import asyncio
import websockets
import json
from datetime import datetime

# Configuration
WS_URL = "ws://localhost:8000/ws/alerts"
API_URL = "http://localhost:8000"

# Test credentials
TEST_USER = "admin"
TEST_PASSWORD = "admin123"


async def get_token():
    """Get authentication token."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_URL}/api/auth/login",
            json={"username": TEST_USER, "password": TEST_PASSWORD}
        )
        data = response.json()
        return data.get("access_token")


async def test_connection():
    """Test 1: WebSocket connection."""
    print("\n" + "="*60)
    print("Test 1: WebSocket Connection")
    print("="*60)

    token = await get_token()
    if not token:
        print("❌ Failed to get token")
        return False

    try:
        # Construct WebSocket URL with token
        ws_url = f"{WS_URL}?token={token}"

        async with websockets.connect(ws_url) as websocket:
            print(f"✅ Connected to {WS_URL}")

            # Wait for welcome message
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            print(f"✅ Received message: {data.get('type')}")

            return True

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def test_ping_pong():
    """Test 2: Ping/Pong heartbeat."""
    print("\n" + "="*60)
    print("Test 2: Ping/Pong Heartbeat")
    print("="*60)

    token = await get_token()
    if not token:
        print("❌ Failed to get token")
        return False

    try:
        ws_url = f"{WS_URL}?token={token}"

        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected")

            # Send ping
            ping_msg = {
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send(json.dumps(ping_msg))
            print("✅ Sent ping")

            # Wait for pong
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)

            if data.get("type") == "pong":
                print("✅ Received pong")
                return True
            else:
                print(f"⚠️  Received: {data.get('type')}")
                return False

    except Exception as e:
        print(f"❌ Ping/Pong test failed: {e}")
        return False


async def test_alert_reception():
    """Test 3: Alert reception via WebSocket."""
    print("\n" + "="*60)
    print("Test 3: Alert Reception")
    print("="*60)

    token = await get_token()
    if not token:
        print("❌ Failed to get token")
        return False

    try:
        ws_url = f"{WS_URL}?token={token}"

        async with websockets.connect(ws_url) as websocket:
            print("✅ Connected, waiting for alerts...")

            # Send a test alert via HTTP API
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{API_URL}/api/v1/wazuh/stream/test-alert",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "agent_id": "001",
                        "severity": "high",
                        "event_type": "websocket_test",
                        "count": 1
                    }
                )

            print("✅ Sent test alert via HTTP API")

            # Wait for WebSocket message
            message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            data = json.loads(message)

            print("✅ Received WebSocket message:")
            print(f"   Type: {data.get('type')}")
            print(f"   Channel: {data.get('channel')}")
            if data.get('type') == 'alert':
                alert_data = data.get('data', {})
                print(f"   Alert ID: {alert_data.get('id')}")
                print(f"   Severity: {alert_data.get('severity')}")
                print(f"   Event Type: {alert_data.get('event_type')}")
                return True

            return False

    except Exception as e:
        print(f"❌ Alert reception test failed: {e}")
        return False


async def test_multiple_clients():
    """Test 4: Multiple WebSocket clients."""
    print("\n" + "="*60)
    print("Test 4: Multiple Clients")
    print("="*60)

    token = await get_token()
    if not token:
        print("❌ Failed to get token")
        return False

    client_count = 3
    clients_connected = 0
    clients_received = 0

    async def connect_client(client_id: int):
        nonlocal clients_connected, clients_received
        try:
            ws_url = f"{WS_URL}?token={token}"
            async with websockets.connect(ws_url) as websocket:
                clients_connected += 1
                print(f"✅ Client {client_id} connected")

                # Wait for alert
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    data = json.loads(message)
                    if data.get('type') == 'alert':
                        clients_received += 1
                        print(f"✅ Client {client_id} received alert")
                except asyncio.TimeoutError:
                    pass

        except Exception as e:
            print(f"❌ Client {client_id} failed: {e}")

    # Connect multiple clients
    tasks = [connect_client(i) for i in range(1, client_count + 1)]

    # Send test alert
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{API_URL}/api/v1/wazuh/stream/test-alert",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "agent_id": "001",
                "severity": "high",
                "event_type": "multi_client_test",
                "count": 1
            }
        )

    await asyncio.gather(*tasks)

    print("\n📊 Results:")
    print(f"   Clients connected: {clients_connected}/{client_count}")
    print(f"   Clients received alert: {clients_received}/{client_count}")

    return clients_connected == client_count and clients_received == client_count


async def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 WebSocket Backend Test Suite")
    print("="*60)
    print(f"WebSocket URL: {WS_URL}")
    print(f"API URL: {API_URL}")

    results = []

    # Test 1: Connection
    results.append(await test_connection())

    # Test 2: Ping/Pong
    results.append(await test_ping_pong())

    # Test 3: Alert Reception
    results.append(await test_alert_reception())

    # Test 4: Multiple Clients
    results.append(await test_multiple_clients())

    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"Test 1 (Connection): {'✅ PASS' if results[0] else '❌ FAIL'}")
    print(f"Test 2 (Ping/Pong): {'✅ PASS' if results[1] else '❌ FAIL'}")
    print(f"Test 3 (Alert Reception): {'✅ PASS' if results[2] else '❌ FAIL'}")
    print(f"Test 4 (Multiple Clients): {'✅ PASS' if results[3] else '❌ FAIL'}")

    passed = sum(results)
    total = len(results)
    print(f"\n📈 Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
