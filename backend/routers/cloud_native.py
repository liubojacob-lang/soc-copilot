"""
Cloud Native Security Router
Kubernetes and cloud security API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime

from core.logger import get_logger
from dependencies.auth import get_current_user
from models.user import UserModel, UserRole
from services.cloud_native_service import (
    get_cloud_native_service,
    CloudProvider,
    SecurityFindingSeverity,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/cloud-native", tags=["cloud-native", "kubernetes", "containers"]
)


# Request/Response Models
class ContainerScanRequest(BaseModel):
    """Container scan request."""

    image: str = Field(..., description="Container image name")
    tag: str = Field(default="latest", description="Image tag")


class VulnerabilityResponse(BaseModel):
    """Vulnerability response."""

    image: str
    image_tag: str
    cve_id: str
    severity: str
    package_name: str
    fixed_version: Optional[str]
    description: str
    published_date: datetime


class K8sScanRequest(BaseModel):
    """Kubernetes scan request."""

    cluster_name: str
    namespace: Optional[str] = None


class K8sFindingResponse(BaseModel):
    """Kubernetes security finding."""

    id: str
    resource_name: str
    namespace: str
    kind: str
    severity: str
    category: str
    title: str
    description: str
    remediation: str
    detected_at: datetime


@router.post("/containers/scan")
async def scan_container_image(
    request: ContainerScanRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Scan container image for vulnerabilities.

    Integrates with vulnerability scanners (Trivy, Clair) to detect CVEs
    in container images.
    """
    try:
        service = get_cloud_native_service()

        vulnerabilities = await service.scan_container_image(
            image=request.image, image_tag=request.tag
        )

        return {
            "image": f"{request.image}:{request.tag}",
            "scan_time": datetime.now().isoformat(),
            "total_vulnerabilities": len(vulnerabilities),
            "severity_breakdown": {
                "critical": len(
                    [v for v in vulnerabilities if v.severity == "critical"]
                ),
                "high": len([v for v in vulnerabilities if v.severity == "high"]),
                "medium": len([v for v in vulnerabilities if v.severity == "medium"]),
                "low": len([v for v in vulnerabilities if v.severity == "low"]),
            },
            "vulnerabilities": [
                VulnerabilityResponse(
                    image=v.image,
                    image_tag=v.image_tag,
                    cve_id=v.cve_id,
                    severity=v.severity,
                    package_name=v.package_name,
                    fixed_version=v.fixed_version,
                    description=v.description,
                    published_date=v.published_date,
                )
                for v in vulnerabilities
            ],
        }

    except Exception as e:
        logger.error(f"Error scanning container: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}",
        )


@router.post("/kubernetes/scan")
async def scan_kubernetes_cluster(
    request: K8sScanRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Scan Kubernetes cluster for security issues.

    Checks for:
    - CIS Kubernetes Benchmark violations
    - Missing security policies
    - Misconfigured resources
    - Network policy gaps
    """
    try:
        service = get_cloud_native_service()

        findings = await service.scan_kubernetes_cluster(
            cluster_name=request.cluster_name, namespace=request.namespace
        )

        return {
            "cluster": request.cluster_name,
            "namespace": request.namespace,
            "scan_time": datetime.now().isoformat(),
            "total_findings": len(findings),
            "severity_breakdown": {
                "critical": len(
                    [
                        f
                        for f in findings
                        if f.severity == SecurityFindingSeverity.CRITICAL
                    ]
                ),
                "high": len(
                    [f for f in findings if f.severity == SecurityFindingSeverity.HIGH]
                ),
                "medium": len(
                    [
                        f
                        for f in findings
                        if f.severity == SecurityFindingSeverity.MEDIUM
                    ]
                ),
                "low": len(
                    [f for f in findings if f.severity == SecurityFindingSeverity.LOW]
                ),
            },
            "findings": [
                K8sFindingResponse(
                    id=f.id,
                    resource_name=f.resource.name,
                    namespace=f.resource.namespace,
                    kind=f.resource.kind,
                    severity=f.severity.value,
                    category=f.category,
                    title=f.title,
                    description=f.description,
                    remediation=f.remediation,
                    detected_at=f.detected_at,
                )
                for f in findings
            ],
        }

    except Exception as e:
        logger.error(f"Error scanning K8s cluster: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan failed: {str(e)}",
        )


@router.get("/kubernetes/resources/{resource_type}")
async def get_kubernetes_resources(
    resource_type: str,
    namespace: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get Kubernetes resources.

    Resource types: pods, deployments, services, configmaps, secrets
    """
    try:
        service = get_cloud_native_service()

        resources = await service.get_kubernetes_resources(
            resource_type=resource_type, namespace=namespace
        )

        return {
            "resource_type": resource_type,
            "namespace": namespace,
            "count": len(resources),
            "resources": [
                {
                    "name": r.name,
                    "namespace": r.namespace,
                    "kind": r.kind,
                    "labels": r.labels,
                    "status": r.status,
                }
                for r in resources
            ],
        }

    except Exception as e:
        logger.error(f"Error getting K8s resources: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resources: {str(e)}",
        )


@router.get("/cloud/connections")
async def get_cloud_connections(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get connected cloud providers.

    Returns list of cloud providers that have been configured.
    """
    try:
        service = get_cloud_native_service()
        connections = await service.get_connected_clouds()

        return {"connections": connections, "total_connected": len(connections)}

    except Exception as e:
        logger.error(f"Error getting cloud connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get connections: {str(e)}",
        )


@router.get("/cloud/events/{provider}")
async def get_cloud_security_events(
    provider: str,
    hours: int = Query(default=24, ge=1, le=168),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get cloud security events (CloudTrail, Activity Logs).

    Providers: aws, azure, gcp, alicloud
    """
    try:
        service = get_cloud_native_service()

        try:
            provider_enum = CloudProvider(provider)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider: {provider}",
            )

        events = await service.collect_cloud_trails(provider=provider_enum, hours=hours)

        return {
            "provider": provider,
            "time_range_hours": hours,
            "total_events": len(events),
            "events": [
                {
                    "event_id": e.event_id,
                    "service": e.service,
                    "event_type": e.event_type,
                    "severity": e.severity.value,
                    "resource_id": e.resource_id,
                    "description": e.description,
                    "timestamp": e.timestamp,
                }
                for e in events
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cloud events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get events: {str(e)}",
        )


@router.get("/compliance/report")
async def get_compliance_report(
    cluster_name: Optional[str] = None,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Generate security compliance report.

    Includes CIS Kubernetes Benchmark results and security findings.
    """
    try:
        service = get_cloud_native_service()

        report = await service.get_security_compliance_report(cluster_name=cluster_name)

        return report

    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )


@router.get("/dashboard")
async def get_cloud_native_dashboard(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get cloud native security dashboard.

    Overview of container and Kubernetes security status.
    """
    try:
        service = get_cloud_native_service()

        # Get connections
        connections = await service.get_connected_clouds()

        # Get summary stats
        # In production, query actual data
        return {
            "overview": {
                "connected_clusters": 2,
                "connected_clouds": len(connections),
                "total_containers": 45,
                "vulnerable_images": 8,
            },
            "security_summary": {
                "critical_findings": 3,
                "high_findings": 12,
                "medium_findings": 28,
                "low_findings": 45,
            },
            "compliance": {
                "cis_benchmark": 85.0,  # percentage
                "last_scan": datetime.now().isoformat(),
            },
            "recent_vulnerabilities": [
                {"image": "nginx:1.21", "cve": "CVE-2023-1234", "severity": "high"}
            ],
            "connections": connections,
        }

    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}",
        )
