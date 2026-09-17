"""Alembic environment configuration for async SQLAlchemy."""

import asyncio

# Import your Base and models
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from db.session import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# 连接串只从 DATABASE_URL 读取。alembic.ini 不再保留任何硬编码地址，
# 缺失时直接失败而不是回退 —— 否则漏配会把迁移打到错的库（审计 F-003）。
import os

_database_url = os.getenv("DATABASE_URL")

if not _database_url:
    raise RuntimeError(
        "DATABASE_URL is not set, and alembic.ini no longer carries a fallback URL "
        "(security audit F-003). Export DATABASE_URL before running alembic, or use "
        "./Scripts/sim.sh, which injects it from .env.local-sim."
    )

config.set_main_option("sqlalchemy.url", _database_url)

# Import all models to ensure they are registered with Base
# F1-7a: Added comprehensive model imports for tenant isolation
# 2026-09-07: restored — the import block below was accidentally deleted in
# d42c1e4, leaving target_metadata empty so `alembic revision --autogenerate`
# would emit DROP TABLE for the entire schema.
import models.ai_model  # noqa: F401
import models.ai_task  # noqa: F401
import models.ai_user_setting  # noqa: F401
import models.alert_note  # noqa: F401
import models.api_key  # noqa: F401
import models.asset  # noqa: F401
import models.audit_log  # noqa: F401
import models.blocked_ip  # noqa: F401
import models.case  # noqa: F401
import models.correlated_event  # noqa: F401
import models.correlation_rule  # noqa: F401
import models.event_similarity  # noqa: F401
import models.history  # noqa: F401
import models.ioc_hit  # noqa: F401
import models.marketplace  # noqa: F401
import models.monitor_history  # noqa: F401
import models.on_call_schedule  # noqa: F401
import models.playbook_approval  # noqa: F401
import models.playbook_definition  # noqa: F401
import models.playbook_node_attempt  # noqa: F401
import models.playbook_node_run  # noqa: F401
import models.playbook_output  # noqa: F401
import models.playbook_run  # noqa: F401
import models.prompt_registry  # noqa: F401
import models.rbac  # noqa: F401
import models.root_cause_analysis  # noqa: F401
import models.secret  # noqa: F401
import models.security_alert  # noqa: F401
import models.security_vulnerability  # noqa: F401
import models.siem_log  # noqa: F401
import models.threat_intel_cache  # noqa: F401
import models.trigger  # noqa: F401
import models.user  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async support.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
