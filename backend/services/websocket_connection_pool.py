"""
WebSocket Connection Pool Service

This service provides connection pooling and reuse to optimize
resource usage and improve performance.

Features:
- Connection pool management
- Connection health checks
- Connection warmup
- Pool statistics tracking
"""

import asyncio
import time
from typing import Dict, Set, Optional, List, Any
from datetime import datetime, timezone, timedelta
from enum import Enum

from core.logger import get_logger
from pydantic import BaseModel

logger = get_logger(__name__)


class ConnectionState(str, Enum):
    """States of a connection in the pool."""
    IDLE = "idle"
    ACTIVE = "active"
    CLOSING = "closing"
    CLOSED = "closed"
    UNHEALTHY = "unhealthy"


class PoolConfig(BaseModel):
    """Configuration for connection pool."""
    enabled: bool = True
    max_pool_size: int = 1000  # Maximum connections in pool
    max_idle_time_seconds: int = 300  # Close idle connections after 5 minutes
    health_check_interval_seconds: int = 60  # Check health every minute
    enable_warmup: bool = True  # Enable connection warmup
    warmup_connections: int = 10  # Number of connections to warm up


class PoolStats(BaseModel):
    """Statistics for connection pool."""
    total_connections: int = 0
    active_connections: int = 0
    idle_connections: int = 0
    unhealthy_connections: int = 0
    total_created: int = 0
    total_closed: int = 0
    total_reused: int = 0
    avg_idle_time_seconds: float = 0.0


class PooledConnection:
    """A pooled connection with metadata."""

    def __init__(self, websocket, user_id: str, connection_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.connection_id = connection_id
        self.state = ConnectionState.ACTIVE
        self.created_at = time.time()
        self.last_used_at = time.time()
        self.last_health_check = time.time()

    def mark_used(self) -> None:
        """Mark connection as used."""
        self.last_used_at = time.time()
        self.state = ConnectionState.ACTIVE

    def mark_idle(self) -> None:
        """Mark connection as idle."""
        self.last_used_at = time.time()
        self.state = ConnectionState.IDLE

    def get_age_seconds(self) -> float:
        """Get connection age in seconds."""
        return time.time() - self.created_at

    def get_idle_time_seconds(self) -> float:
        """Get idle time in seconds."""
        return time.time() - self.last_used_at


class ConnectionPoolService:
    """
    Service for managing WebSocket connection pool.

    Provides connection reuse, health monitoring, and
    automatic cleanup of idle connections.
    """

    def __init__(self, config: Optional[PoolConfig] = None):
        self.config = config or PoolConfig()
        self.stats = PoolStats()

        # Connection pool: {connection_id: PooledConnection}
        self.pool: Dict[str, PooledConnection] = {}

        # User connections: {user_id: set of connection_ids}
        self.user_connections: Dict[str, Set[str]] = {}

        # WebSocket to connection_id mapping
        self.websocket_to_connection: Dict[Any, str] = {}

        self._lock = asyncio.Lock()
        self._health_check_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Start the connection pool service."""
        if not self.config.enabled:
            logger.info("Connection pool disabled by configuration")
            return

        if self._running:
            return

        self._running = True

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info("Connection pool service started")

    async def stop(self) -> None:
        """Stop the connection pool service."""
        if not self._running:
            return

        self._running = False

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        await self.close_all()

        logger.info("Connection pool service stopped")

    async def add_connection(
        self,
        websocket: Any,
        user_id: str,
        connection_id: str
    ) -> None:
        """
        Add a connection to the pool.

        Args:
            websocket: WebSocket connection object
            user_id: User identifier
            connection_id: Unique connection identifier
        """
        if not self.config.enabled:
            return

        async with self._lock:
            # Check pool size limit
            if len(self.pool) >= self.config.max_pool_size:
                # Try to free some space by closing idle connections
                await self._close_idle_connections()

                if len(self.pool) >= self.config.max_pool_size:
                    logger.warning(
                        f"Connection pool full ({self.config.max_pool_size}), "
                        f"cannot add new connection"
                    )
                    return

            # Create pooled connection
            pooled_conn = PooledConnection(websocket, user_id, connection_id)

            self.pool[connection_id] = pooled_conn
            self.websocket_to_connection[websocket] = connection_id

            # Track user connections
            if user_id not in self.user_connections:
                self.user_connections[user_id] = set()
            self.user_connections[user_id].add(connection_id)

            # Update stats
            self.stats.total_connections += 1
            self.stats.active_connections += 1
            self.stats.total_created += 1

            logger.debug(
                f"Added connection to pool: {connection_id} "
                f"(pool size: {len(self.pool)})"
            )

    async def remove_connection(self, connection_id: str) -> None:
        """
        Remove a connection from the pool.

        Args:
            connection_id: Connection identifier
        """
        if not self.config.enabled:
            return

        async with self._lock:
            if connection_id not in self.pool:
                return

            pooled_conn = self.pool[connection_id]

            # Remove from user connections
            if pooled_conn.user_id in self.user_connections:
                self.user_connections[pooled_conn.user_id].discard(connection_id)

            # Remove from websocket mapping
            if pooled_conn.websocket in self.websocket_to_connection:
                del self.websocket_to_connection[pooled_conn.websocket]

            # Remove from pool
            del self.pool[connection_id]

            # Update stats
            self.stats.total_connections -= 1
            if pooled_conn.state == ConnectionState.ACTIVE:
                self.stats.active_connections -= 1
            elif pooled_conn.state == ConnectionState.IDLE:
                self.stats.idle_connections -= 1
            elif pooled_conn.state == ConnectionState.UNHEALTHY:
                self.stats.unhealthy_connections -= 1

            self.stats.total_closed += 1

            logger.debug(f"Removed connection from pool: {connection_id}")

    async def mark_connection_idle(self, connection_id: str) -> None:
        """
        Mark a connection as idle (available for reuse).

        Args:
            connection_id: Connection identifier
        """
        if not self.config.enabled:
            return

        async with self._lock:
            if connection_id not in self.pool:
                return

            pooled_conn = self.pool[connection_id]

            if pooled_conn.state == ConnectionState.ACTIVE:
                pooled_conn.mark_idle()
                self.stats.active_connections -= 1
                self.stats.idle_connections += 1

                logger.debug(f"Marked connection as idle: {connection_id}")

    async def mark_connection_active(self, connection_id: str) -> None:
        """
        Mark a connection as active (in use).

        Args:
            connection_id: Connection identifier
        """
        if not self.config.enabled:
            return

        async with self._lock:
            if connection_id not in self.pool:
                return

            pooled_conn = self.pool[connection_id]

            if pooled_conn.state == ConnectionState.IDLE:
                pooled_conn.mark_used()
                self.stats.idle_connections -= 1
                self.stats.active_connections += 1
                self.stats.total_reused += 1

                logger.debug(f"Marked connection as active: {connection_id}")

    async def get_user_connection(
        self,
        user_id: str
    ) -> Optional[PooledConnection]:
        """
        Get an existing idle connection for a user.

        Args:
            user_id: User identifier

        Returns:
            PooledConnection if found, None otherwise
        """
        if not self.config.enabled:
            return None

        async with self._lock:
            if user_id not in self.user_connections:
                return None

            # Find an idle connection for this user
            for connection_id in self.user_connections[user_id]:
                if connection_id in self.pool:
                    pooled_conn = self.pool[connection_id]

                    if pooled_conn.state == ConnectionState.IDLE:
                        # Mark as active
                        await self.mark_connection_active(connection_id)
                        return pooled_conn

            return None

    async def _health_check_loop(self) -> None:
        """Background loop for health checking connections."""
        while self._running:
            try:
                await asyncio.sleep(self.config.health_check_interval_seconds)
                await self._health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def _health_check(self) -> None:
        """Perform health check on all connections."""
        async with self._lock:
            now = time.time()
            unhealthy_connections = []

            for connection_id, pooled_conn in self.pool.items():
                # Check if connection is idle for too long
                if (pooled_conn.state == ConnectionState.IDLE and
                    pooled_conn.get_idle_time_seconds() > self.config.max_idle_time_seconds):
                    unhealthy_connections.append(connection_id)

                # Mark unhealthy if old and idle
                if (pooled_conn.get_age_seconds() > 3600 and
                    pooled_conn.get_idle_time_seconds() > self.config.max_idle_time_seconds):
                    pooled_conn.state = ConnectionState.UNHEALTHY
                    self.stats.unhealthy_connections += 1
                    self.stats.idle_connections -= 1

            # Close unhealthy connections
            for connection_id in unhealthy_connections:
                logger.info(f"Closing unhealthy connection: {connection_id}")
                await self._close_connection(connection_id)

    async def _close_idle_connections(self) -> None:
        """Close idle connections to free up pool space."""
        idle_connections = [
            conn_id for conn_id, conn in self.pool.items()
            if conn.state == ConnectionState.IDLE
        ]

        # Close oldest idle connections first
        idle_connections.sort(
            key=lambda cid: self.pool[cid].get_idle_time_seconds(),
            reverse=True
        )

        # Close up to 10% of pool
        to_close = min(len(idle_connections), max(1, len(self.pool) // 10))

        for connection_id in idle_connections[:to_close]:
            await self._close_connection(connection_id)

    async def _close_connection(self, connection_id: str) -> None:
        """Close a specific connection."""
        if connection_id not in self.pool:
            return

        pooled_conn = self.pool[connection_id]

        try:
            # Try to close WebSocket
            await pooled_conn.websocket.close()
        except Exception as e:
            logger.debug(f"Error closing WebSocket {connection_id}: {e}")

        # Remove from pool
        await self.remove_connection(connection_id)

    async def close_all(self) -> None:
        """Close all connections in the pool."""
        async with self._lock:
            connection_ids = list(self.pool.keys())

            for connection_id in connection_ids:
                await self._close_connection(connection_id)

    def get_stats(self) -> PoolStats:
        """Get pool statistics."""
        return self.stats

    def reset_stats(self) -> None:
        """Reset pool statistics."""
        self.stats = PoolStats()


# Global instance
_pool_service: Optional[ConnectionPoolService] = None


def get_connection_pool() -> ConnectionPoolService:
    """Get or create the global connection pool service instance."""
    global _pool_service
    if _pool_service is None:
        _pool_service = ConnectionPoolService()
    return _pool_service


async def start_connection_pool():
    """Initialize and start the connection pool service."""
    service = get_connection_pool()
    await service.start()
    logger.info(
        f"Connection pool initialized "
        f"(max_size={service.config.max_pool_size}, "
        f"max_idle={service.config.max_idle_time_seconds}s)"
    )
    return service
