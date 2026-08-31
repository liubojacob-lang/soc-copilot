"""Asset Discovery Service — F3-5: Automatic network & cloud asset discovery.

Provides:
- NMAP-based network scanning
- Cloud API resource discovery (AWS/Azure/GCP stubs)
- Automatic registration of discovered assets into the assets table
"""

import asyncio
import json
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger

logger = get_logger(__name__)


# ── Data types ───────────────────────────────────────────────────────────


@dataclass
class DiscoveredHost:
    """Result of a network/cloud discovery scan."""

    hostname: str | None = None
    ip: str | None = None
    os: str | None = None
    os_version: str | None = None
    mac: str | None = None
    open_ports: list[int] = field(default_factory=list)
    services: list[str] = field(default_factory=list)
    source: str = "nmap"  # nmap, aws, azure, gcp
    instance_id: str | None = None  # cloud instance ID
    instance_type: str | None = None
    status: str = "unknown"  # running, stopped, terminated
    region: str | None = None

    def to_asset_dict(self) -> dict[str, Any]:
        """Convert to dict matching assets table schema."""
        return {
            "hostname": self.hostname or self.ip or "unknown",
            "ip": self.ip,
            "business": f"auto-discovered ({self.source})",
            "criticality": self._infer_criticality(),
            "tags": json.dumps(self._build_tags()),
            "notes": self._build_notes(),
            "is_active": self.status != "terminated",
        }

    def _infer_criticality(self) -> str:
        """Heuristic criticality based on open ports and services."""
        critical_ports = {22, 3389, 1433, 3306, 5432, 6379, 27017}
        if any(p in critical_ports for p in self.open_ports):
            return "high"
        if any("database" in s.lower() or "db" in s.lower() for s in self.services):
            return "critical"
        return "medium"

    def _build_tags(self) -> list[str]:
        """Build tag list from discovered info."""
        tags = [f"source:{self.source}"]
        if self.region:
            tags.append(f"region:{self.region}")
        for port in self.open_ports:
            tags.append(f"port:{port}")
        return tags

    def _build_notes(self) -> str:
        """Build notes string."""
        parts = [f"Auto-discovered via {self.source}"]
        if self.os:
            parts.append(f"OS: {self.os}")
        if self.open_ports:
            parts.append(f"Open ports: {','.join(str(p) for p in self.open_ports)}")
        if self.services:
            parts.append(f"Services: {','.join(self.services)}")
        if self.instance_id:
            parts.append(f"Instance: {self.instance_id}")
        return " | ".join(parts)


@dataclass
class DiscoveryResult:
    """Aggregate result of a discovery scan."""

    hosts: list[DiscoveredHost] = field(default_factory=list)
    scanned_count: int = 0
    new_assets: int = 0
    skipped_assets: int = 0
    errors: list[str] = field(default_factory=list)
    scan_duration_ms: float = 0.0


# ── NMAP Scanner ─────────────────────────────────────────────────────────


def _find_nmap() -> str | None:
    """Locate the nmap binary on the system."""
    try:
        result = subprocess.run(
            ["which", "nmap"], capture_output=True, text=True, timeout=5
        )
        path = result.stdout.strip()
        if path and result.returncode == 0:
            return path
    except Exception:
        pass

    # Fallback paths
    for candidate in ["/usr/bin/nmap", "/usr/local/bin/nmap", "/opt/homebrew/bin/nmap"]:
        try:
            subprocess.run([candidate, "--version"], capture_output=True, timeout=3)
            return candidate
        except Exception:
            continue

    return None


async def _run_nmap_scan(
    target: str,
    ports: str | None = None,
    fast_mode: bool = True,
) -> list[DiscoveredHost]:
    """Run nmap scan against a target IP range and parse results.

    Args:
        target: IP range (e.g. "192.168.1.0/24") or host
        ports: Port spec (e.g. "1-1024"), None for default
        fast_mode: Use -T4 -F for speed

    Returns:
        List of discovered hosts
    """
    nmap_path = _find_nmap()
    if not nmap_path:
        logger.warning("nmap not found on system — skipping NMAP scan")
        return []

    cmd = [nmap_path, "-sV", "-O", "--osscan-guess", "-oX", "-"]
    if fast_mode:
        cmd.extend(["-T4", "-F"])
    if ports:
        cmd.extend(["-p", ports])
    cmd.append(target)

    try:
        logger.info(f"Running nmap: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=300
        )

        if proc.returncode != 0 and proc.returncode != 1:
            # nmap returncode 1 is normal (some hosts down)
            logger.warning(f"nmap exited with {proc.returncode}: {stderr.decode()[:500]}")

        return _parse_nmap_xml(stdout.decode(errors="replace"))

    except asyncio.TimeoutError:
        logger.error(f"nmap scan timed out for {target}")
        return []
    except FileNotFoundError:
        logger.error("nmap binary not found")
        return []
    except Exception as e:
        logger.error(f"nmap scan failed: {e}")
        return []


def _parse_nmap_xml(xml_output: str) -> list[DiscoveredHost]:
    """Parse nmap XML output into DiscoveredHost objects.

    Uses regex-based parsing as a lightweight alternative to full XML parsing,
    avoiding extra dependencies.
    """
    hosts: list[DiscoveredHost] = []

    # Split by <host ... </host>
    host_blocks = re.findall(
        r"<host[^>]*>(.*?)</host>", xml_output, re.DOTALL
    )

    for block in host_blocks:
        host = DiscoveredHost()

        # Extract addresses
        addrs = re.findall(
            r'<address\s+addr="([^"]+)"\s+addrtype="([^"]+)".*?/>', block
        )
        for addr, atype in addrs:
            if atype == "ipv4":
                host.ip = addr
            elif atype == "mac":
                host.mac = addr

        # Extract hostnames
        hostnames = re.findall(
            r'<hostname\s+name="([^"]+)"\s+type="([^"]+)"', block
        )
        for name, htype in hostnames:
            if htype == "PTR" or htype == "user":
                host.hostname = name
                break
        if not host.hostname and hostnames:
            host.hostname = hostnames[0][0]

        # Extract ports and services
        ports = re.findall(
            r'<port\s+protocol="([^"]+)"\s+portid="([^"]+)">.*?<state\s+state="([^"]+)".*?<service\s+name="([^"]+)".*?(?:product="([^"]*)")?.*?(?:version="([^"]*)")?.*?</port>',
            block,
            re.DOTALL,
        )
        host.open_ports = []
        host.services = []
        for proto, port_id, state, svc_name, product, version in ports:
            if state == "open":
                host.open_ports.append(int(port_id))
                svc_str = svc_name
                if product:
                    svc_str = f"{product}"
                    if version:
                        svc_str += f" {version}"
                if svc_str not in host.services:
                    host.services.append(svc_str)

        # Extract OS
        os_match = re.search(
            r'<osmatch\s+name="([^"]+)"\s+accuracy="([^"]+)"', block
        )
        if os_match:
            host.os = os_match.group(1)

        # Status
        status_match = re.search(r'<status\s+state="([^"]+)"', block)
        if status_match:
            host.status = status_match.group(1)

        if host.ip:
            hosts.append(host)

    return hosts


# ── Cloud Discovery (stubs) ──────────────────────────────────────────────


async def discover_aws_instances(
    region: str = "us-east-1",
    access_key: str | None = None,
    secret_key: str | None = None,
) -> list[DiscoveredHost]:
    """AWS EC2 resource discovery — stub implementation.

    Real implementation would use boto3:
        ec2 = boto3.client('ec2', region_name=region)
        resp = ec2.describe_instances()
        # parse instances

    Args:
        region: AWS region
        access_key: AWS access key (optional)
        secret_key: AWS secret key (optional)

    Returns:
        List of discovered hosts
    """
    logger.info(f"AWS EC2 discovery: region={region} (stub mode)")

    # Stub: return sample data structure
    # In production, replace with boto3 EC2 describe_instances()
    hosts: list[DiscoveredHost] = []

    try:
        # Attempt boto3 import; if unavailable, return stub data
        import boto3  # type: ignore[import-untyped]

        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )
        ec2 = session.client("ec2")
        resp = ec2.describe_instances()

        for reservation in resp.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                private_ip = instance.get("PrivateIpAddress")
                public_ip = instance.get("PublicIpAddress")
                host = DiscoveredHost(
                    hostname=instance.get("PrivateDnsName", "").split(".")[0],
                    ip=private_ip or public_ip,
                    instance_id=instance.get("InstanceId"),
                    instance_type=instance.get("InstanceType"),
                    source="aws",
                    status=instance.get("State", {}).get("Name", "unknown"),
                    region=region,
                )
                hosts.append(host)
    except ImportError:
        logger.info("boto3 not installed; returning AWS stub data")
        hosts = [
            DiscoveredHost(
                hostname="aws-web-prod-01",
                ip="10.0.1.100",
                instance_id="i-0a1b2c3d4e5f67890",
                instance_type="t3.medium",
                source="aws",
                status="running",
                region=region,
                open_ports=[22, 80, 443],
                services=["nginx", "ssh"],
            ),
            DiscoveredHost(
                hostname="aws-db-prod-01",
                ip="10.0.2.50",
                instance_id="i-0b2c3d4e5f6a78901",
                instance_type="r5.large",
                source="aws",
                status="running",
                region=region,
                open_ports=[3306, 5432],
                services=["mysql", "postgresql"],
            ),
        ]
    except Exception as e:
        logger.error(f"AWS discovery failed: {e}")
        return []

    return hosts


async def discover_azure_instances(
    subscription_id: str | None = None,
    resource_group: str | None = None,
) -> list[DiscoveredHost]:
    """Azure VM resource discovery — stub implementation.

    Real implementation would use azure-mgmt-compute:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.compute import ComputeManagementClient

    Args:
        subscription_id: Azure subscription ID
        resource_group: Azure resource group

    Returns:
        List of discovered hosts
    """
    logger.info(f"Azure VM discovery: subscription={subscription_id} (stub mode)")

    # Stub: return sample data
    return [
        DiscoveredHost(
            hostname="az-app-prod-01",
            ip="10.1.0.20",
            instance_id="/subscriptions/xxx/resourceGroups/rg-prod/virtualMachines/app-prod-01",
            instance_type="Standard_D4s_v3",
            source="azure",
            status="running",
            region="eastus",
            open_ports=[22, 443, 8080],
            services=["nginx", "java/tomcat"],
        ),
    ]


async def discover_gcp_instances(
    project_id: str | None = None,
    zone: str = "us-central1-a",
) -> list[DiscoveredHost]:
    """GCP Compute Engine resource discovery — stub implementation.

    Real implementation would use google-cloud-compute:
        from google.cloud import compute_v1

    Args:
        project_id: GCP project ID
        zone: GCP zone

    Returns:
        List of discovered hosts
    """
    logger.info(f"GCP discovery: project={project_id}, zone={zone} (stub mode)")

    return [
        DiscoveredHost(
            hostname="gcp-gke-node-01",
            ip="10.128.0.10",
            instance_id="1234567890123456789",
            instance_type="e2-standard-4",
            source="gcp",
            status="running",
            region=zone,
            open_ports=[22, 10250, 30000],
            services=["kubelet", "node-exporter"],
        ),
    ]


# ── Asset Discovery Service ──────────────────────────────────────────────


class AssetDiscoveryService:
    """Orchestrates network and cloud asset discovery.

    Scans configured IP ranges, queries cloud APIs, and registers
    newly discovered assets in the assets database table.
    """

    def __init__(
        self,
        session: AsyncSession,
        default_ip_ranges: list[str] | None = None,
    ):
        """Initialize discovery service.

        Args:
            session: Database session
            default_ip_ranges: Default IP ranges to scan
        """
        self.session = session
        self.default_ranges = default_ip_ranges or [
            "192.168.1.0/24",
            "10.0.0.0/24",
        ]

    async def discover_network(
        self,
        targets: list[str] | None = None,
        ports: str | None = None,
        fast_mode: bool = True,
    ) -> DiscoveryResult:
        """Run NMAP scan and discover network hosts.

        Args:
            targets: IP ranges to scan
            ports: Port specification
            fast_mode: Use fast scan flags

        Returns:
            DiscoveryResult
        """
        targets = targets or self.default_ranges
        result = DiscoveryResult()
        t_start = datetime.now()

        for target in targets:
            hosts = await _run_nmap_scan(target, ports, fast_mode)
            result.hosts.extend(hosts)
            result.scanned_count += 1

        result.scan_duration_ms = (
            datetime.now() - t_start
        ).total_seconds() * 1000

        # Register discovered hosts
        await self._register_hosts(result)

        return result

    async def discover_cloud(
        self,
        provider: str = "aws",
        **kwargs: Any,
    ) -> DiscoveryResult:
        """Run cloud API discovery.

        Args:
            provider: Cloud provider (aws, azure, gcp)
            **kwargs: Provider-specific parameters

        Returns:
            DiscoveryResult
        """
        result = DiscoveryResult()
        t_start = datetime.now()

        if provider == "aws":
            result.hosts = await discover_aws_instances(
                region=kwargs.get("region", "us-east-1"),
                access_key=kwargs.get("access_key"),
                secret_key=kwargs.get("secret_key"),
            )
        elif provider == "azure":
            result.hosts = await discover_azure_instances(
                subscription_id=kwargs.get("subscription_id"),
                resource_group=kwargs.get("resource_group"),
            )
        elif provider == "gcp":
            result.hosts = await discover_gcp_instances(
                project_id=kwargs.get("project_id"),
                zone=kwargs.get("zone", "us-central1-a"),
            )
        else:
            result.errors.append(f"Unknown provider: {provider}")

        result.scanned_count = 1
        result.scan_duration_ms = (
            datetime.now() - t_start
        ).total_seconds() * 1000

        # Register discovered hosts
        await self._register_hosts(result)

        return result

    async def discover_all(
        self,
        network_targets: list[str] | None = None,
        cloud_providers: list[str] | None = None,
    ) -> DiscoveryResult:
        """Run both network and cloud discovery.

        Args:
            network_targets: IP ranges
            cloud_providers: List of cloud providers

        Returns:
            Combined result
        """
        combined = DiscoveryResult()

        # Network scan
        net_result = await self.discover_network(network_targets)
        combined.hosts.extend(net_result.hosts)
        combined.scanned_count += net_result.scanned_count
        combined.errors.extend(net_result.errors)

        # Cloud scans in parallel
        providers = cloud_providers or ["aws", "azure", "gcp"]
        cloud_tasks = [
            self.discover_cloud(provider) for provider in providers
        ]
        cloud_results = await asyncio.gather(*cloud_tasks, return_exceptions=True)
        for cr in cloud_results:
            if isinstance(cr, Exception):
                combined.errors.append(str(cr))
            elif isinstance(cr, DiscoveryResult):
                combined.hosts.extend(cr.hosts)
                combined.scanned_count += cr.scanned_count
                combined.errors.extend(cr.errors)

        combined.new_assets = await self._register_hosts(combined)
        return combined

    async def _register_hosts(self, result: DiscoveryResult) -> int:
        """Auto-register discovered hosts in the assets table.

        Skips hosts that already exist (by IP or hostname).

        Args:
            result: DiscoveryResult with hosts to register

        Returns:
            Number of newly registered assets
        """
        new_count = 0

        for host in result.hosts:
            if not host.ip and not host.hostname:
                continue

            exists = await self._host_exists(host)
            if exists:
                result.skipped_assets += 1
                continue

            try:
                await self._insert_asset(host)
                new_count += 1
                result.new_assets += 1
            except Exception as e:
                err_msg = f"Failed to insert {host.hostname or host.ip}: {e}"
                logger.error(err_msg)
                result.errors.append(err_msg)

        logger.info(
            f"Asset registration: {new_count} new, {result.skipped_assets} skipped"
        )
        return new_count

    async def _host_exists(self, host: DiscoveredHost) -> bool:
        """Check if a host already exists in the assets table."""
        from models.asset import AssetDB

        conditions = []
        if host.ip:
            conditions.append(AssetDB.ip == host.ip)
        if host.hostname:
            conditions.append(AssetDB.hostname == host.hostname)

        if not conditions:
            return False

        from sqlalchemy import or_

        stmt = select(AssetDB.id).where(or_(*conditions)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _insert_asset(self, host: DiscoveredHost) -> None:
        """Insert a discovered host as a new asset."""
        import uuid

        from models.asset import AssetDB

        asset_dict = host.to_asset_dict()
        asset = AssetDB(
            id=str(uuid.uuid4()),
            hostname=asset_dict["hostname"],
            ip=asset_dict["ip"],
            business=asset_dict["business"],
            criticality=asset_dict["criticality"],
            tags=asset_dict["tags"],
            notes=asset_dict["notes"],
            is_active=asset_dict["is_active"],
        )
        self.session.add(asset)
        await self.session.commit()
        logger.info(f"Registered new asset: {host.hostname or host.ip}")
