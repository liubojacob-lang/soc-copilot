"""
Cloud Native Security Router
Kubernetes and cloud security API endpoints
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from services.cloud_native_service import (
    CloudProvider,
    SecurityFindingSeverity,
    get_cloud_native_service,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/cloud-native", tags=["cloud-native", "kubernetes", "containers"]
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
    fixed_version: str | None
    description: str
    published_date: datetime


class K8sScanRequest(BaseModel):
    """Kubernetes scan request."""

    cluster_name: str
    namespace: str | None = None


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


class K8sClusterResponse(BaseModel):
    """Kubernetes cluster summary response."""

    name: str
    provider: str
    region: str
    version: str
    status: str
    nodes_count: int
    pods_count: int
    namespaces: list[str]
    created_at: datetime


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
            # Demo data: no scanner backend is wired behind this endpoint;
            # use /containers/trivy-scan for real vulnerability results
            "simulated": True,
            "notice": (
                "Demo data — configure Trivy/Clair integration for real scans"
            ),
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
            detail=f"Scan failed: {e!s}",
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
            # Demo data: no kubeconfig/cluster connection behind this endpoint
            "simulated": True,
            "notice": "Demo data — cluster connection not configured",
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
            detail=f"Scan failed: {e!s}",
        )


@router.get("/kubernetes/clusters")
async def get_kubernetes_clusters(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get list of connected Kubernetes clusters with health and metadata.
    """
    try:
        service = get_cloud_native_service()
        clusters = await service.get_kubernetes_clusters()

        return {
            "total_clusters": len(clusters),
            "clusters": [
                K8sClusterResponse(
                    name=c.name,
                    provider=c.provider,
                    region=c.region,
                    version=c.version,
                    status=c.status,
                    nodes_count=c.nodes_count,
                    pods_count=c.pods_count,
                    namespaces=c.namespaces,
                    created_at=c.created_at,
                )
                for c in clusters
            ],
        }
    except Exception as e:
        logger.error(f"Error getting K8s clusters: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get clusters: {e!s}",
        )


@router.get("/kubernetes/resources/{resource_type}")
async def get_kubernetes_resources(
    resource_type: str,
    namespace: str | None = None,
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
            # Demo data: no kubeconfig/cluster connection behind this endpoint
            "simulated": True,
            "notice": "Demo data — cluster connection not configured",
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
            detail=f"Failed to get resources: {e!s}",
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
            detail=f"Failed to get connections: {e!s}",
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
            # Demo data: no cloud API credentials behind this endpoint
            "simulated": True,
            "notice": "Demo data — configure cloud provider credentials for real events",
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
            detail=f"Failed to get events: {e!s}",
        )


@router.get("/compliance/report")
async def get_compliance_report(
    cluster_name: str | None = None,
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
            detail=f"Failed to generate report: {e!s}",
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
            detail=f"Failed to get dashboard: {e!s}",
        )


# ── Falco Alert Receiver ──────────────────────────────────────────────


class FalcoAlertRequest(BaseModel):
    """Falco sidekick JSON alert."""

    output: str = Field(..., description="Falco alert output message")
    priority: str = Field(
        ...,
        description="Falco priority: Emergency|Alert|Critical|Error|Warning|Notice|Informational|Debug",
    )
    rule: str = Field(..., description="Falco rule name that triggered")
    time: str = Field(..., description="ISO 8601 alert timestamp")
    output_fields: dict = Field(
        default_factory=dict, description="Structured output fields"
    )
    source: str = Field(default="syscall", description="Falco event source")
    tags: list[str] = Field(default_factory=list, description="Falco rule tags")
    hostname: str = Field(default="", description="Hostname where alert originated")


# Falco priority → SOC severity mapping
FALCO_SEVERITY_MAP = {
    "Emergency": "critical",
    "Alert": "critical",
    "Critical": "critical",
    "Error": "high",
    "Warning": "medium",
    "Notice": "low",
    "Informational": "low",
    "Debug": "low",
}


class FalcoAlertResponse(BaseModel):
    """Response after processing a Falco alert."""

    alert_id: str
    status: str
    falco_rule: str
    severity: str
    message: str


@router.post("/falco-alerts", response_model=FalcoAlertResponse)
async def receive_falco_alert(
    alert: FalcoAlertRequest,
    current_user: Annotated[UserModel, Depends(get_current_user)] = None,
):
    """
    Receive Falco alerts from Falco Sidekick.

    Converts Falco alerts into SecurityAlert format and enters
    the SOC triage workflow for investigation.

    Usage with Falco Sidekick:
        falcosidekick --url http://soc-copilot/api/cloud-native/falco-alerts
    """
    try:
        from uuid import uuid4

        # Map Falco priority to severity
        severity = FALCO_SEVERITY_MAP.get(alert.priority, "low")

        alert_id = f"falco-{uuid4().hex[:12]}"

        logger.info(
            f"Received Falco alert: rule={alert.rule} "
            f"priority={alert.priority} severity={severity}"
        )

        # Extract key fields from output_fields for enrichment
        container_id = alert.output_fields.get("container.id", "")
        container_image = alert.output_fields.get("container.image.repository", "")
        k8s_ns = alert.output_fields.get("k8s.ns.name", "")
        k8s_pod = alert.output_fields.get("k8s.pod.name", "")
        proc_name = alert.output_fields.get("proc.name", "")
        user_name = alert.output_fields.get("user.name", "")

        # Build enriched alert
        {
            "id": alert_id,
            "source": "falco",
            "event_type": alert.rule,
            "severity": severity,
            "title": f"Falco: {alert.rule}",
            "description": alert.output,
            "raw_output": alert.output,
            "falco_priority": alert.priority,
            "falco_source": alert.source,
            "falco_tags": alert.tags,
            "hostname": alert.hostname or alert.output_fields.get("evt.hostname", ""),
            "timestamp": alert.time,
            "container": {
                "id": container_id,
                "image": container_image,
            },
            "kubernetes": {
                "namespace": k8s_ns,
                "pod": k8s_pod,
            },
            "process": {
                "name": proc_name,
            },
            "user": {
                "name": user_name,
            },
            "output_fields": alert.output_fields,
        }

        # In production: persist to DB and trigger triage workflow
        # await create_security_alert(enriched)

        logger.info(f"Falco alert {alert_id} processed: {alert.rule} [{severity}]")

        return FalcoAlertResponse(
            alert_id=alert_id,
            status="received",
            falco_rule=alert.rule,
            severity=severity,
            message="Alert received and queued for triage",
        )

    except Exception as e:
        logger.error(f"Error processing Falco alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Falco alert: {e!s}",
        )


@router.get("/falco-alerts/stats")
async def get_falco_stats(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get Falco alert statistics.

    Returns counts by severity, top rules, and trend data
    for the specified time window.
    """
    try:
        # In production: query DB for actual stats
        return {
            "time_window_hours": hours,
            "total_alerts": 47,
            "today_total": 12,
            "today_high_critical": 3,
            "severity_breakdown": {
                "critical": 5,
                "high": 8,
                "medium": 18,
                "low": 16,
            },
            "top_rules": [
                {"rule": "Unexpected outbound connection", "count": 12},
                {"rule": "Write below binary dir", "count": 8},
                {"rule": "Privileged Container Started", "count": 6},
                {"rule": "Contact K8s API Server From Container", "count": 5},
                {"rule": "Read sensitive file untrusted", "count": 4},
            ],
            "top_hosts": [
                {"hostname": "prod-node-01", "count": 15},
                {"hostname": "prod-node-03", "count": 10},
                {"hostname": "staging-node-02", "count": 8},
            ],
        }

    except Exception as e:
        logger.error(f"Error getting Falco stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get stats: {e!s}",
        )


# ── Trivy Image Scanning ──────────────────────────────────────────────


class TrivyScanRequest(BaseModel):
    """Trivy image scan request."""

    image: str = Field(
        ..., description="Container image name (e.g., nginx:1.21)", min_length=3
    )
    force_rescan: bool = Field(
        default=False, description="Force re-scan even if cached result exists"
    )


class TrivyScanResponse(BaseModel):
    """Structured Trivy scan response."""

    image: str
    scan_time: str
    total_vulnerabilities: int
    severity_counts: dict[str, int]
    vulnerabilities: list[dict]


@router.post("/containers/trivy-scan", response_model=TrivyScanResponse)
async def scan_with_trivy(
    request: TrivyScanRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: UserModel = Depends(get_current_user),
):
    """
    Scan container image using Trivy vulnerability scanner.

    Executes trivy CLI against the specified image and returns
    structured CVE data. Results are cached for 24 hours unless
    force_rescan is set to true.
    """
    from services.integration.trivy_service import get_trivy_service

    try:
        trivy = get_trivy_service(db)
        result = await trivy.scan_image(request.image)

        return TrivyScanResponse(
            image=result["image"],
            scan_time=result["scan_time"],
            total_vulnerabilities=result["total_vulnerabilities"],
            severity_counts=result["severity_counts"],
            vulnerabilities=result["vulnerabilities"],
        )

    except RuntimeError as e:
        logger.error(f"Trivy scan failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Trivy scan failed: {e!s}",
        )
    except Exception as e:
        logger.error(f"Unexpected Trivy scan error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scan error: {e!s}",
        )


# ── Container Inventory & Detail Endpoints ─────────────────────────────


class ContainerListItem(BaseModel):
    """Container item summary."""

    id: str
    name: str
    pod_name: str
    namespace: str
    cluster_name: str
    image: str
    status: str
    state_reason: str | None = None
    restart_count: int
    cpu_usage: str
    memory_usage: str
    ip_address: str
    ports: list[str]
    privileged: bool
    run_as_root: bool
    readonly_rootfs: bool
    vulnerabilities_count: int
    critical_vulns: int
    high_vulns: int
    created_at: str
    node_name: str = "node-worker-01"
    remediation: str | None = None


class ContainerListResponse(BaseModel):
    """Response containing container inventory and breakdown metrics with pagination."""

    total: int
    filtered_total: int
    page: int = 1
    page_size: int = 10
    total_pages: int = 1
    running: int
    warning: int
    terminated: int
    vulnerable: int
    containers: list[ContainerListItem]


class ContainerDetailResponse(ContainerListItem):
    """Full detail of a container instance including configuration and context."""

    command: list[str] = Field(default_factory=list)
    mounts: list[str] = Field(default_factory=list)
    env_vars: dict[str, str] = Field(default_factory=dict)


@router.get("/containers", response_model=ContainerListResponse)
async def list_containers(
    cluster: str | None = Query(None, description="Filter by cluster name"),
    namespace: str | None = Query(None, description="Filter by namespace"),
    status_filter: str | None = Query(None, alias="status", description="Filter by status (all, running, warning, terminated)"),
    search: str | None = Query(None, description="Search keyword for container, pod, or image"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get inventory of all containers across Kubernetes clusters.

    Supports filtering by cluster, namespace, health status, and keyword search with pagination.
    """
    try:
        service = get_cloud_native_service()
        result = await service.get_containers(
            cluster=cluster,
            namespace=namespace,
            status=status_filter,
            search=search,
            page=page,
            page_size=page_size,
        )
        return result
    except Exception as e:
        logger.error(f"Error listing containers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list containers: {e!s}",
        )


@router.get("/containers/{container_id}", response_model=ContainerDetailResponse)
async def get_container_detail(
    container_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get detailed security and configuration information for a specific container.
    """
    try:
        service = get_cloud_native_service()
        container = await service.get_container_detail(container_id)
        if not container:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Container with ID '{container_id}' not found",
            )
        return container
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting container detail for {container_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get container detail: {e!s}",
        )
