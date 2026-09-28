"""End-to-end verification script for alert-worker against Redis Streams and local webhook.

Usage:
    cd backend
    python scripts/verify_alert_worker.py
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import UTC, datetime

from aiohttp import web

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.message_queue_manager import get_message_queue_manager
from workers.alert_worker import AlertWorker

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("verify_alert_worker")

received_webhooks = []


async def webhook_handler(request):
    data = await request.json()
    received_webhooks.append(data)
    logger.info(
        "🎯 Mock Webhook received notification: %s",
        json.dumps(data, ensure_ascii=False),
    )
    return web.json_response({"status": "ok"})


async def run_mock_webhook_server():
    app = web.Application()
    app.router.add_post("/webhook", webhook_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 19999)
    await site.start()
    return runner


async def main():
    redis_url = os.getenv(
        "REDIS_URL", "redis://:soc_sim_redis_123456@127.0.0.1:16379/0"
    )
    os.environ["REDIS_URL"] = redis_url
    os.environ["FEISHU_WEBHOOK_URL"] = "http://127.0.0.1:19999/webhook"

    logger.info(
        "1. Starting mock webhook receiver on http://127.0.0.1:19999/webhook..."
    )
    webhook_runner = await run_mock_webhook_server()

    try:
        logger.info("2. Initializing MessageQueueManager with %s...", redis_url)
        mq = get_message_queue_manager(redis_url)

        alert_id = f"test-alert-{uuid.uuid4().hex[:8]}"
        test_alert = {
            "id": alert_id,
            "title": "E2E Test SSH Brute Force Detected",
            "source": "suricata",
            "severity": "critical",
            "event_type": "authentication_failure",
            "created_at": datetime.now(UTC).isoformat(),
            "description": "Multiple failed SSH login attempts from 192.168.1.100",
        }

        logger.info(
            "3. Publishing test alert %s to Redis Streams (severity: critical)...",
            alert_id,
        )
        msg_id = await mq.publish_alert_async(test_alert, severity="critical")
        assert msg_id is not None, "Failed to publish message to Redis Streams"
        logger.info("✅ Alert published with message_id: %s", msg_id)

        logger.info("4. Initializing AlertWorker(worker_id='e2e-verifier')...")
        worker = AlertWorker(worker_id="e2e-verifier")

        logger.info("5. Consuming 1 message with AlertWorker...")
        messages = await worker.mq_manager.consume_alerts_async(
            worker_id=worker.worker_id,
            count=1,
            block=5000,
            priority_order=True,
        )
        assert len(messages) == 1, f"Expected 1 message, got {len(messages)}"
        consumed_msg = messages[0]
        logger.info(
            "✅ AlertWorker consumed message: %s from stream: %s",
            consumed_msg["message_id"],
            consumed_msg["stream"],
        )

        logger.info("6. Processing message through notification pipeline...")
        await worker._process_message(consumed_msg)

        # Assertions
        assert (
            len(received_webhooks) == 1
        ), f"Expected 1 webhook call, got {len(received_webhooks)}"
        payload = received_webhooks[0]
        assert (
            "E2E Test SSH Brute Force Detected" in payload["content"]["text"]
        ), "Payload missing alert title"
        assert alert_id in payload["content"]["text"], "Payload missing alert ID"
        logger.info(
            "✅ Mock webhook successfully received alert body: %s",
            payload["content"]["text"],
        )

        # Check ACK in Redis Streams
        logger.info("7. Verifying message was ACKed in Redis Streams...")
        stream = consumed_msg["stream"]
        redis_client = worker.mq_manager.broker.redis_client
        pending = redis_client.xpending_range(
            stream,
            worker.mq_manager.consumer_group,
            min="-",
            max="+",
            count=10,
        )
        # Any pending with this message_id?
        msg_pending = [
            p for p in pending if p["message_id"].decode() == consumed_msg["message_id"]
        ]
        assert (
            len(msg_pending) == 0
        ), f"Message {consumed_msg['message_id']} is still pending in group!"
        logger.info(
            "✅ Message was ACKed in Redis Streams (0 pending for this message_id)."
        )

        logger.info("=" * 60)
        logger.info("🎉 T3 alert-worker END-TO-END VERIFICATION PASSED SUCCESSFULLY!")
        logger.info("=" * 60)

    finally:
        await webhook_runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
