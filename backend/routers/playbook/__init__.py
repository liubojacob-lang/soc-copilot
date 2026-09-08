"""Playbook router package.

This package contains the split playbook router modules:
- queries: Query and action generation endpoints
- runs: Playbook run execution endpoints
- definitions: DAG-based playbook definition endpoints
- approvals: Approval workflow endpoints
- versions: Version management, replay, and import/export endpoints
"""

from fastapi import APIRouter

from .approvals import router as approvals_router
from .definitions import router as definitions_router
from .queries import router as queries_router
from .runs import router as runs_router
from .versions import router as versions_router

# Create main router that includes all sub-routers
router = APIRouter(prefix="/api/v1/playbook", tags=["playbook"])

# Include all sub-routers
router.include_router(queries_router)
router.include_router(runs_router)
router.include_router(definitions_router)
router.include_router(approvals_router)
router.include_router(versions_router)
