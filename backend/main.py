"""SOC Copilot API - Main application entry point.

Refactored with lifecycle management for cleaner startup/shutdown.
"""

import sys
from pathlib import Path

# Add backend directory to Python path
backend_dir = Path(__file__).parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.config import settings
from core.logger import get_logger
from db.session import AsyncSessionLocal
from middleware import (
    AuditMiddleware,
    ExceptionCaptureMiddleware,
    ObservabilityMiddleware,
    RequestContextMiddleware,
    ResourceAuthorizationMiddleware,
    TraceIDMiddleware,
    setup_exception_handlers,
    setup_trace_logging,
)
from middleware.csrf_middleware import setup_csrf_middleware
from middleware.performance import PerformanceMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from middleware.tenant_middleware import TenantMiddleware
from observability.logging import setup_json_logging
from observability.tracing import setup_tracing
from routers import (
    admin_settings,
    ai,
    ai_models,
    ai_tasks,
    alert,
    alert_enrichment,
    alert_stream,
    alerts_to_loki,
    api_keys,
    assets,
    audit,
    auth,
    blocked_ips,
    cases,
    cloud_native,
    correlation,
    dashboard,
    export,
    health,
    history,
    ioc_hits,
    marketplace,
    monitor,
    monitoring_alerts,
    notifications,
    playbook,
    playbook_definitions,
    prompt_registry,
    report,
    secrets,
    security_alerts,
    security_vulnerabilities,
    siem,
    system_dashboard,
    threat_hunting,
    threat_intel,
    timeline,
    triggers,
    ueba,
    users,
    webhooks,
    websocket_filters,
)
from routers import websocket as ws_router
from routers.playbook import internal as playbook_internal

setup_json_logging(settings.log_level)
logger = get_logger(__name__)


class AddCredentialsMiddleware(BaseHTTPMiddleware):
    """Add credentials header for specific origins."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        origin = request.headers.get("origin", "")
        if "localhost" in origin or "127.0.0.1" in origin:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        return response


async def create_bootstrap_admin():
    """Create bootstrap admin user if no users exist."""
    from core.security import get_password_hash
    from models.user import UserRole
    from repositories.user_repository import UserRepository

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
                must_change_password=True,
            )

            logger.info(f"Bootstrap admin created with ID: {admin_user.id}")
            logger.warning("Bootstrap admin must change password on first login!")

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

    alembic_dir = Path(__file__).parent / "migrations_alembic"
    ini_path = Path(__file__).parent / "alembic.ini"

    if alembic_dir.exists() and ini_path.exists():
        try:
            config = Config(str(ini_path))
            config.set_main_option("script_location", str(alembic_dir))
            import logging

            logging.getLogger("alembic").setLevel(logging.WARNING)
            import asyncio
            import subprocess
            import sys

            # Run migrations in thread pool to avoid blocking event loop
            def run_migrations_sync():
                return subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "alembic",
                        "-c",
                        str(ini_path),
                        "upgrade",
                        "head",
                    ],
                    capture_output=True,
                    text=True,
                    cwd=str(Path(__file__).parent),
                )

            try:
                from services.migration_lock import migration_process_lock
            except ImportError:  # pragma: no cover - Windows dev only
                migration_process_lock = None

            def run_migrations_locked():
                if migration_process_lock is None:
                    return run_migrations_sync()
                with migration_process_lock():
                    return run_migrations_sync()

            result = await asyncio.to_thread(run_migrations_locked)
            if result.returncode == 0:
                logger.info("Database migrations completed")
            else:
                detail = result.stderr or result.stdout
                if settings.environment == "production":
                    raise RuntimeError(f"Database migration failed: {detail}")
                logger.warning(f"Migration output: {detail}")
        except Exception as e:
            if settings.environment == "production":
                # Fail fast: running with an unverified schema in production is worse
                # than a crashed container (restart policy will retry after fix).
                raise
            logger.warning(f"Migration failed (might be ok if already applied): {e}")


def register_lifecycle_services():
    """Register all lifecycle services with the manager.

    Services are registered in order of priority:
    1. CRITICAL: Database
    2. ESSENTIAL: Queue Manager, Cron Scheduler, Rate Limiter
    3. NORMAL: AI Task Processor, Alert Pipeline, WebSocket Monitoring, Alert Evaluator
    4. OPTIONAL: Audit Archive
    """
    from services.lifecycle import (
        AITaskProcessorService,
        AlertEvaluatorService,
        AlertPipelineService,
        AuditArchiveService,
        CronSchedulerServiceWrapper,
        DatabaseService,
        DataRetentionService,
        QueueManagerService,
        RateLimiterService,
        WebSocketMonitoringService,
        get_lifecycle_manager,
    )

    manager = get_lifecycle_manager()

    # CRITICAL priority
    manager.register(DatabaseService())

    # ESSENTIAL priority
    manager.register(QueueManagerService())
    manager.register(CronSchedulerServiceWrapper())
    manager.register(RateLimiterService())

    # NORMAL priority
    manager.register(AITaskProcessorService())
    manager.register(AlertPipelineService())
    manager.register(WebSocketMonitoringService())
    manager.register(AlertEvaluatorService())

    # OPTIONAL priority
    if settings.audit_log_cleanup_enabled:
        manager.register(AuditArchiveService())
    if settings.data_retention_enabled:
        manager.register(DataRetentionService())

    return manager


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """Application lifespan manager using lifecycle services.

    This refactored version uses the LifecycleManager for cleaner
    startup and shutdown of all services.
    """
    # Startup
    logger.info("Initializing SOC Copilot API v0.9.0")
    logger.info(f"Environment: {settings.environment}")
    logger.info("Playbook Engine: ENABLED (DAG-based with Node Plugin System)")
    logger.info("Trigger System: ENABLED (webhook + cron)")
    logger.info(f"Run Queue: ENABLED (max_concurrent={settings.run_queue_max})")
    logger.info("Secrets Management: ENABLED (Fernet encryption)")
    logger.info(
        f"External TI: {'ENABLED' if settings.allow_external_ti else 'DISABLED'}"
    )
    logger.info("Authentication: ENABLED")
    logger.info("RBAC: ENABLED (admin, analyst, auditor)")
    logger.info("Audit Logging: ENABLED")

    # Production security checks
    from core.security_validators import run_production_security_checks

    security_errors = run_production_security_checks()
    if security_errors:
        msg = "Production security validation failed: " + "; ".join(security_errors)
        if settings.enforce_strict_checks:
            logger.critical(msg)
            raise RuntimeError(msg)
        logger.critical(
            msg
            + " (startup allowed; set STRICT_PRODUCTION_CHECKS=true or ENVIRONMENT=production to fail)"
        )

    # Run migrations
    await run_migrations()

    # Validate security environment variables
    from middleware.env_validator import validate_cors_origins, validate_security_env

    validate_security_env()
    validate_cors_origins()

    # Register and start all lifecycle services
    manager = register_lifecycle_services()
    started_services = await manager.start_all()
    logger.info(f"Started {len(started_services)} lifecycle services")

    # Create bootstrap admin
    await create_bootstrap_admin()

    # Load node plugins
    from pathlib import Path

    from playbook_engine.v7_dag.registry import NodeRegistry

    node_registry = NodeRegistry()
    plugin_dir = Path(__file__).parent / "playbook_engine" / "v7_dag" / "plugins"
    plugin_count = node_registry.auto_load_plugins(plugin_dir)
    logger.info(f"Loaded {plugin_count} node plugins")

    # Start background cleanup task for WebSocket known_users
    import asyncio

    from services.websocket_manager import get_manager

    cleanup_task = None

    async def websocket_cleanup_task():
        """Periodically clean up stale WebSocket users."""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                manager = get_manager()
                cleaned = await manager.cleanup_stale_users()
                if cleaned > 0:
                    logger.info(f"Cleaned up {cleaned} stale WebSocket users")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket cleanup task error: {e}")

    cleanup_task = asyncio.create_task(websocket_cleanup_task())
    logger.info("Started WebSocket user cleanup background task")

    yield

    # Shutdown
    logger.info("Shutting down SOC Copilot API")
    if cleanup_task:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
    await manager.stop_all()
    logger.info("Shutdown complete")


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
    _cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
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

# v1.0: Runtime assertion - reject allow_credentials=True with wildcard origins
if "*" in _cors_origins:
    # In development, warn but allow. In production, this is already blocked above.
    if settings.environment != "production":
        logger.warning(
            "CORS: allow_credentials=True with wildcard origins in development. "
            "This is insecure - do not use in production. "
            "Set explicit CORS_ORIGINS instead."
        )
    else:
        raise RuntimeError(
            "CORS: allow_credentials=True requires explicit origins, not wildcard. "
            "Set CORS_ORIGINS to comma-separated explicit URLs."
        )

# Add credentials header for localhost origins
app.add_middleware(AddCredentialsMiddleware)

# Security headers middleware (adds CSP, X-Frame-Options, HSTS, etc.)
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=settings.environment == "production",
)

# P1: Gzip compression middleware - REMOVED due to compatibility issues
# Use uvicorn's built-in gzip or nginx gzip compression instead

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


# ============================================================================
# v1.1: legacy /api/* alias → /api/v1/* (rewritten in-place, no redirect)
# ============================================================================


@app.middleware("http")
async def api_version_alias(request: Request, call_next):
    """Alias legacy /api/* paths onto /api/v1/* by rewriting the path in place.

    The whole frontend client uses legacy /api/* paths. A 308 redirect here
    would bounce browsers to an absolute URL built from the Host header —
    cross-origin in dev, where CSP connect-src 'self' blocks it (and even in
    prod it costs an extra roundtrip). Rewriting scope["path"] routes the
    request to the v1 endpoint with zero client-visible changes.
    """
    path = request.url.path
    if path.startswith("/api/") and not path.startswith("/api/v1/"):
        new_path = path.replace("/api/", "/api/v1/", 1)
        request.scope["path"] = new_path
        request.scope["raw_path"] = new_path.encode()
    return await call_next(request)


# Setup CSRF protection (must be before exception handlers in request chain)
setup_csrf_middleware(
    app,
    exempt_paths={
        "/api/triggers/webhook",  # Webhook endpoints have their own validation
        "/api/playbook-definitions/runs",  # API can be called via API key
    },
)

# Setup trace logging
setup_trace_logging()


# Include routers - health first (no auth required), then auth, then others
app.include_router(health.router)  # v0.8.2: Enhanced health check and metrics
app.include_router(correlation.router)  # v0.8.0: Event correlation engine
app.include_router(blocked_ips.router)  # IP/Domain blocking for threat response
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
app.include_router(playbook_internal.router)
app.include_router(webhooks.router)
app.include_router(triggers.router)
app.include_router(secrets.router)  # v0.7.4: Secrets management
app.include_router(admin_settings.router)  # System settings
app.include_router(ai.router)  # Phase 2: AI Copilot service
app.include_router(prompt_registry.router)  # P1-23: Prompt Registry
app.include_router(ai_tasks.router)  # v0.7.7: AI background task queue
app.include_router(ueba.router)  # Phase 3: UEBA analytics
app.include_router(threat_hunting.router)  # Phase 3: Threat hunting
app.include_router(marketplace.router)  # Phase 4: Playbook marketplace
app.include_router(cloud_native.router)  # Phase 4: Cloud native security
app.include_router(monitor.router)  # Real-time monitoring dashboard
app.include_router(security_alerts.router)  # v0.9.0: External security alert ingestion
app.include_router(alert_enrichment.router)  # v0.9.0: Threat intelligence enrichment
app.include_router(
    notifications.router
)  # v0.9.x: Notification channels and queue status
from routers import alerts_lifecycle  # v0.9.0: Alert lifecycle management

app.include_router(alerts_lifecycle.router)  # v0.9.0: Alert lifecycle management
app.include_router(ws_router.router)  # v0.8.5: WebSocket real-time alerts
app.include_router(websocket_filters.router)  # v0.9.0: WebSocket filter management
app.include_router(monitoring_alerts.router)  # v0.9.1: Monitoring alert rules
app.include_router(export.router)  # v0.8.5: Data export functionality
app.include_router(system_dashboard.router)  # v0.8.5: System health dashboard
app.include_router(
    security_vulnerabilities.router
)  # v0.9.2: Security vulnerability management
app.include_router(alert_stream.router)  # v0.9.0: Wazuh alert stream management
app.include_router(alerts_to_loki.router)  # v0.9.0: Send alerts to Loki
app.include_router(cases.router)  # v0.10.0: Case management
app.include_router(dashboard.router)  # v0.10.0: Operational dashboard
app.include_router(siem.router)  # v1.1: SIEM log storage and search


# Global OPTIONS handler for CORS preflight
@app.options("/{path:path}")
async def options_handler(path: str, request: Request):
    """Handle OPTIONS preflight requests for CORS.

    SECURITY: Validate origin against whitelist to prevent unauthorized cross-origin access.
    """
    origin = request.headers.get("origin", "")

    # Security: Validate origin against whitelist
    if origin:
        # Check if origin is in allowed list
        # cors_origins is a comma-separated string; split before matching or
        # `origin in allowed_origins` degrades into substring matching
        raw_origins = getattr(settings, "cors_origins", "") or ""
        allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        # Handle wildcard and specific origins
        is_allowed = "*" in allowed_origins or origin in allowed_origins

        # In production, reject unknown origins
        if not is_allowed and settings.environment == "production":
            return Response(
                status_code=403,
                headers={"Content-Type": "text/plain"},
                content="Origin not allowed",
            )

        # In development, allow localhost variants
        if not is_allowed and settings.environment == "development":
            if not (
                origin.startswith("http://localhost")
                or origin.startswith("http://127.0.0.1")
            ):
                return Response(
                    status_code=403,
                    headers={"Content-Type": "text/plain"},
                    content="Origin not allowed in development mode",
                )

    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": origin or "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-CSRF-Token, X-API-Key",
            "Access-Control-Allow-Credentials": "true" if origin else "false",
            "Access-Control-Max-Age": "600",
        },
    )


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "SOC Copilot API v1.1", "auth": "enabled"}


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "1.1.0", "auth": "enabled"}


if __name__ == "__main__":
    import uvicorn

    # Increase timeout for long AI analysis requests (120 seconds)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # nosec B104 - container entrypoint, port published by compose
        port=8000,
        reload=True,
        timeout_keep_alive=120,
        timeout_graceful_shutdown=30,
    )
