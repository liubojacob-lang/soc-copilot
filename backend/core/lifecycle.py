"""Lifecycle management for application services.

This module provides a structured way to manage application startup and shutdown
of various services (database, queue managers, schedulers, etc.).

Key components:
- LifecycleService: Base class for services with lifecycle management
- LifecycleManager: Manages registration, startup, and shutdown of services
- ServicePriority: Defines startup order (lower priority starts first)

Usage:
    from core.lifecycle import LifecycleService, LifecycleManager, ServicePriority

    class DatabaseService(LifecycleService):
        @property
        def name(self) -> str:
            return "database"

        @property
        def priority(self) -> ServicePriority:
            return ServicePriority.CRITICAL

        async def start(self) -> None:
            await init_db()

        async def stop(self) -> None:
            await engine.dispose()

    # Register and start
    manager = LifecycleManager()
    manager.register(DatabaseService())
    await manager.start_all()
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class ServicePriority(IntEnum):
    """Service startup priority (lower value = starts first).

    Services are started in ascending order of priority and stopped
    in descending order.
    """

    CRITICAL = 0  # Database, configuration - must start first
    ESSENTIAL = 10  # Auth, cache, rate limiter
    NORMAL = 20  # Business services
    OPTIONAL = 30  # Monitoring, metrics, background tasks


@dataclass
class ServiceState:
    """State of a lifecycle service.

    Attributes:
        name: Service name
        started: Whether the service has been started
        error: Error that occurred during start/stop (if any)
        started_at: Timestamp when service was started
        stopped_at: Timestamp when service was stopped
    """

    name: str
    started: bool = False
    error: Exception | None = None
    started_at: datetime | None = None
    stopped_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "name": self.name,
            "started": self.started,
            "error": str(self.error) if self.error else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
        }


class LifecycleService(ABC):
    """Base class for services with lifecycle management.

    Services should inherit from this class and implement start() and stop()
    methods. The priority property determines startup order, and dependencies
    can be specified to ensure correct initialization order.

    Example:
        class CacheService(LifecycleService):
            def __init__(self):
                self._cache = None

            @property
            def name(self) -> str:
                return "cache"

            @property
            def priority(self) -> ServicePriority:
                return ServicePriority.ESSENTIAL

            @property
            def dependencies(self) -> List[str]:
                return ["database"]  # Requires database to be started first

            async def start(self) -> None:
                self._cache = await create_cache()

            async def stop(self) -> None:
                if self._cache:
                    await self._cache.close()
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Service name for logging and identification.

        Must be unique across all registered services.
        """
        pass

    @property
    def priority(self) -> ServicePriority:
        """Startup priority (lower starts first).

        Override this to change the default priority.
        """
        return ServicePriority.NORMAL

    @property
    def dependencies(self) -> list[str]:
        """List of service names this service depends on.

        The lifecycle manager will ensure dependencies are started
        before this service.
        """
        return []

    @abstractmethod
    async def start(self) -> None:
        """Start the service.

        This method should initialize the service and make it ready for use.
        It should raise an exception if the service cannot be started.
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the service.

        This method should clean up resources and shut down the service.
        It should not raise exceptions - errors should be logged.
        """
        pass

    async def health_check(self) -> bool:
        """Check if the service is healthy.

        Override this to implement custom health checks.
        Returns True by default.
        """
        return True

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} priority={self.priority.name}>"


class LifecycleManager:
    """Manages application lifecycle services.

    This class handles:
    - Registration of lifecycle services
    - Ordered startup based on priority and dependencies
    - Graceful shutdown in reverse order
    - Error handling and rollback on startup failure
    - Service state tracking

    Example:
        manager = LifecycleManager()

        # Register services
        manager.register(DatabaseService())
        manager.register(CacheService())
        manager.register(WorkerService())

        # Start all services
        try:
            started = await manager.start_all()
            logger.info(f"Started {len(started)} services")
        except Exception as e:
            logger.error(f"Failed to start services: {e}")
            raise

        # ... application runs ...

        # Stop all services
        await manager.stop_all()
    """

    def __init__(self):
        self._services: dict[str, LifecycleService] = {}
        self._states: dict[str, ServiceState] = {}
        self._started = False
        self._startup_order: list[str] = []

    def register(self, service: LifecycleService) -> None:
        """Register a lifecycle service.

        Args:
            service: The service to register

        Raises:
            ValueError: If a service with the same name is already registered
        """
        if service.name in self._services:
            raise ValueError(f"Service '{service.name}' is already registered")

        self._services[service.name] = service
        self._states[service.name] = ServiceState(name=service.name)
        logger.debug(
            f"Registered lifecycle service: {service.name} (priority={service.priority.name})"
        )

    def get(self, name: str) -> LifecycleService | None:
        """Get a registered service by name.

        Args:
            name: Service name

        Returns:
            The service instance or None if not found
        """
        return self._services.get(name)

    def get_state(self, name: str) -> ServiceState | None:
        """Get the state of a service.

        Args:
            name: Service name

        Returns:
            The service state or None if not found
        """
        return self._states.get(name)

    def get_all_states(self) -> dict[str, ServiceState]:
        """Get all service states.

        Returns:
            Dictionary of service name to state
        """
        return self._states.copy()

    def _resolve_startup_order(self) -> list[str]:
        """Resolve the correct startup order based on priority and dependencies.

        Returns:
            List of service names in startup order

        Raises:
            ValueError: If circular dependencies are detected
        """
        # Sort by priority first
        sorted_services = sorted(
            self._services.values(), key=lambda s: s.priority.value
        )

        # Build dependency graph
        visited = set()
        order = []
        temp_visited = set()

        def visit(service: LifecycleService):
            if service.name in temp_visited:
                raise ValueError(
                    f"Circular dependency detected involving: {service.name}"
                )

            if service.name in visited:
                return

            temp_visited.add(service.name)

            # Visit dependencies first
            for dep_name in service.dependencies:
                if dep_name not in self._services:
                    logger.warning(
                        f"Service '{service.name}' depends on '{dep_name}' which is not registered"
                    )
                    continue
                visit(self._services[dep_name])

            temp_visited.remove(service.name)
            visited.add(service.name)
            order.append(service.name)

        for service in sorted_services:
            visit(service)

        return order

    async def start_all(self) -> list[str]:
        """Start all services in the correct order.

        Services are started based on their priority and dependencies.
        If any service fails to start, all previously started services
        are stopped (rollback).

        Returns:
            List of successfully started service names

        Raises:
            Exception: If any service fails to start
        """
        if self._started:
            logger.warning("Lifecycle manager already started")
            return []

        logger.info(f"Starting {len(self._services)} lifecycle services...")

        startup_order = self._resolve_startup_order()
        started_services: list[str] = []

        for service_name in startup_order:
            service = self._services[service_name]
            state = self._states[service_name]

            try:
                logger.info(
                    f"Starting service: {service_name} (priority={service.priority.name})"
                )
                await service.start()

                state.started = True
                state.started_at = datetime.utcnow()
                started_services.append(service_name)

                logger.info(f"Service started: {service_name}")

            except Exception as e:
                state.error = e
                logger.error(f"Failed to start service '{service_name}': {e}")

                # Rollback started services
                await self._rollback(started_services)
                raise

        self._started = True
        self._startup_order = started_services

        logger.info(f"All {len(started_services)} services started successfully")
        return started_services

    async def stop_all(self) -> list[str]:
        """Stop all services in reverse startup order.

        Services are stopped in the reverse order they were started.
        Errors during shutdown are logged but do not prevent other
        services from being stopped.

        Returns:
            List of stopped service names
        """
        if not self._started:
            logger.debug("Lifecycle manager not started, nothing to stop")
            return []

        logger.info("Stopping lifecycle services...")

        stopped_services: list[str] = []

        # Stop in reverse order
        for service_name in reversed(self._startup_order):
            service = self._services.get(service_name)
            state = self._states.get(service_name)

            if service is None or state is None:
                continue

            if not state.started:
                continue

            try:
                logger.info(f"Stopping service: {service_name}")
                await service.stop()

                state.started = False
                state.stopped_at = datetime.utcnow()
                stopped_services.append(service_name)

                logger.info(f"Service stopped: {service_name}")

            except Exception as e:
                state.error = e
                logger.error(f"Error stopping service '{service_name}': {e}")

        self._started = False
        logger.info(f"Stopped {len(stopped_services)} services")

        return stopped_services

    async def _rollback(self, started_services: list[str]) -> None:
        """Rollback started services on startup failure.

        Args:
            started_services: List of services that were successfully started
        """
        logger.warning(f"Rolling back {len(started_services)} started services...")

        for service_name in reversed(started_services):
            service = self._services.get(service_name)
            state = self._states.get(service_name)

            if service is None:
                continue

            try:
                await service.stop()
                if state:
                    state.started = False
                    state.stopped_at = datetime.utcnow()
            except Exception as e:
                logger.error(f"Rollback failed for '{service_name}': {e}")

    async def health_check(self) -> dict[str, bool]:
        """Check health of all started services.

        Returns:
            Dictionary of service name to health status
        """
        results = {}

        for service_name, service in self._services.items():
            state = self._states.get(service_name)

            if state and state.started:
                try:
                    results[service_name] = await service.health_check()
                except Exception as e:
                    logger.error(f"Health check failed for '{service_name}': {e}")
                    results[service_name] = False
            else:
                results[service_name] = False

        return results

    @property
    def is_started(self) -> bool:
        """Check if the manager has been started."""
        return self._started

    @property
    def service_count(self) -> int:
        """Get the number of registered services."""
        return len(self._services)


# Global lifecycle manager instance
_lifecycle_manager: LifecycleManager | None = None


def get_lifecycle_manager() -> LifecycleManager:
    """Get or create the global lifecycle manager.

    Returns:
        The global LifecycleManager instance
    """
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


def reset_lifecycle_manager() -> None:
    """Reset the global lifecycle manager.

    This is primarily useful for testing.
    """
    global _lifecycle_manager
    _lifecycle_manager = None
