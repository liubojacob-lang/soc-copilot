"""Cross-process lock used to serialize database migrations.

uvicorn workers each run the application lifespan; without a lock they race
on `alembic upgrade` (observed with --workers 4: the losers crash on the
alembic_version creation race). The first process to hold the lock migrates;
the rest wait, then no-op because the schema is already at head.

POSIX-only (fcntl). Windows dev environments run a single worker and skip
the lock (callers fall back to a plain call).
"""

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

# backend/ directory: this file lives in backend/services/
BACKEND_DIR = Path(__file__).resolve().parent.parent
LOCK_FILENAME = ".alembic.lock"


@contextmanager
def migration_process_lock() -> Iterator[None]:
    """Hold an exclusive cross-process lock for the duration of a block."""
    lock_path = (BACKEND_DIR / LOCK_FILENAME).resolve()
    if not lock_path.is_relative_to(BACKEND_DIR.resolve()):
        raise RuntimeError("Migration lock path escaped backend directory")
    with lock_path.open("w") as lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
