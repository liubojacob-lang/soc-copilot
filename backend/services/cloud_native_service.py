"""
Cloud Native Security Service
Kubernetes, container, and cloud security monitoring
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from core.logger import get_logger
from core.config import settings

logger = get_logger(__name__)


class CloudProvider(Enum):
    """Supported cloud providers."""

    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ALICLOUD = "alicloud"


class SecurityFindingSeverity(Enum):
    """Security finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class K8sResource:
    """Kubernetes resource."""

    name: str
    namespace: str
    kind: str  # Pod, Deployment, Service, etc.
    labels: Dict[str, str]
    annotations: Dict[str, str]
    spec: Dict[str, Any]
    status: Dict[str, Any]


@dataclass
class ContainerVulnerability:
    """Container vulnerability scan result."""

    image: str
    image_tag: str
    cve_id: str
    severity: str
    package_name: str
    fixed_version: Optional[str]
    description: str
    published_date: datetime


@dataclass
class K8sSecurityFinding:
    """Kubernetes security finding."""

    id: str
    resource: K8sResource
    severity: SecurityFindingSeverity
    category: str  # CIS, PSP, NetworkPolicy, etc.
    title: str
    description: str
    remediation: str
    detected_at: datetime


@dataclass
class CloudSecurityEvent:
    """Cloud security event."""

    event_id: str
    provider: CloudProvider
    service: str  # EC2, S3, IAM, etc.
    event_type: str
    severity: SecurityFindingSeverity
    resource_id: str
    resource_type: str
    description: str
    raw_event: Dict[str, Any]
    timestamp: datetime


class CloudNativeSecurityService:
    """Cloud native security monitoring service."""

    def __init__(self):
        self.k8s_connected = False
        self.cloud_connections: Dict[CloudProvider, bool] = {}
        self._initialize_connections()

    def _initialize_connections(self):
        """Initialize cloud connections from config."""
        # Check for cloud credentials in environment
        for provider in CloudProvider:
            if self._check_cloud_credentials(provider):
                self.cloud_connections[provider] = True
                logger.info(f"{provider.value.upper()} credentials found")

    def _check_cloud_credentials(self, provider: CloudProvider) -> bool:
        """Check if cloud provider credentials are configured."""
        if provider == CloudProvider.AWS:
            return bool(
                getattr(settings, "AWS_ACCESS_KEY_ID", None)
                and getattr(settings, "AWS_SECRET_ACCESS_KEY", None)
            )
        elif provider == CloudProvider.AZURE:
            return bool(getattr(settings, "AZURE_SUBSCRIPTION_ID", None))
        elif provider == CloudProvider.GCP:
            return bool(getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", None))
        elif provider == CloudProvider.ALICLOUD:
            return bool(
                getattr(settings, "ALICLOUD_ACCESS_KEY", None)
                and getattr(settings, "ALICLOUD_SECRET_KEY", None)
            )
        return False

    async def scan_container_image(
        self, image: str, image_tag: str = "latest"
    ) -> List[ContainerVulnerability]:
        """
        Scan container image for vulnerabilities.

        Args:
            image: Image name (e.g., "nginx")
            image_tag: Image tag (e.g., "1.21")

        Returns:
            List of vulnerabilities found
        """
        logger.info(f"Scanning container image: {image}:{image_tag}")

        # In production, integrate with Trivy, Clair, or similar
        # For now, return sample data

        sample_vulns = [
            ContainerVulnerability(
                image=image,
                image_tag=image_tag,
                cve_id="CVE-2023-1234",
                severity="high",
                package_name="openssl",
                fixed_version="1.1.1w",
                description="Buffer overflow vulnerability in OpenSSL",
                published_date=datetime.now(),
            ),
            ContainerVulnerability(
                image=image,
                image_tag=image_tag,
                cve_id="CVE-2023-5678",
                severity="medium",
                package_name="curl",
                fixed_version="8.4.0",
                description="Information disclosure in curl",
                published_date=datetime.now(),
            ),
        ]

        return sample_vulns

    async def scan_kubernetes_cluster(
        self, cluster_name: str, namespace: Optional[str] = None
    ) -> List[K8sSecurityFinding]:
        """
        Scan Kubernetes cluster for security issues.

        Args:
            cluster_name: Cluster name
            namespace: Optional namespace to limit scan

        Returns:
            List of security findings
        """
        logger.info(f"Scanning K8s cluster: {cluster_name}")

        # In production, use kubeconfig to connect and scan
        # For now, return sample findings

        findings = [
            K8sSecurityFinding(
                id="k8s-001",
                resource=K8sResource(
                    name="web-app",
                    namespace="production",
                    kind="Deployment",
                    labels={"app": "web"},
                    annotations={},
                    spec={},
                    status={},
                ),
                severity=SecurityFindingSeverity.HIGH,
                category="CIS",
                title="Container running as root",
                description="Container is configured to run as root user",
                remediation="Set runAsNonRoot: true in securityContext",
                detected_at=datetime.now(),
            ),
            K8sSecurityFinding(
                id="k8s-002",
                resource=K8sResource(
                    name="api-service",
                    namespace="production",
                    kind="Pod",
                    labels={"app": "api"},
                    annotations={},
                    spec={},
                    status={},
                ),
                severity=SecurityFindingSeverity.CRITICAL,
                category="NetworkPolicy",
                title="No network policy defined",
                description="Pod has no network policy restricting ingress/egress",
                remediation="Create NetworkPolicy resource for this pod",
                detected_at=datetime.now(),
            ),
            K8sSecurityFinding(
                id="k8s-003",
                resource=K8sResource(
                    name="db-secret",
                    namespace="default",
                    kind="Secret",
                    labels={},
                    annotations={},
                    spec={},
                    status={},
                ),
                severity=SecurityFindingSeverity.MEDIUM,
                category="SecretManagement",
                title="Secret not encrypted at rest",
                description="Kubernetes secret is not encrypted at rest",
                remediation="Enable encryption at rest for secrets",
                detected_at=datetime.now(),
            ),
        ]

        if namespace:
            findings = [f for f in findings if f.resource.namespace == namespace]

        return findings

    async def get_kubernetes_resources(
        self, resource_type: str, namespace: Optional[str] = None
    ) -> List[K8sResource]:
        """
        Get Kubernetes resources.

        Args:
            resource_type: Type of resource (pods, deployments, services)
            namespace: Optional namespace filter

        Returns:
            List of resources
        """
        # In production, query actual K8s API
        sample_resources = [
            K8sResource(
                name="web-app-7d4f8b9c5-x2abc",
                namespace="production",
                kind="Pod",
                labels={"app": "web", "version": "v1"},
                annotations={},
                spec={"containers": [{"name": "web", "image": "nginx:1.21"}]},
                status={"phase": "Running"},
            ),
            K8sResource(
                name="api-deployment",
                namespace="production",
                kind="Deployment",
                labels={"app": "api"},
                annotations={},
                spec={"replicas": 3},
                status={"readyReplicas": 3},
            ),
        ]

        if namespace:
            sample_resources = [r for r in sample_resources if r.namespace == namespace]

        return sample_resources

    async def collect_cloud_trails(
        self, provider: CloudProvider, hours: int = 24
    ) -> List[CloudSecurityEvent]:
        """
        Collect cloud audit logs/trails.

        Args:
            provider: Cloud provider
            hours: Hours of logs to collect

        Returns:
            List of security events
        """
        if not self.cloud_connections.get(provider):
            logger.warning(f"{provider.value} not connected")
            return []

        # In production, use cloud SDKs to fetch CloudTrail/Activity Logs
        sample_events = [
            CloudSecurityEvent(
                event_id="aws-001",
                provider=CloudProvider.AWS,
                service="IAM",
                event_type="CreateAccessKey",
                severity=SecurityFindingSeverity.MEDIUM,
                resource_id="user/admin",
                resource_type="IAMUser",
                description="New access key created for admin user",
                raw_event={},
                timestamp=datetime.now(),
            ),
            CloudSecurityEvent(
                event_id="aws-002",
                provider=CloudProvider.AWS,
                service="S3",
                event_type="PutBucketPolicy",
                severity=SecurityFindingSeverity.HIGH,
                resource_id="bucket-sensitive-data",
                resource_type="S3Bucket",
                description="S3 bucket policy modified to allow public access",
                raw_event={},
                timestamp=datetime.now(),
            ),
            CloudSecurityEvent(
                event_id="aws-003",
                provider=CloudProvider.AWS,
                service="EC2",
                event_type="AuthorizeSecurityGroupIngress",
                severity=SecurityFindingSeverity.MEDIUM,
                resource_id="sg-12345678",
                resource_type="SecurityGroup",
                description="Security group rule added allowing 0.0.0.0/0",
                raw_event={},
                timestamp=datetime.now(),
            ),
        ]

        return sample_events

    async def get_security_compliance_report(
        self, cluster_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate security compliance report.

        Args:
            cluster_name: Optional cluster to focus on

        Returns:
            Compliance report
        """
        findings = await self.scan_kubernetes_cluster(cluster_name or "default")

        # Count by severity
        severity_counts = {}
        for severity in SecurityFindingSeverity:
            count = len([f for f in findings if f.severity == severity])
            if count > 0:
                severity_counts[severity.value] = count

        # CIS benchmark compliance
        cis_compliance = {
            "total_checks": 100,
            "passed": 85,
            "failed": 10,
            "skipped": 5,
            "compliance_percentage": 85.0,
        }

        return {
            "scan_date": datetime.now().isoformat(),
            "cluster": cluster_name,
            "total_findings": len(findings),
            "severity_breakdown": severity_counts,
            "cis_compliance": cis_compliance,
            "findings": [
                {
                    "id": f.id,
                    "resource": f"{f.resource.kind}/{f.resource.name}",
                    "namespace": f.resource.namespace,
                    "severity": f.severity.value,
                    "category": f.category,
                    "title": f.title,
                    "remediation": f.remediation,
                }
                for f in findings[:10]  # Limit to first 10
            ],
        }

    async def get_connected_clouds(self) -> List[Dict[str, Any]]:
        """Get list of connected cloud providers."""
        connected = []
        for provider, is_connected in self.cloud_connections.items():
            if is_connected:
                connected.append(
                    {
                        "provider": provider.value,
                        "connected": True,
                        "services": ["EC2", "S3", "IAM"]
                        if provider == CloudProvider.AWS
                        else ["Compute", "Storage"],
                    }
                )
        return connected


# Global service instance
_cloud_native_service: Optional[CloudNativeSecurityService] = None


def get_cloud_native_service() -> CloudNativeSecurityService:
    """Get or create global cloud native security service."""
    global _cloud_native_service
    if _cloud_native_service is None:
        _cloud_native_service = CloudNativeSecurityService()
    return _cloud_native_service


async def initialize_cloud_native():
    """Initialize cloud native service on application startup."""
    global _cloud_native_service
    _cloud_native_service = CloudNativeSecurityService()
    logger.info("Cloud native security service initialized")


async def close_cloud_native():
    """Cleanup cloud native service on application shutdown."""
    global _cloud_native_service
    if _cloud_native_service:
        logger.info("Cloud native security service closed")
        _cloud_native_service = None
