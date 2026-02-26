"""Standardized retry policies for network/db/queue operations."""

from __future__ import annotations

from typing import Callable, Type

from utils.retry import with_retry, with_sync_retry


def network_retry(max_retries: int = 3):
    return with_retry(
        max_retries=max_retries,
        base_delay=0.5,
        max_delay=8.0,
        exceptions=(ConnectionError, TimeoutError),
        jitter=True,
    )


def queue_retry(max_retries: int = 5):
    return with_retry(
        max_retries=max_retries,
        base_delay=0.2,
        max_delay=5.0,
        exceptions=(Exception,),
        jitter=True,
    )


def db_retry(max_retries: int = 2):
    return with_retry(
        max_retries=max_retries,
        base_delay=0.1,
        max_delay=2.0,
        exceptions=(Exception,),
        jitter=False,
    )


def sync_io_retry(max_retries: int = 3):
    return with_sync_retry(
        max_retries=max_retries,
        base_delay=0.5,
        max_delay=4.0,
        exceptions=(Exception,),
        jitter=True,
    )
