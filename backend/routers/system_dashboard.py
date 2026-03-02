"""System health dashboard for SOC Copilot.

Provides comprehensive system monitoring including:
- Database connection pool status
- Redis connection pool status
- AI model availability
- Disk space and memory usage
- System statistics
"""

import os
import time
import shutil
import platform
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import AsyncSessionLocal, engine
from core.config import settings
from core.logger import get_logger
from core.token_blacklist import get_token_blacklist, REDIS_AVAILABLE
from dependencies.auth import get_current_user
from models.user import UserModel

logger = get_logger(__name__)

router = APIRouter(prefix="/api/system", tags=["System Dashboard"])


# ==================== Models ====================

class PoolStatus(BaseModel):
    """Connection pool status."""
    size: int
    checked_in: int
    checked_out: int
    overflow: int
    invalid: int


class DatabaseStatus(BaseModel):
    """Database status model."""
    status: str
    latency_ms: float
    pool: Optional[PoolStatus] = None
    version: Optional[str] = None
    database_size: Optional[str] = None
    active_connections: Optional[int] = None


class RedisStatus(BaseModel):
    """Redis status model."""
    status: str
    latency_ms: Optional[float] = None
    version: Optional[str] = None
    connected_clients: Optional[int] = None
    used_memory: Optional[str] = None
    uptime_seconds: Optional[int] = None
    pool_connections: Optional[int] = None


class AIModelStatus(BaseModel):
    """AI model status model."""
    id: str
    name: str
    provider: str
    is_active: bool
    last_used: Optional[str] = None
    total_requests: int = 0


class DiskUsage(BaseModel):
    """Disk usage model."""
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float


class MemoryUsage(BaseModel):
    """Memory usage model."""
    total_gb: float
    available_gb: float
    used_gb: float
    percent_used: float


class SystemStats(BaseModel):
    """System statistics model."""
    cpu_percent: float
    memory: MemoryUsage
    disk: DiskUsage
    uptime_seconds: float
    platform: str
    python_version: str


class SystemDashboard(BaseModel):
    """Full system dashboard model."""
    timestamp: str
    version: str
    environment: str
    database: DatabaseStatus
    redis: RedisStatus
    ai_models: List[AIModelStatus]
    system: SystemStats
    features: Dict[str, bool]


# ==================== Helper Functions ====================

def get_database_pool_status() -> Optional[PoolStatus]:
    """Get SQLAlchemy connection pool status."""
    try:
        pool = engine.pool
        return PoolStatus(
            size=pool.size(),
            checked_in=pool.checkedin(),
            checked_out=pool.checkedout(),
            overflow=pool.overflow(),
            invalid=pool.invalidatedcount(),
        )
    except Exception as e:
        logger.warning(f"Failed to get pool status: {e}")
        return None


async def get_database_size(session: AsyncSession) -> Optional[str]:
    """Get database size (SQLite only)."""
    try:
        # For SQLite
        if "sqlite" in str(engine.url):
            db_path = str(engine.url).replace("sqlite:///", "")
            if os.path.exists(db_path):
                size_bytes = os.path.getsize(db_path)
                if size_bytes < 1024:
                    return f"{size_bytes} B"
                elif size_bytes < 1024 * 1024:
                    return f"{size_bytes / 1024:.2f} KB"
                elif size_bytes < 1024 * 1024 * 1024:
                    return f"{size_bytes / (1024 * 1024):.2f} MB"
                else:
                    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
        return None
    except Exception:
        return None


def get_disk_usage() -> DiskUsage:
    """Get disk usage for the application directory."""
    try:
        total, used, free = shutil.disk_usage("/")
        total_gb = total / (1024 ** 3)
        used_gb = used / (1024 ** 3)
        free_gb = free / (1024 ** 3)
        percent_used = (used / total) * 100
        
        return DiskUsage(
            total_gb=round(total_gb, 2),
            used_gb=round(used_gb, 2),
            free_gb=round(free_gb, 2),
            percent_used=round(percent_used, 2),
        )
    except Exception as e:
        logger.warning(f"Failed to get disk usage: {e}")
        return DiskUsage(total_gb=0, used_gb=0, free_gb=0, percent_used=0)


def get_memory_usage() -> MemoryUsage:
    """Get memory usage."""
    try:
        import psutil
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        available_gb = mem.available / (1024 ** 3)
        used_gb = mem.used / (1024 ** 3)
        
        return MemoryUsage(
            total_gb=round(total_gb, 2),
            available_gb=round(available_gb, 2),
            used_gb=round(used_gb, 2),
            percent_used=round(mem.percent, 2),
        )
    except ImportError:
        # psutil not available, return placeholder
        return MemoryUsage(total_gb=0, used_gb=0, available_gb=0, percent_used=0)
    except Exception as e:
        logger.warning(f"Failed to get memory usage: {e}")
        return MemoryUsage(total_gb=0, used_gb=0, available_gb=0, percent_used=0)


def get_cpu_percent() -> float:
    """Get CPU usage percentage."""
    try:
        import psutil
        return round(psutil.cpu_percent(interval=0.1), 2)
    except ImportError:
        return 0.0
    except Exception:
        return 0.0


async def get_ai_models_status(session: AsyncSession) -> List[AIModelStatus]:
    """Get status of all AI models."""
    try:
        from sqlalchemy import select
        from models.ai_model import AIModelModel
        
        result = await session.execute(
            select(AIModelModel).order_by(AIModelModel.name)
        )
        models = result.scalars().all()
        
        return [
            AIModelStatus(
                id=str(m.id),
                name=m.name,
                provider=m.provider,
                is_active=m.is_active,
                last_used=m.last_used.isoformat() if m.last_used else None,
                total_requests=m.total_requests or 0,
            )
            for m in models
        ]
    except Exception as e:
        logger.warning(f"Failed to get AI models status: {e}")
        return []


# ==================== Endpoints ====================

@router.get("/dashboard", response_model=SystemDashboard, summary="Get full system dashboard")
async def get_system_dashboard(
    current_user: UserModel = Depends(get_current_user),
):
    """Get comprehensive system health dashboard.
    
    **Requires:** Authenticated user (admin recommended)
    
    **Returns:**
    - Database status with connection pool info
    - Redis status with memory usage
    - AI models availability
    - System resources (CPU, memory, disk)
    - Feature flags status
    """
    start_time = time.time()
    
    # Check database
    db_status = "ok"
    db_latency = 0.0
    db_version = None
    db_size = None
    
    try:
        db_start = time.time()
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT sqlite_version()"))
            row = result.fetchone()
            if row:
                db_version = row[0]
            db_size = await get_database_size(session)
        db_latency = (time.time() - db_start) * 1000
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        db_status = "error"
    
    database_status = DatabaseStatus(
        status=db_status,
        latency_ms=round(db_latency, 2),
        pool=get_database_pool_status(),
        version=db_version,
        database_size=db_size,
    )
    
    # Check Redis
    redis_status = "disabled"
    redis_latency = None
    redis_info = {}
    
    if REDIS_AVAILABLE and settings.redis_url:
        try:
            redis_start = time.time()
            blacklist = get_token_blacklist()
            info = await blacklist.get_blacklist_info()
            redis_latency = (time.time() - redis_start) * 1000
            
            if info.get("redis_available"):
                redis_status = "ok"
                redis_info = info
            else:
                redis_status = "degraded"
        except Exception as e:
            logger.error(f"Redis check failed: {e}")
            redis_status = "error"
    
    redis_status_model = RedisStatus(
        status=redis_status,
        latency_ms=round(redis_latency, 2) if redis_latency else None,
        pool_connections=redis_info.get("pool_connections"),
    )
    
    # Get AI models
    async with AsyncSessionLocal() as session:
        ai_models = await get_ai_models_status(session)
    
    # System stats
    system_stats = SystemStats(
        cpu_percent=get_cpu_percent(),
        memory=get_memory_usage(),
        disk=get_disk_usage(),
        uptime_seconds=round(time.time() - _startup_time, 2),
        platform=platform.platform(),
        python_version=platform.python_version(),
    )
    
    # Feature flags
    features = {
        "redis_enabled": REDIS_AVAILABLE and bool(settings.redis_url),
        "ai_copilot": bool(settings.openai_api_key),
        "threat_intel": bool(settings.otx_api_key),
        "audit_archive": True,
        "websocket": True,
        "rate_limiting": True,
    }
    
    total_latency = (time.time() - start_time) * 1000
    logger.info(
        "System dashboard generated",
        extra={
            "user_id": current_user.id,
            "latency_ms": round(total_latency, 2),
        }
    )
    
    return SystemDashboard(
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.8.5",
        environment=settings.environment,
        database=database_status,
        redis=redis_status_model,
        ai_models=ai_models,
        system=system_stats,
        features=features,
    )


@router.get("/database", response_model=DatabaseStatus, summary="Get database status")
async def get_database_status(
    current_user: UserModel = Depends(get_current_user),
):
    """Get detailed database status including connection pool."""
    start_time = time.time()
    status = "ok"
    version = None
    db_size = None
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT sqlite_version()"))
            row = result.fetchone()
            if row:
                version = row[0]
            db_size = await get_database_size(session)
    except Exception as e:
        status = "error"
        logger.error(f"Database status check failed: {e}")
    
    latency = (time.time() - start_time) * 1000
    
    return DatabaseStatus(
        status=status,
        latency_ms=round(latency, 2),
        pool=get_database_pool_status(),
        version=version,
        database_size=db_size,
    )


@router.get("/redis", response_model=RedisStatus, summary="Get Redis status")
async def get_redis_status(
    current_user: UserModel = Depends(get_current_user),
):
    """Get detailed Redis status."""
    if not REDIS_AVAILABLE or not settings.redis_url:
        return RedisStatus(status="disabled")
    
    start_time = time.time()
    
    try:
        blacklist = get_token_blacklist()
        info = await blacklist.get_blacklist_info()
        latency = (time.time() - start_time) * 1000
        
        if info.get("redis_available"):
            return RedisStatus(
                status="ok",
                latency_ms=round(latency, 2),
                pool_connections=info.get("pool_connections"),
            )
        else:
            return RedisStatus(status="degraded", latency_ms=round(latency, 2))
    except Exception as e:
        logger.error(f"Redis status check failed: {e}")
        return RedisStatus(status="error")


@router.get("/resources", response_model=SystemStats, summary="Get system resources")
async def get_system_resources(
    current_user: UserModel = Depends(get_current_user),
):
    """Get system resource usage (CPU, memory, disk)."""
    return SystemStats(
        cpu_percent=get_cpu_percent(),
        memory=get_memory_usage(),
        disk=get_disk_usage(),
        uptime_seconds=round(time.time() - _startup_time, 2),
        platform=platform.platform(),
        python_version=platform.python_version(),
    )


@router.get("/features", summary="Get feature flags")
async def get_feature_flags(
    current_user: UserModel = Depends(get_current_user),
):
    """Get current feature flag status."""
    return {
        "redis_enabled": REDIS_AVAILABLE and bool(settings.redis_url),
        "ai_copilot": bool(settings.openai_api_key),
        "threat_intel": bool(settings.otx_api_key),
        "audit_archive": True,
        "websocket": True,
        "rate_limiting": True,
        "csrf_protection": True,
        "idempotency": True,
    }


# Track startup time
_startup_time = time.time()
