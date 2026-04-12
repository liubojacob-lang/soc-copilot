#!/usr/bin/env python3
"""
Alert Worker - 消费告警并发送通知

从 Redis Streams 消费告警消息，并通过多渠道发送通知。
支持水平扩展，多个 Worker 实例可以并行处理。

用法:
    python workers/alert_worker.py [worker_id]

环境变量:
    REDIS_URL: Redis 连接 URL (默认: redis://redis:6379/0)
    WORKER_ID: Worker 标识 (默认: 1)
    LOG_LEVEL: 日志级别 (默认: INFO)
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.message_queue_manager import get_message_queue_manager
from services.notification_service import get_notification_service

# 配置日志
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class AlertWorker:
    """
    告警 Worker

    从消息队列消费告警并发送通知
    """

    def __init__(self, worker_id: str):
        """
        初始化 Worker

        Args:
            worker_id: Worker 标识
        """
        self.worker_id = worker_id
        self.mq_manager = get_message_queue_manager()
        self.notification_service = get_notification_service()

        self.running = False
        self.shutdown_requested = False

        # 统计信息
        self.processed_count = 0
        self.error_count = 0
        self.start_time = datetime.now()

        logger.info(f"Alert Worker {worker_id} initialized")

    async def run(self):
        """主循环"""
        self.running = True
        logger.info("=" * 60)
        logger.info(f"Alert Worker {self.worker_id} started")
        logger.info("=" * 60)

        # 设置信号处理器
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

        # 启动统计信息打印任务
        stats_task = asyncio.create_task(self._print_stats())

        try:
            while not self.shutdown_requested:
                try:
                    # 消费消息
                    messages = await self.mq_manager.consume_alerts_async(
                        worker_id=self.worker_id,
                        count=1,
                        block=5000,  # 5秒超时
                        priority_order=True,  # 优先处理 critical 告警
                    )

                    if messages:
                        for message in messages:
                            await self._process_message(message)
                            self.processed_count += 1
                    else:
                        logger.debug(
                            f"Worker {self.worker_id}: No messages, waiting..."
                        )

                except Exception as e:
                    logger.error(f"Error in worker loop: {e}")
                    self.error_count += 1
                    await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.running = False
            stats_task.cancel()
            logger.info(
                f"Worker {self.worker_id} stopped. Processed: {self.processed_count}, Errors: {self.error_count}"
            )

    async def _process_message(self, message: dict):
        """
        处理单条消息

        Args:
            message: 消息数据
        """
        message_id = message.get("message_id", "unknown")
        stream = message.get("stream", "unknown")
        alert = message.get("alert", {})
        severity = message.get("severity", "medium")

        try:
            logger.info(f"📨 Processing alert {message_id} (severity: {severity})")

            # 发送通知
            results = await self.notification_service.send_alert(alert)

            # 记录结果
            success_count = sum(1 for v in results.values() if v)
            total_count = len(results)

            if total_count > 0:
                if success_count == total_count:
                    logger.info("  ✓ All notifications sent successfully")
                else:
                    logger.warning(
                        f"  ⚠ {success_count}/{total_count} notifications succeeded"
                    )
            else:
                logger.warning("  ⚠ No notifications configured")

            # 确认消息处理完成
            ack_success = await self.mq_manager.acknowledge_async(stream, message_id)

            if ack_success:
                logger.info(f"  ✓ Message {message_id} acknowledged")
            else:
                logger.error(f"  ✗ Failed to acknowledge message {message_id}")

        except Exception as e:
            logger.error(f"  ✗ Error processing message {message_id}: {e}")
            # 消息未被确认，将保留在待处理列表中供其他 worker 处理

    async def _print_stats(self):
        """定期打印统计信息"""
        while self.running:
            await asyncio.sleep(60)  # 每60秒打印一次

            if self.processed_count > 0:
                uptime = (datetime.now() - self.start_time).total_seconds()
                rate = self.processed_count / uptime if uptime > 0 else 0

                logger.info(
                    f"📊 Worker {self.worker_id} stats: "
                    f"Processed={self.processed_count}, "
                    f"Errors={self.error_count}, "
                    f"Rate={rate:.2f} msg/sec, "
                    f"Uptime={uptime:.0f}s"
                )

                # 打印队列统计
                queue_stats = self.mq_manager.get_queue_stats()
                for severity, stats in queue_stats.items():
                    if stats["length"] > 0:
                        logger.info(
                            f"  Queue {severity}: {stats['length']} messages, {stats['pending']} pending"
                        )

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.shutdown_requested = True


async def main():
    """主函数"""
    # 获取 Worker ID
    worker_id = os.getenv("WORKER_ID", "1")

    # 也可以从命令行参数获取
    if len(sys.argv) > 1:
        worker_id = sys.argv[1]

    # 创建并启动 Worker
    worker = AlertWorker(worker_id)

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
