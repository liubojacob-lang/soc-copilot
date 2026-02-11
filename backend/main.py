"""SOC Copilot API - Main application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.logger import get_logger
from core.config import settings
from db.session import init_db, AsyncSessionLocal
from routers import (
    alert,
    report,
    timeline,
    history,
    assets,
    ioc_hits,
    threat_intel,
    playbook,
    playbook_definitions,
    auth,
    users,
    api_keys,
    audit,
    webhooks,
    triggers,
    secrets,
    admin_settings,
    dify,  # v0.7.4: Dify workflow integration
    ai,  # Phase 2: AI Copilot
    ueba,  # Phase 3: UEBA analytics
    threat_hunting,  # Phase 3: Threat hunting
    marketplace,  # Phase 4: Playbook marketplace
    cloud_native,  # Phase 4: Cloud native security
)
from middleware import AuditMiddleware

logger = get_logger(__name__)


# Custom middleware to add credentials header for specific origins
class AddCredentialsMiddleware(BaseHTTPMiddleware):
    """Add credentials header for specific origins."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin", "")
        # Allow credentials for localhost origins
        if "localhost" in origin or "127.0.0.1" in origin:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


async def create_bootstrap_admin():
    """Create bootstrap admin user if no users exist."""
    from repositories.user_repository import UserRepository
    from models.user import UserRole
    from core.security import get_password_hash

    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user_count = await user_repo.count()

        if user_count == 0:
            logger.info("No users found. Creating bootstrap admin user...")
            logger.info(
                f"Bootstrap admin username: {settings.bootstrap_admin_username}"
            )
            logger.info(f"Bootstrap admin email: {settings.bootstrap_admin_email}")
            logger.warning("CHANGE THE DEFAULT PASSWORD AFTER FIRST LOGIN!")

            hashed_password = get_password_hash(settings.bootstrap_admin_password)
            admin_user = await user_repo.create(
                username=settings.bootstrap_admin_username,
                email=settings.bootstrap_admin_email,
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
            )

            logger.info(f"Bootstrap admin created with ID: {admin_user.id}")

            # Create audit log
            from repositories.audit_repository import AuditRepository

            audit_repo = AuditRepository(session)
            await audit_repo.create(
                action="user:create",
                method="bootstrap",
                path="/bootstrap",
                status_code=200,
                user_id=admin_user.id,
                target_type="user",
                target_id=admin_user.id,
                extra_json={"bootstrap": True},
            )
            await session.commit()

            logger.info("Bootstrap admin creation complete!")


async def run_migrations():
    """Run Alembic database migrations on startup."""
    from pathlib import Path
    from alembic.config import Config
    from alembic import command

    alembic_dir = Path(__file__).parent / "migrations_alembic"
    ini_path = Path(__file__).parent / "alembic.ini"

    if alembic_dir.exists() and ini_path.exists():
        try:
            config = Config(str(ini_path))
            config.set_main_option("script_location", str(alembic_dir))
            # Disable fileConfig to avoid logging conflicts
            import logging

            logging.getLogger("alembic").setLevel(logging.WARNING)
            # Run migrations in a separate process to avoid event loop conflicts
            import subprocess

            result = subprocess.run(
                ["python", "-m", "alembic", "-c", str(ini_path), "upgrade", "head"],
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent),
            )
            if result.returncode == 0:
                logger.info("Database migrations completed")
            else:
                logger.warning(f"Migration output: {result.stderr or result.stdout}")
        except Exception as e:
            logger.warning(f"Migration failed (might be ok if already applied): {e}")


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Application lifespan manager.

    Initializes database on startup and creates bootstrap admin if needed.
    """
    # Startup
    logger.info(f"Initializing SOC Copilot API v0.7.4")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Playbook Engine: ENABLED (DAG-based with Node Plugin System)")
    logger.info(f"Trigger System: ENABLED (webhook + cron)")
    logger.info(f"Run Queue: ENABLED (max_concurrent={settings.run_queue_max})")
    logger.info(f"Secrets Management: ENABLED (Fernet encryption)")
    logger.info(
        f"External TI: {'ENABLED' if settings.allow_external_ti else 'DISABLED'}"
    )
    logger.info(f"Authentication: ENABLED")
    logger.info(f"RBAC: ENABLED (admin, analyst, auditor)")
    logger.info(f"Audit Logging: ENABLED")

    # P1: 生产环境敏感配置校验
    if settings.environment == "production":
        _fail = []
        if (
            not settings.jwt_secret
            or settings.jwt_secret == "CHANGE_THIS_IN_PRODUCTION_MIN_32_CHARS_LONG"
        ):
            _fail.append("JWT_SECRET must be set to a secure value (min 32 chars)")
        if settings.bootstrap_admin_password == "admin123!":
            _fail.append("BOOTSTRAP_ADMIN_PASSWORD must be changed from default")
        if not settings.secret_encryption_key and not settings.strict_production_checks:
            logger.warning(
                "SECRET_ENCRYPTION_KEY is not set; secrets management will be unavailable. "
                "Set STRICT_PRODUCTION_CHECKS=1 to fail startup when key is missing."
            )
        elif not settings.secret_encryption_key and settings.strict_production_checks:
            _fail.append(
                "SECRET_ENCRYPTION_KEY must be set in production when STRICT_PRODUCTION_CHECKS=1"
            )
        if _fail:
            msg = "Production config validation failed: " + "; ".join(_fail)
            if settings.strict_production_checks:
                logger.critical(msg)
                raise RuntimeError(msg)
            logger.critical(
                msg + " (startup allowed; set STRICT_PRODUCTION_CHECKS=1 to fail)"
            )

    # Run migrations before initializing database
    await run_migrations()
    await init_db()
    logger.info("Database initialized")

    # Create bootstrap admin if no users exist
    await create_bootstrap_admin()

    # v0.7.4: Initialize queue manager
    from services.run_queue_manager import RunQueueManager, set_run_queue_manager

    queue_manager = RunQueueManager(AsyncSessionLocal)
    set_run_queue_manager(queue_manager)
    await queue_manager.recover_runs()
    logger.info(
        f"Run queue manager initialized (max_concurrent={settings.run_queue_max})"
    )

    # v0.7.4: Load node plugins
    from pathlib import Path
    from playbook_engine.v7_dag.registry import NodeRegistry, get_node_registry

    node_registry = NodeRegistry()
    plugin_dir = Path(__file__).parent / "playbook_engine" / "v7_dag" / "plugins"
    plugin_count = node_registry.auto_load_plugins(plugin_dir)
    logger.info(f"Loaded {plugin_count} node plugins")

    # Start cron scheduler
    from services.cron_scheduler_service import CronSchedulerService, set_cron_scheduler

    cron_scheduler = CronSchedulerService(AsyncSessionLocal)
    set_cron_scheduler(cron_scheduler)
    await cron_scheduler.start()
    logger.info("Cron scheduler started")

    # v0.7.4: Start queue processor
    await queue_manager.start_background_processor()

    yield

    # Shutdown
    logger.info("Shutting down SOC Copilot API")
    if cron_scheduler:
        await cron_scheduler.stop()
        logger.info("Cron scheduler stopped")

    # v0.7.4: Stop queue processor
    if queue_manager:
        await queue_manager.stop_background_processor()
        logger.info("Queue processor stopped")


app = FastAPI(
    title="SOC Copilot API",
    description="Security Operations Center Analysis Platform with Playbook Engine, OTX Threat Intelligence, and Multi-User Support",
    version="0.7.4",
    lifespan=lifespan,
)

# Middleware to set user_id in request.state for audit middleware
# Must be added BEFORE AuditMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SetUserStateMiddleware(BaseHTTPMiddleware):
    """Middleware to set user_id in request.state for audit middleware."""

    async def dispatch(self, request: Request, call_next):
        """Set current user in request.state for audit middleware."""
        # Try to get user from Authorization header only
        # API key lookup is done in the auth dependency to avoid DB calls in middleware
        auth_header = request.headers.get("authorization")
        user_id = None

        if auth_header and auth_header.startswith("Bearer "):
            from core.security import decode_token

            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            if payload:
                user_id = payload.get("sub")

        request.state.user_id = user_id
        response = await call_next(request)
        return response


# CORS: 生产环境通过 CORS_ORIGINS 配置允许来源，未配置时默认 ["*"]
_cors_origins = (
    [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if settings.cors_origins
    else ["*"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "Content-Range"],
)

# Add credentials header for localhost origins
app.add_middleware(AddCredentialsMiddleware)

# Set user state middleware (must be before AuditMiddleware)
app.add_middleware(SetUserStateMiddleware)

# Audit middleware (must be added after SetUserStateMiddleware)
app.add_middleware(AuditMiddleware)


# Include routers - auth first, then others
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(audit.router)
app.include_router(alert.router)
app.include_router(report.router)
app.include_router(timeline.router)
app.include_router(history.router)
app.include_router(assets.router)
app.include_router(ioc_hits.router)
app.include_router(threat_intel.router)
app.include_router(playbook.router)
app.include_router(playbook_definitions.router)
app.include_router(webhooks.router)
app.include_router(triggers.router)
app.include_router(secrets.router)  # v0.7.4: Secrets management
app.include_router(admin_settings.router)  # System settings
app.include_router(dify.router)  # v0.7.4: Dify workflow integration
app.include_router(ai.router)  # Phase 2: AI Copilot service
app.include_router(ueba.router)  # Phase 3: UEBA analytics
app.include_router(threat_hunting.router)  # Phase 3: Threat hunting
app.include_router(marketplace.router)  # Phase 4: Playbook marketplace
app.include_router(cloud_native.router)  # Phase 4: Cloud native security


# Global OPTIONS handler for CORS preflight
from fastapi.responses import Response


@app.options("/{path:path}")
async def options_handler(path: str, request: Request):
    """Handle OPTIONS preflight requests for CORS."""
    origin = request.headers.get("origin", "*")
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "600",
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "SOC Copilot API v0.7", "auth": "enabled"}


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.7.4", "auth": "enabled"}


if __name__ == "__main__":
    import uvicorn

    # Increase timeout for long AI analysis requests (120 seconds)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_keep_alive=120,
        timeout_graceful_shutdown=30,
    )
