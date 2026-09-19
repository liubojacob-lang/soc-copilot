"""
Cloud Native Security Service
Kubernetes, container, and cloud security monitoring
"""

import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from core.config import settings
from core.logger import get_logger

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
class K8sClusterInfo:
    """Kubernetes cluster summary info."""

    name: str
    provider: str
    region: str
    version: str
    status: str  # healthy, warning, critical
    nodes_count: int
    pods_count: int
    namespaces: list[str]
    created_at: datetime


@dataclass
class K8sResource:
    """Kubernetes resource."""

    name: str
    namespace: str
    kind: str  # Pod, Deployment, Service, etc.
    labels: dict[str, str]
    annotations: dict[str, str]
    spec: dict[str, Any]
    status: dict[str, Any]


@dataclass
class ContainerVulnerability:
    """Container vulnerability scan result."""

    image: str
    image_tag: str
    cve_id: str
    severity: str
    package_name: str
    fixed_version: str | None
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
    raw_event: dict[str, Any]
    timestamp: datetime


@dataclass
class ContainerDetail:
    """Detailed container instance information."""

    id: str
    name: str
    pod_name: str
    namespace: str
    cluster_name: str
    image: str
    status: str  # running, warning, terminated
    state_reason: str | None
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
    command: list[str] | None = None
    mounts: list[str] | None = None
    env_vars: dict[str, str] | None = None
    remediation: str | None = None


class CloudNativeSecurityService:
    """Cloud native security monitoring service."""

    def __init__(self):
        self.k8s_connected = False
        self.cloud_connections: dict[CloudProvider, bool] = {}
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
    ) -> list[ContainerVulnerability]:
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
        self, cluster_name: str, namespace: str | None = None
    ) -> list[K8sSecurityFinding]:
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

    async def get_kubernetes_clusters(self) -> list[K8sClusterInfo]:
        """
        Get connected Kubernetes clusters.

        Returns:
            List of connected Kubernetes clusters with health and metric stats.
        """
        return [
            K8sClusterInfo(
                name="k8s-prod-cluster",
                provider="AWS EKS",
                region="ap-east-1",
                version="v1.28.2",
                status="healthy",
                nodes_count=12,
                pods_count=36,
                namespaces=["production", "ingress-nginx", "monitoring", "kube-system"],
                created_at=datetime.now(),
            ),
            K8sClusterInfo(
                name="k8s-staging-cluster",
                provider="AliCloud ACK",
                region="cn-hangzhou",
                version="v1.27.4",
                status="warning",
                nodes_count=4,
                pods_count=9,
                namespaces=["staging", "kube-system", "default"],
                created_at=datetime.now(),
            ),
        ]

    async def get_kubernetes_resources(
        self, resource_type: str, namespace: str | None = None
    ) -> list[K8sResource]:
        """
        Get Kubernetes resources.

        Args:
            resource_type: Type of resource (pods, deployments, services, secrets, configmaps)
            namespace: Optional namespace filter

        Returns:
            List of resources
        """
        # In production, query actual K8s API via client-go or kubernetes-client
        r_type = resource_type.lower()
        resources_map = {
            "pods": [
                K8sResource(
                    name="web-app-7d4f8b9c5-x2abc",
                    namespace="production",
                    kind="Pod",
                    labels={"app": "web", "version": "v1"},
                    annotations={"prometheus.io/scrape": "true"},
                    spec={"containers": [{"name": "web", "image": "nginx:1.21"}]},
                    status={"phase": "Running", "restarts": 0, "ip": "10.244.1.15"},
                ),
                K8sResource(
                    name="api-service-6b9c8d-k912z",
                    namespace="production",
                    kind="Pod",
                    labels={"app": "api", "tier": "backend"},
                    annotations={},
                    spec={"containers": [{"name": "api", "image": "soc-api:v1.2"}]},
                    status={"phase": "Running", "restarts": 1, "ip": "10.244.1.16"},
                ),
                K8sResource(
                    name="redis-cache-0",
                    namespace="production",
                    kind="Pod",
                    labels={"app": "redis", "role": "master"},
                    annotations={},
                    spec={"containers": [{"name": "redis", "image": "redis:7-alpine"}]},
                    status={"phase": "Running", "restarts": 0, "ip": "10.244.2.4"},
                ),
                K8sResource(
                    name="staging-frontend-54c-789a",
                    namespace="staging",
                    kind="Pod",
                    labels={"app": "frontend-dev"},
                    annotations={},
                    spec={"containers": [{"name": "web", "image": "nginx:alpine"}]},
                    status={"phase": "Running", "restarts": 3, "ip": "10.244.3.11"},
                ),
            ],
            "deployments": [
                K8sResource(
                    name="web-app",
                    namespace="production",
                    kind="Deployment",
                    labels={"app": "web"},
                    annotations={},
                    spec={"replicas": 3, "strategy": "RollingUpdate"},
                    status={
                        "readyReplicas": 3,
                        "availableReplicas": 3,
                        "updatedReplicas": 3,
                    },
                ),
                K8sResource(
                    name="api-deployment",
                    namespace="production",
                    kind="Deployment",
                    labels={"app": "api"},
                    annotations={},
                    spec={"replicas": 2, "strategy": "RollingUpdate"},
                    status={
                        "readyReplicas": 2,
                        "availableReplicas": 2,
                        "updatedReplicas": 2,
                    },
                ),
                K8sResource(
                    name="auth-service",
                    namespace="production",
                    kind="Deployment",
                    labels={"app": "auth"},
                    annotations={},
                    spec={"replicas": 2, "strategy": "RollingUpdate"},
                    status={
                        "readyReplicas": 2,
                        "availableReplicas": 2,
                        "updatedReplicas": 2,
                    },
                ),
            ],
            "services": [
                K8sResource(
                    name="web-svc",
                    namespace="production",
                    kind="Service",
                    labels={"app": "web"},
                    annotations={
                        "service.beta.kubernetes.io/aws-load-balancer-type": "nlb"
                    },
                    spec={
                        "type": "LoadBalancer",
                        "ports": [{"port": 80, "targetPort": 80}],
                    },
                    status={"loadBalancer": {"ingress": [{"ip": "35.192.12.8"}]}},
                ),
                K8sResource(
                    name="api-internal-svc",
                    namespace="production",
                    kind="Service",
                    labels={"app": "api"},
                    annotations={},
                    spec={
                        "type": "ClusterIP",
                        "ports": [{"port": 8000, "targetPort": 8000}],
                    },
                    status={"clusterIP": "10.96.0.45"},
                ),
                K8sResource(
                    name="redis-svc",
                    namespace="production",
                    kind="Service",
                    labels={"app": "redis"},
                    annotations={},
                    spec={
                        "type": "ClusterIP",
                        "ports": [{"port": 6379, "targetPort": 6379}],
                    },
                    status={"clusterIP": "10.96.0.88"},
                ),
            ],
            "secrets": [
                K8sResource(
                    name="db-credentials",
                    namespace="production",
                    kind="Secret",
                    labels={"tier": "database"},
                    annotations={},
                    spec={"type": "Opaque", "dataKeys": ["username", "password"]},
                    status={"encryptedAtRest": False},
                ),
                K8sResource(
                    name="tls-wildcard-cert",
                    namespace="production",
                    kind="Secret",
                    labels={"app": "ingress"},
                    annotations={},
                    spec={
                        "type": "kubernetes.io/tls",
                        "dataKeys": ["tls.crt", "tls.key"],
                    },
                    status={"encryptedAtRest": True},
                ),
            ],
            "configmaps": [
                K8sResource(
                    name="nginx-config",
                    namespace="production",
                    kind="ConfigMap",
                    labels={"app": "web"},
                    annotations={},
                    spec={"dataKeys": ["nginx.conf", "mime.types"]},
                    status={},
                ),
                K8sResource(
                    name="cluster-domain-config",
                    namespace="kube-system",
                    kind="ConfigMap",
                    labels={"k8s-app": "kube-dns"},
                    annotations={},
                    spec={"dataKeys": ["Corefile"]},
                    status={},
                ),
            ],
        }

        # Fallback to general list if specific resource type not mapped
        sample_resources = resources_map.get(r_type)
        if sample_resources is None:
            sample_resources = resources_map["pods"] + resources_map["deployments"]

        if namespace:
            sample_resources = [r for r in sample_resources if r.namespace == namespace]

        return sample_resources

    async def collect_cloud_trails(
        self, provider: CloudProvider, hours: int = 24
    ) -> list[CloudSecurityEvent]:
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
        self, cluster_name: str | None = None
    ) -> dict[str, Any]:
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

    async def get_connected_clouds(self) -> list[dict[str, Any]]:
        """Get list of connected cloud providers."""
        connected = []
        for provider, is_connected in self.cloud_connections.items():
            if is_connected:
                connected.append(
                    {
                        "provider": provider.value,
                        "connected": True,
                        "services": (
                            ["EC2", "S3", "IAM"]
                            if provider == CloudProvider.AWS
                            else ["Compute", "Storage"]
                        ),
                    }
                )
        return connected

    def _build_simulated_containers(self) -> list[ContainerDetail]:
        """Build the catalog of 45 realistic simulated container instances."""
        containers: list[ContainerDetail] = []

        # ── Prod Cluster (36 containers) ──────────────────────────────────
        # Web frontend pods (3 containers)
        web_replicas = [
            ("01", "xk8w9", "10.244.1.10", "45m", "128Mi"),
            ("02", "b2k3m", "10.244.1.11", "42m", "124Mi"),
            ("03", "9q8lp", "10.244.2.12", "50m", "132Mi"),
        ]
        for seq, pod_hash, ip, cpu, mem in web_replicas:
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-web-{seq}",
                    name=f"soc-web-frontend-{pod_hash}",
                    pod_name=f"soc-web-frontend-79b94-{pod_hash}",
                    namespace="production",
                    cluster_name="k8s-prod-cluster",
                    image="soc-copilot-frontend:v0.9.0",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage=cpu,
                    memory_usage=mem,
                    ip_address=ip,
                    ports=["3000/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=True,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-10T08:00:00Z",
                    command=["node", "server.js"],
                    mounts=["/app/public", "/app/.next"],
                    env_vars={"NODE_ENV": "production", "PORT": "3000"},
                )
            )

        # API gateway pods (3 containers)
        api_replicas = [
            ("01", "m4q2p", "10.244.1.20", "120m", "256Mi"),
            ("02", "r8t1v", "10.244.2.21", "115m", "248Mi"),
            ("03", "3h7wk", "10.244.3.22", "130m", "260Mi"),
        ]
        for seq, pod_hash, ip, cpu, mem in api_replicas:
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-api-{seq}",
                    name=f"soc-api-gateway-{pod_hash}",
                    pod_name=f"soc-api-gateway-56c4d-{pod_hash}",
                    namespace="production",
                    cluster_name="k8s-prod-cluster",
                    image="soc-copilot-backend:v0.9.0",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage=cpu,
                    memory_usage=mem,
                    ip_address=ip,
                    ports=["8000/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=True,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-10T08:00:00Z",
                    command=[
                        "uvicorn",
                        "main:app",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "8000",
                    ],
                    mounts=["/app", "/tmp"],
                    env_vars={"ENVIRONMENT": "production", "LOG_LEVEL": "INFO"},
                )
            )

        # Auth service pods (2 containers - 1 vuln each)
        for seq, pod_hash, ip in [
            ("01", "9zpt4", "10.244.1.30"),
            ("02", "vx52k", "10.244.2.31"),
        ]:
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-auth-{seq}",
                    name=f"auth-service-{pod_hash}",
                    pod_name=f"auth-service-68d7-{pod_hash}",
                    namespace="production",
                    cluster_name="k8s-prod-cluster",
                    image="soc-auth:v1.0.2",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="60m",
                    memory_usage="180Mi",
                    ip_address=ip,
                    ports=["8080/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=False,
                    vulnerabilities_count=1,
                    critical_vulns=0,
                    high_vulns=1,
                    created_at="2026-09-11T02:00:00Z",
                    command=["/bin/auth-server"],
                    mounts=["/etc/certs"],
                    env_vars={"AUTH_MODE": "jwt-rs256"},
                    remediation="Upgrade soc-auth base image to patch CVE-2023-44487",
                )
            )

        # Redis cache pods (3 containers)
        for idx in range(3):
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-redis-0{idx+1}",
                    name=f"redis-cluster-{idx}",
                    pod_name=f"redis-cluster-{idx}",
                    namespace="production",
                    cluster_name="k8s-prod-cluster",
                    image="redis:7-alpine",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage=f"{30-idx}m",
                    memory_usage=f"{64-idx*2}Mi",
                    ip_address=f"10.244.{idx+1}.4{idx}",
                    ports=["6379/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=False,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-08T00:00:00Z",
                    command=["redis-server", "/usr/local/etc/redis/redis.conf"],
                    mounts=["/data"],
                    env_vars={"REDIS_PORT": "6379"},
                )
            )

        # PostgreSQL Primary & Replica (2 containers)
        for role, seq, ip, cpu, mem in [
            ("primary", "01", "10.244.1.50", "180m", "512Mi"),
            ("replica", "02", "10.244.2.51", "90m", "380Mi"),
        ]:
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-pg-{seq}",
                    name=f"postgres-{role}-0",
                    pod_name=f"postgres-{role}-0",
                    namespace="production",
                    cluster_name="k8s-prod-cluster",
                    image="postgres:15-alpine",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage=cpu,
                    memory_usage=mem,
                    ip_address=ip,
                    ports=["5432/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=False,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-05T00:00:00Z",
                    command=["postgres"],
                    mounts=["/var/lib/postgresql/data"],
                    env_vars={"POSTGRES_DB": "soc_prod_db"},
                )
            )

        # Elasticsearch Cluster (3 containers - 2 vulns each)
        for idx in range(3):
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-es-0{idx+1}",
                    name=f"es-master-{idx}",
                    pod_name=f"es-master-{idx}",
                    namespace="production",
                    cluster_name="k8s-prod-cluster",
                    image="elasticsearch:8.11.0",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage=f"{350-idx*20}m",
                    memory_usage=f"{1536-idx*40}Mi",
                    ip_address=f"10.244.{idx+1}.60",
                    ports=["9200/TCP", "9300/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=False,
                    vulnerabilities_count=2,
                    critical_vulns=0,
                    high_vulns=1,
                    created_at="2026-09-06T00:00:00Z",
                    command=["bin/elasticsearch"],
                    mounts=["/usr/share/elasticsearch/data"],
                    env_vars={"cluster.name": "soc-cluster", "discovery.type": "zen"},
                    remediation="Apply Elasticsearch 8.11.3 patch release",
                )
            )

        # Logstash Collectors (2 containers - 1 vuln each)
        for seq, pod_hash, ip in [
            ("01", "7h8k9", "10.244.1.70"),
            ("02", "3w2q1", "10.244.2.71"),
        ]:
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-logstash-{seq}",
                    name=f"logstash-collector-{pod_hash}",
                    pod_name=f"logstash-collector-49b-{pod_hash}",
                    namespace="production",
                    cluster_name="k8s-prod-cluster",
                    image="logstash:8.11.0",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="200m",
                    memory_usage="750Mi",
                    ip_address=ip,
                    ports=["5044/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=False,
                    vulnerabilities_count=1,
                    critical_vulns=0,
                    high_vulns=1,
                    created_at="2026-09-07T00:00:00Z",
                    command=["/usr/share/logstash/bin/logstash"],
                    mounts=["/usr/share/logstash/pipeline"],
                    env_vars={"PIPELINE_WORKERS": "2"},
                )
            )

        # Ingress Nginx Controllers (2 containers)
        for seq, pod_hash, ip in [
            ("01", "z8fgh", "10.244.1.80"),
            ("02", "p5c9x", "10.244.2.81"),
        ]:
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-ingress-{seq}",
                    name=f"ingress-nginx-controller-{pod_hash}",
                    pod_name=f"ingress-nginx-controller-8567-{pod_hash}",
                    namespace="ingress-nginx",
                    cluster_name="k8s-prod-cluster",
                    image="registry.k8s.io/ingress-nginx/controller:v1.8.1",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="150m",
                    memory_usage="220Mi",
                    ip_address=ip,
                    ports=["80/TCP", "443/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=True,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-01T00:00:00Z",
                    command=["/nginx-ingress-controller"],
                    mounts=["/etc/ingress-controller"],
                    env_vars={"POD_NAME": f"ingress-{pod_hash}"},
                )
            )

        # Cert-Manager (3 containers)
        cert_comps = [
            (
                "mgr",
                "cert-manager-controller",
                "7856-t4k9q",
                "10.244.1.82",
                ["9402/TCP"],
            ),
            ("cainjector", "cert-manager-cainjector", "547-j8w2l", "10.244.2.83", []),
            (
                "webhook",
                "cert-manager-webhook",
                "6b8c-r1q7z",
                "10.244.3.84",
                ["10250/TCP"],
            ),
        ]
        for key, c_name, pod_hash, ip, ports in cert_comps:
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-cert-{key}",
                    name=f"{c_name}-{pod_hash}",
                    pod_name=f"{c_name}-{pod_hash}",
                    namespace="ingress-nginx",
                    cluster_name="k8s-prod-cluster",
                    image="quay.io/jetstack/cert-manager-controller:v1.13.0",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="15m",
                    memory_usage="45Mi",
                    ip_address=ip,
                    ports=ports,
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=True,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-01T00:00:00Z",
                )
            )

        # Prometheus & Monitoring (2 Prom + 1 Grafana + 3 Node-Exporter + 1 KSM = 7 containers)
        for idx in range(2):
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-prom-0{idx+1}",
                    name=f"prometheus-k8s-{idx}",
                    pod_name=f"prometheus-k8s-{idx}",
                    namespace="monitoring",
                    cluster_name="k8s-prod-cluster",
                    image="quay.io/prometheus/prometheus:v2.47.0",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="280m",
                    memory_usage="1024Mi",
                    ip_address=f"10.244.{idx+1}.90",
                    ports=["9090/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=False,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-02T00:00:00Z",
                    command=[
                        "/bin/prometheus",
                        "--config.file=/etc/prometheus/prometheus.yml",
                    ],
                    mounts=["/prometheus", "/etc/prometheus"],
                )
            )

        containers.append(
            ContainerDetail(
                id="cnt-prod-grafana-01",
                name="grafana-core-c8h1x",
                pod_name="grafana-core-59df9-c8h1x",
                namespace="monitoring",
                cluster_name="k8s-prod-cluster",
                image="grafana/grafana:10.1.2",
                status="running",
                state_reason=None,
                restart_count=0,
                cpu_usage="65m",
                memory_usage="190Mi",
                ip_address="10.244.1.92",
                ports=["3000/TCP"],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=False,
                vulnerabilities_count=0,
                critical_vulns=0,
                high_vulns=0,
                created_at="2026-09-02T00:00:00Z",
                mounts=["/var/lib/grafana"],
            )
        )

        for idx, h in enumerate(["4j9q2", "8h2b5", "3m7w1"]):
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-node-exp-0{idx+1}",
                    name=f"node-exporter-{h}",
                    pod_name=f"node-exporter-{h}",
                    namespace="monitoring",
                    cluster_name="k8s-prod-cluster",
                    image="quay.io/prometheus/node-exporter:v1.6.1",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="15m",
                    memory_usage="32Mi",
                    ip_address=f"10.244.{idx+1}.93",
                    ports=["9100/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=True,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-02T00:00:00Z",
                )
            )

        containers.append(
            ContainerDetail(
                id="cnt-prod-ksm-01",
                name="kube-state-metrics-r9t2w",
                pod_name="kube-state-metrics-7548-r9t2w",
                namespace="monitoring",
                cluster_name="k8s-prod-cluster",
                image="registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.9.2",
                status="running",
                state_reason=None,
                restart_count=0,
                cpu_usage="35m",
                memory_usage="80Mi",
                ip_address="10.244.1.96",
                ports=["8080/TCP"],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=True,
                vulnerabilities_count=0,
                critical_vulns=0,
                high_vulns=0,
                created_at="2026-09-02T00:00:00Z",
            )
        )

        # Falco DaemonSet (3 containers - Privileged / Security Context Warning)
        for idx, h in enumerate(["7x8k2", "2k9p1", "6w4r8"]):
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-falco-0{idx+1}",
                    name=f"falco-daemon-{h}",
                    pod_name=f"falco-daemon-node{idx+1}-{h}",
                    namespace="kube-system",
                    cluster_name="k8s-prod-cluster",
                    image="falcosecurity/falco:0.36.2",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="120m",
                    memory_usage="160Mi",
                    ip_address=f"10.244.{idx+1}.10{idx}",
                    ports=["8765/TCP"],
                    privileged=True,
                    run_as_root=True,
                    readonly_rootfs=False,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-01T00:00:00Z",
                    command=[
                        "/usr/bin/falco",
                        "-K",
                        "/var/run/secrets/kubernetes.io/serviceaccount/token",
                    ],
                    mounts=["/var/run/docker.sock", "/dev", "/proc", "/boot"],
                    env_vars={"FALCO_BPF_PROBE": ""},
                    remediation="Legitimate security daemonset; ensure strict node isolation and RBAC audit",
                )
            )

        # CoreDNS (2 containers)
        for idx, h in enumerate(["q92k8", "wr51t"]):
            containers.append(
                ContainerDetail(
                    id=f"cnt-prod-coredns-0{idx+1}",
                    name=f"coredns-{h}",
                    pod_name=f"coredns-5dd57-{h}",
                    namespace="kube-system",
                    cluster_name="k8s-prod-cluster",
                    image="registry.k8s.io/coredns/coredns:v1.10.1",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="25m",
                    memory_usage="45Mi",
                    ip_address=f"10.244.{idx+1}.105",
                    ports=["53/UDP", "53/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=True,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-01T00:00:00Z",
                )
            )

        # Vault Agent (1 container - Warning CrashLoopBackOff - 1 vuln)
        containers.append(
            ContainerDetail(
                id="cnt-prod-vault-01",
                name="vault-agent-init-x9z",
                pod_name="vault-agent-init-89ab-x9z",
                namespace="production",
                cluster_name="k8s-prod-cluster",
                image="hashicorp/vault:1.14.0",
                status="warning",
                state_reason="CrashLoopBackOff",
                restart_count=5,
                cpu_usage="0m",
                memory_usage="12Mi",
                ip_address="10.244.1.110",
                ports=[],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=False,
                vulnerabilities_count=1,
                critical_vulns=0,
                high_vulns=1,
                created_at="2026-09-14T01:00:00Z",
                command=["vault", "agent", "-config=/vault/config/agent.hcl"],
                mounts=["/vault/config"],
                env_vars={"VAULT_ADDR": "https://vault.internal:8200"},
                remediation="Check Vault connection credentials and TLS token renew configuration",
            )
        )

        # ── Staging Cluster (9 containers) ────────────────────────────────
        containers.append(
            ContainerDetail(
                id="cnt-stage-web-01",
                name="staging-web-4k8x1",
                pod_name="staging-web-6d9b-4k8x1",
                namespace="staging",
                cluster_name="k8s-staging-cluster",
                image="soc-copilot-frontend:staging",
                status="running",
                state_reason=None,
                restart_count=0,
                cpu_usage="30m",
                memory_usage="90Mi",
                ip_address="10.244.4.10",
                ports=["3000/TCP"],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=True,
                vulnerabilities_count=0,
                critical_vulns=0,
                high_vulns=0,
                created_at="2026-09-12T00:00:00Z",
            )
        )

        for seq, pod_hash, ip in [
            ("01", "2j9z4", "10.244.4.20"),
            ("02", "9w1t8", "10.244.4.21"),
        ]:
            containers.append(
                ContainerDetail(
                    id=f"cnt-stage-api-{seq}",
                    name=f"staging-api-{pod_hash}",
                    pod_name=f"staging-api-7b8c-{pod_hash}",
                    namespace="staging",
                    cluster_name="k8s-staging-cluster",
                    image="soc-copilot-backend:staging",
                    status="running",
                    state_reason=None,
                    restart_count=0,
                    cpu_usage="80m",
                    memory_usage="190Mi",
                    ip_address=ip,
                    ports=["8000/TCP"],
                    privileged=False,
                    run_as_root=False,
                    readonly_rootfs=True,
                    vulnerabilities_count=0,
                    critical_vulns=0,
                    high_vulns=0,
                    created_at="2026-09-12T00:00:00Z",
                )
            )

        containers.append(
            ContainerDetail(
                id="cnt-stage-redis-01",
                name="staging-redis-0",
                pod_name="staging-redis-0",
                namespace="staging",
                cluster_name="k8s-staging-cluster",
                image="redis:7-alpine",
                status="running",
                state_reason=None,
                restart_count=0,
                cpu_usage="18m",
                memory_usage="40Mi",
                ip_address="10.244.4.30",
                ports=["6379/TCP"],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=False,
                vulnerabilities_count=0,
                critical_vulns=0,
                high_vulns=0,
                created_at="2026-09-12T00:00:00Z",
            )
        )

        containers.append(
            ContainerDetail(
                id="cnt-stage-pg-01",
                name="staging-db-0",
                pod_name="staging-db-0",
                namespace="staging",
                cluster_name="k8s-staging-cluster",
                image="postgres:15-alpine",
                status="running",
                state_reason=None,
                restart_count=0,
                cpu_usage="95m",
                memory_usage="280Mi",
                ip_address="10.244.4.40",
                ports=["5432/TCP"],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=False,
                vulnerabilities_count=0,
                critical_vulns=0,
                high_vulns=0,
                created_at="2026-09-12T00:00:00Z",
            )
        )

        containers.append(
            ContainerDetail(
                id="cnt-stage-ingress-01",
                name="staging-ingress-p1q8z",
                pod_name="staging-ingress-75c-p1q8z",
                namespace="kube-system",
                cluster_name="k8s-staging-cluster",
                image="ingress-nginx:v1.8.1",
                status="running",
                state_reason=None,
                restart_count=0,
                cpu_usage="50m",
                memory_usage="110Mi",
                ip_address="10.244.4.50",
                ports=["80/TCP", "443/TCP"],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=True,
                vulnerabilities_count=0,
                critical_vulns=0,
                high_vulns=0,
                created_at="2026-09-12T00:00:00Z",
            )
        )

        containers.append(
            ContainerDetail(
                id="cnt-stage-siem-01",
                name="staging-mock-siem-t9r2x",
                pod_name="staging-mock-siem-8c4d-t9r2x",
                namespace="default",
                cluster_name="k8s-staging-cluster",
                image="mock-siem:latest",
                status="running",
                state_reason=None,
                restart_count=0,
                cpu_usage="40m",
                memory_usage="120Mi",
                ip_address="10.244.4.60",
                ports=["9000/TCP"],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=False,
                vulnerabilities_count=0,
                critical_vulns=0,
                high_vulns=0,
                created_at="2026-09-13T00:00:00Z",
            )
        )

        # Legacy report app (Warning - 5 vulns, run_as_root = True)
        containers.append(
            ContainerDetail(
                id="cnt-stage-legacy-01",
                name="legacy-report-app-z4p1m",
                pod_name="legacy-report-app-58b-z4p1m",
                namespace="default",
                cluster_name="k8s-staging-cluster",
                image="nginx:1.21",
                status="warning",
                state_reason="SecurityPolicyViolation",
                restart_count=2,
                cpu_usage="35m",
                memory_usage="64Mi",
                ip_address="10.244.4.70",
                ports=["80/TCP"],
                privileged=False,
                run_as_root=True,
                readonly_rootfs=False,
                vulnerabilities_count=5,
                critical_vulns=0,
                high_vulns=3,
                created_at="2026-09-13T00:00:00Z",
                command=["nginx", "-g", "daemon off;"],
                mounts=["/usr/share/nginx/html"],
                env_vars={"REPORT_ENV": "staging"},
                remediation="Update nginx:1.21 to nginx:1.25-alpine and enforce runAsNonRoot: true",
            )
        )

        # Backup CronJob Pod (Terminated / Completed)
        containers.append(
            ContainerDetail(
                id="cnt-stage-backup-01",
                name="db-backup-99ab",
                pod_name="db-backup-283921-99ab",
                namespace="staging",
                cluster_name="k8s-staging-cluster",
                image="bitnami/postgresql-client:15",
                status="terminated",
                state_reason="Completed",
                restart_count=0,
                cpu_usage="0m",
                memory_usage="0Mi",
                ip_address="10.244.4.80",
                ports=[],
                privileged=False,
                run_as_root=False,
                readonly_rootfs=True,
                vulnerabilities_count=0,
                critical_vulns=0,
                high_vulns=0,
                created_at="2026-09-14T02:00:00Z",
                command=["pg_dump", "-h", "staging-db", "-U", "postgres"],
                mounts=["/backup"],
            )
        )

        return containers

    async def get_containers(
        self,
        cluster: str | None = None,
        namespace: str | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> dict[str, Any]:
        """
        Query container instances with filtering, aggregate summary, and pagination.
        """
        all_containers = self._build_simulated_containers()
        filtered = all_containers

        if isinstance(cluster, str) and cluster.strip():
            filtered = [
                c for c in filtered if c.cluster_name.lower() == cluster.lower().strip()
            ]
        if isinstance(namespace, str) and namespace.strip():
            filtered = [
                c for c in filtered if c.namespace.lower() == namespace.lower().strip()
            ]
        if isinstance(status, str) and status.lower() != "all" and status.strip():
            filtered = [
                c for c in filtered if c.status.lower() == status.lower().strip()
            ]
        if isinstance(search, str) and search.strip():
            q = search.lower().strip()
            filtered = [
                c
                for c in filtered
                if q in c.name.lower()
                or q in c.image.lower()
                or q in c.pod_name.lower()
                or q in c.namespace.lower()
            ]

        # Calculate breakdown stats from the full set
        running_cnt = len([c for c in all_containers if c.status == "running"])
        warning_cnt = len([c for c in all_containers if c.status == "warning"])
        terminated_cnt = len([c for c in all_containers if c.status == "terminated"])
        vulnerable_cnt = len([c for c in all_containers if c.vulnerabilities_count > 0])

        # Pagination calculations
        safe_page = page if isinstance(page, int) and page >= 1 else 1
        safe_page_size = (
            page_size if isinstance(page_size, int) and page_size >= 1 else 10
        )
        filtered_count = len(filtered)
        total_pages = (
            max(1, math.ceil(filtered_count / safe_page_size))
            if safe_page_size > 0
            else 1
        )

        # Slicing
        start_idx = (safe_page - 1) * safe_page_size
        end_idx = start_idx + safe_page_size
        paginated_containers = filtered[start_idx:end_idx]

        return {
            "total": len(all_containers),
            "filtered_total": filtered_count,
            "page": safe_page,
            "page_size": safe_page_size,
            "total_pages": total_pages,
            "running": running_cnt,
            "warning": warning_cnt,
            "terminated": terminated_cnt,
            "vulnerable": vulnerable_cnt,
            "containers": [
                {
                    "id": c.id,
                    "name": c.name,
                    "pod_name": c.pod_name,
                    "namespace": c.namespace,
                    "cluster_name": c.cluster_name,
                    "image": c.image,
                    "status": c.status,
                    "state_reason": c.state_reason,
                    "restart_count": c.restart_count,
                    "cpu_usage": c.cpu_usage,
                    "memory_usage": c.memory_usage,
                    "ip_address": c.ip_address,
                    "ports": c.ports,
                    "privileged": c.privileged,
                    "run_as_root": c.run_as_root,
                    "readonly_rootfs": c.readonly_rootfs,
                    "vulnerabilities_count": c.vulnerabilities_count,
                    "critical_vulns": c.critical_vulns,
                    "high_vulns": c.high_vulns,
                    "created_at": c.created_at,
                    "node_name": c.node_name,
                    "remediation": c.remediation,
                }
                for c in paginated_containers
            ],
        }

    async def get_container_detail(self, container_id: str) -> dict[str, Any] | None:
        """
        Get full detailed information for a single container instance.
        """
        all_containers = self._build_simulated_containers()
        for c in all_containers:
            if c.id == container_id or c.name == container_id:
                return {
                    "id": c.id,
                    "name": c.name,
                    "pod_name": c.pod_name,
                    "namespace": c.namespace,
                    "cluster_name": c.cluster_name,
                    "image": c.image,
                    "status": c.status,
                    "state_reason": c.state_reason,
                    "restart_count": c.restart_count,
                    "cpu_usage": c.cpu_usage,
                    "memory_usage": c.memory_usage,
                    "ip_address": c.ip_address,
                    "ports": c.ports,
                    "privileged": c.privileged,
                    "run_as_root": c.run_as_root,
                    "readonly_rootfs": c.readonly_rootfs,
                    "vulnerabilities_count": c.vulnerabilities_count,
                    "critical_vulns": c.critical_vulns,
                    "high_vulns": c.high_vulns,
                    "created_at": c.created_at,
                    "node_name": c.node_name,
                    "command": c.command or ["/bin/sh"],
                    "mounts": c.mounts or ["/tmp"],
                    "env_vars": c.env_vars or {},
                    "remediation": c.remediation,
                }
        return None


# Global service instance
_cloud_native_service: CloudNativeSecurityService | None = None


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
