"""SOC Copilot API - Main application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.logger import get_logger
from observability.logging import setup_json_logging
from observability.tracing import setup_tracing
from core.config import settings
from db.session import init_db, AsyncSessionLocal
from routers import (
    alert,
    report,
    ai_models,  # AI model management
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
    ai_tasks,  # v0.7.7: AI background task queue
    ueba,  # Phase 3: UEBA analytics
    threat_hunting,  # Phase 3: Threat hunting
    marketplace,  # Phase 4: Playbook marketplace
    cloud_native,  # Phase 4: Cloud native security
    health,  # v0.8.2: Enhanced health check and metrics
    monitor,  # Real-time monitoring dashboard
    correlation,  # v0.8.0: Event correlation engine
    security_alerts,  # v0.9.0: External security alert ingestion
    alert_enrichment,  # v0.9.0: Threat intelligence enrichment
    notifications,  # v0.9.x: Notification channels and queue status
    alert_stream,  # v1.2.0: Real-time alert stream (replaces Wazuh)
)
from routers import websocket as ws_router  # v0.8.5: WebSocket real-time alerts
from routers import websocket_filters  # v0.9.0: WebSocket filter management
from routers import monitoring_alerts  # v0.9.1: Monitoring alert rules
from routers import export  # v0.8.5: Data export functionality
from routers import system_dashboard  # v0.8.5: System health dashboard
from middleware import (
    AuditMiddleware,
    TraceIDMiddleware,
    RequestContextMiddleware,
    ObservabilityMiddleware,
    ExceptionCaptureMiddleware,
    setup_trace_logging,
    setup_exception_handlers,
    ResourceAuthorizationMiddleware,
    IdempotencyMiddleware,  # P0-3: Request deduplication
)
from middleware.tenant_middleware import TenantMiddleware
from middleware.rate_limiter import init_rate_limiter, close_rate_limiter  # v0.8.5: Async rate limiter
from middleware.performance import PerformanceMiddleware  # v0.8.5: Performance monitoring

setup_json_logging(settings.log_level)
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
    from models.user import UserModel, UserRole
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
            logger.info("Bootstrap admin password: [REDACTED for security]")
            logger.warning("CHANGE THE DEFAULT PASSWORD AFTER FIRST LOGIN!")

            hashed_password = get_password_hash(settings.bootstrap_admin_password)
            admin_user = await user_repo.create(
                username=settings.bootstrap_admin_username,
                email=settings.bootstrap_admin_email,
                hashed_password=hashed_password,
                role=UserRole.ADMIN,
                must_change_password=True,  # v0.8.4: Force password change on first login
            )

            logger.info(f"Bootstrap admin created with ID: {admin_user.id}")
            logger.warning("Bootstrap admin must change password on first login!")

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
                extra_json={"bootstrap": True, "must_change_password": True},
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
            import sys

            result = subprocess.run(
                [sys.executable, "-m", "alembic", "-c", str(ini_path), "upgrade", "head"],
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
    logger.info(f"Initializing SOC Copilot API v0.8.0")
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
    from core.security_validators import run_production_security_checks
    
    security_errors = run_production_security_checks()
    if security_errors:
        msg = "Production security validation failed: " + "; ".join(security_errors)
        if settings.strict_production_checks:
            logger.critical(msg)
            raise RuntimeError(msg)
        logger.critical(
            msg + " (startup allowed; set STRICT_PRODUCTION_CHECKS=true to fail)"
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

    # v0.7.7: Start AI task processor
    from services.ai_task_service import start_ai_task_processor, stop_ai_task_processor
    await start_ai_task_processor()
    logger.info("AI task processor started")

    # v0.8.5: Initialize async rate limiter
    await init_rate_limiter()
    logger.info("Rate limiter initialized")

    # v0.9.1: Start WebSocket monitoring service
    from services.websocket_monitoring import start_websocket_monitoring
    await start_websocket_monitoring()
    logger.info("WebSocket monitoring service started")

    # v0.9.1: Initialize alert evaluator
    from services.alert_evaluator import start_alert_evaluator
    await start_alert_evaluator()
    logger.info("Alert evaluator initialized")

    # v0.9.2: Initialize message compression service
    from services.websocket_compression import start_compression_service
    await start_compression_service()
    logger.info("Message compression service initialized")

    # v0.9.2: Start message batch service
    from services.message_batch_service import start_batch_service
    await start_batch_service()
    logger.info("Message batch service initialized")

    # v0.9.2: Start connection pool service
    from services.websocket_connection_pool import start_connection_pool
    await start_connection_pool()
    logger.info("Connection pool service initialized")

    # v0.8.5: Start audit log archival background task
    if settings.audit_log_cleanup_enabled:
        from services.audit_archive_service import run_scheduled_archival
        import asyncio
        archival_task = asyncio.create_task(run_scheduled_archival(AsyncSessionLocal))
        logger.info("Audit log archival service started")

    # v1.2.0: Initialize real-time alert stream service (replaces Wazuh)
    from services.alert_stream_service import init_alert_stream_service

    try:
        stream_service = await init_alert_stream_service(
            aggregation_window_seconds=60,  # 1 minute aggregation window
            max_buffer_size=10000,  # Max 10k alerts in buffer
            max_history_size=1000  # Keep last 1000 alerts
        )
        logger.info("Real-time alert stream service initialized")
    except Exception as e:
        logger.warning(f"Alert stream service initialization failed: {e}")
        # Continue without alert stream

    yield

    # Shutdown
    logger.info("Shutting down SOC Copilot API")

    # v0.8.5: Close rate limiter
    await close_rate_limiter()
    logger.info("Rate limiter closed")

    # v0.9.1: Stop WebSocket monitoring service
    from services.websocket_monitoring import get_websocket_monitoring
    monitoring_service = get_websocket_monitoring()
    await monitoring_service.stop()
    logger.info("WebSocket monitoring service stopped")

    # v0.7.7: Stop AI task processor
    await stop_ai_task_processor()
    logger.info("AI task processor stopped")
    
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
    version="0.8.0",
    lifespan=lifespan,
)

# Setup Prometheus metrics
from core.metrics import setup_metrics
setup_metrics(app)
setup_tracing(app, service_name="soc-backend")

# Middleware to set user_id in request.state for audit middleware
# Must be added BEFORE AuditMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp


class SetUserStateMiddleware(BaseHTTPMiddleware):
    """Middleware to set user_id and user_role in request.state for audit and authorization middleware."""

    async def dispatch(self, request: Request, call_next):
        """Set current user in request.state for audit and authorization middleware."""
        # Try to get user from Authorization header only
        # API key lookup is done in the auth dependency to avoid DB calls in middleware
        auth_header = request.headers.get("authorization")
        user_id = None
        user_role = None

        if auth_header and auth_header.startswith("Bearer "):
            from core.security import decode_token

            token = auth_header.split(" ")[1]
            payload = decode_token(token)
            if payload:
                user_id = payload.get("sub")
                user_role = payload.get("role")

        request.state.user_id = user_id
        request.state.user_role = user_role
        response = await call_next(request)
        return response


# CORS: 生产环境通过 CORS_ORIGINS 配置允许来源，未配置时开发环境允许 ["*"]
# 安全增强: 生产环境不允许通配符 "*"
if settings.environment == "production":
    if not settings.cors_origins:
        raise RuntimeError(
            "CORS_ORIGINS must be configured in production. "
            "Example: CORS_ORIGINS=https://yourdomain.com,https://admin.yourdomain.com"
        )
    _cors_origins = (
        [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    )
    # v0.8.1: Production CORS security - reject wildcard origins
    if "*" in _cors_origins:
        raise RuntimeError(
            "CORS_ORIGINS cannot contain wildcard '*' in production. "
            "Specify explicit origins like https://yourdomain.com"
        )
else:
    # 开发环境允许所有来源用于本地测试
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

# v0.8.5: Performance monitoring middleware (should be early to capture all requests)
if settings.performance_monitoring_enabled:
    app.add_middleware(
        PerformanceMiddleware,
        slow_request_threshold=settings.slow_request_threshold,
    )

# Trace ID middleware (must be first to capture all requests)
app.add_middleware(TraceIDMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(ExceptionCaptureMiddleware)

# Set user state middleware (must be before AuditMiddleware)
app.add_middleware(SetUserStateMiddleware)

# Audit middleware (must be added after SetUserStateMiddleware)
app.add_middleware(AuditMiddleware)

# Resource authorization middleware (must be after SetUserStateMiddleware)
app.add_middleware(ResourceAuthorizationMiddleware)

# Setup global exception handlers
setup_exception_handlers(app)

# Setup trace logging
setup_trace_logging()


# Include routers - health first (no auth required), then auth, then others
app.include_router(health.router)  # v0.8.2: Enhanced health check and metrics
app.include_router(correlation.router)  # v0.8.0: Event correlation engine
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(api_keys.router)
app.include_router(audit.router)
app.include_router(alert.router)
app.include_router(report.router)
app.include_router(ai_models.router)  # AI model management
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
app.include_router(ai_tasks.router)  # v0.7.7: AI background task queue
app.include_router(ueba.router)  # Phase 3: UEBA analytics
app.include_router(threat_hunting.router)  # Phase 3: Threat hunting
app.include_router(marketplace.router)  # Phase 4: Playbook marketplace
app.include_router(cloud_native.router)  # Phase 4: Cloud native security
app.include_router(monitor.router)  # Real-time monitoring dashboard
app.include_router(security_alerts.router)  # v0.9.0: External security alert ingestion
app.include_router(alert_enrichment.router)  # v0.9.0: Threat intelligence enrichment
app.include_router(notifications.router)  # v0.9.x: Notification channels and queue status
from routers import alerts_lifecycle  # v0.9.0: Alert lifecycle management
app.include_router(alerts_lifecycle.router)  # v0.9.0: Alert lifecycle management
app.include_router(ws_router.router)  # v0.8.5: WebSocket real-time alerts
app.include_router(websocket_filters.router)  # v0.9.0: WebSocket filter management
app.include_router(monitoring_alerts.router)  # v0.9.1: Monitoring alert rules
app.include_router(export.router)  # v0.8.5: Data export functionality
app.include_router(system_dashboard.router)  # v0.8.5: System health dashboard
app.include_router(alert_stream.router)  # v1.2.0: Real-time alert stream (replaces Wazuh)


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
    return {"status": "ok", "version": "0.8.0", "auth": "enabled"}


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
