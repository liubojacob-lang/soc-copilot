"""Retry utilities for automatic retry with exponential backoff.

This module provides:
- Decorator for automatic retry with configurable backoff
- Support for specific exception types
- Jitter to prevent thundering herd
"""

import asyncio
import random
from collections.abc import Callable
from functools import wraps
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    jitter: bool = True,
    on_retry: Callable[[int, Exception], None] = None,
):
    """Decorator for automatic retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch and retry
        jitter: Whether to add random jitter to delay
        on_retry: Optional callback called on each retry (attempt, exception)

    Returns:
        Decorated function with retry logic

    Example:
        @with_retry(max_retries=3, exceptions=(aiohttp.ClientError,))
        async def fetch_data():
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    return await response.json()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_error = e

                    if attempt == max_retries:
                        logger.error(
                            f"All {max_retries} retries exhausted for {func.__name__}: {e}"
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2**attempt), max_delay)

                    # Add jitter to prevent thundering herd
                    if jitter:
                        delay += random.SystemRandom().uniform(0, delay * 0.5)

                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {type(e).__name__}: {e}. "
                        f"Waiting {delay:.2f}s"
                    )

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(attempt + 1, e)

                    await asyncio.sleep(delay)

            raise last_error

        return wrapper

    return decorator


def with_sync_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    jitter: bool = True,
):
    """Decorator for synchronous functions with automatic retry.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch and retry
        jitter: Whether to add random jitter to delay

    Returns:
        Decorated function with retry logic
    """
    import time

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_error = e

                    if attempt == max_retries:
                        logger.error(
                            f"All {max_retries} retries exhausted for {func.__name__}: {e}"
                        )
                        raise

                    delay = min(base_delay * (2**attempt), max_delay)
                    if jitter:
                        delay += random.SystemRandom().uniform(0, delay * 0.5)

                    logger.warning(
                        f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}. "
                        f"Waiting {delay:.2f}s"
                    )

                    time.sleep(delay)

            raise last_error

        return wrapper

    return decorator
