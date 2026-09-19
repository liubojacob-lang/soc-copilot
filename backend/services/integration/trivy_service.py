"""
Trivy Image Scanning Service
Integrates with Trivy CLI for container image vulnerability scanning.
Caches results in DB to avoid redundant scans (24h TTL).
"""

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger

logger = get_logger(__name__)

SCAN_CACHE_TTL_HOURS = 24


class TrivyNotInstalledError(Exception):
    """Raised when Trivy binary is not found on the host.

    T1.2: Security scanners must never return fabricated vulnerability data.
    When Trivy is not installed, callers receive this exception and should
    surface a clear 'scanner not installed' message to the user instead of
    returning mock CVE results.
    """

    def __init__(self) -> None:
        super().__init__(
            "Trivy scanner is not installed on this host. "
            "Install via: brew install trivy  (macOS) or "
            "apt-get install trivy  (Debian/Ubuntu). "
            "See https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
        )



@dataclass
class TrivyVulnerability:
    """Parsed Trivy vulnerability result."""

    cve_id: str
    severity: str
    title: str
    description: str
    package_name: str
    installed_version: str
    fixed_version: str | None
    published_date: str
    url: str

    def to_dict(self) -> dict:
        return {
            "cve_id": self.cve_id,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "package_name": self.package_name,
            "installed_version": self.installed_version,
            "fixed_version": self.fixed_version,
            "published_date": self.published_date,
            "url": self.url,
        }


@dataclass
class ScanResult:
    """Complete Trivy scan result."""

    image: str
    scan_time: str
    vulnerabilities: list[TrivyVulnerability]
    severity_counts: dict[str, int]
    total: int

    def to_dict(self) -> dict:
        return {
            "image": self.image,
            "scan_time": self.scan_time,
            "total_vulnerabilities": self.total,
            "severity_counts": self.severity_counts,
            "vulnerabilities": [v.to_dict() for v in self.vulnerabilities],
        }


class TrivyService:
    """Trivy CLI-based container image vulnerability scanner.

    Usage:
        service = TrivyService(session)
        result = await service.scan_image("nginx:1.21")
    """

    SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "UNKNOWN": 4}

    def __init__(self, session: AsyncSession):
        self.session = session
        self._trivy_path: str | None = None

    def _check_trivy_installed(self) -> bool:
        """Check if trivy CLI is installed and accessible."""
        if self._trivy_path:
            return True
        try:
            result = subprocess.run(
                ["which", "trivy"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                self._trivy_path = "trivy"
                logger.info("Trivy CLI found in PATH")
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        for alt_path in ["/usr/local/bin/trivy", "/opt/homebrew/bin/trivy"]:
            if os.path.exists(alt_path):
                self._trivy_path = alt_path
                logger.info(f"Trivy CLI found at: {alt_path}")
                return True

        logger.warning(
            "Trivy CLI not found. Install: https://github.com/aquasecurity/trivy"
        )
        return False

    async def _get_cached_scan(self, image: str) -> dict | None:
        """Retrieve cached scan result from the database (if within TTL)."""
        try:
            from sqlalchemy import text

            result = await self.session.execute(
                text(
                    "SELECT scan_result, scanned_at FROM image_scans "
                    "WHERE image = :image AND scanned_at > :cutoff "
                    "ORDER BY scanned_at DESC LIMIT 1"
                ),
                {
                    "image": image,
                    "cutoff": (
                        datetime.now(UTC) - timedelta(hours=SCAN_CACHE_TTL_HOURS)
                    ).isoformat(),
                },
            )
            row = result.fetchone()
            if row:
                cached = json.loads(row[0])
                logger.info(f"Cache hit for image: {image} (scanned at {row[1]})")
                return cached
        except Exception as e:
            logger.debug(f"Cache lookup skipped (table may not exist): {e}")

        return None

    async def _cache_scan_result(self, image: str, result: dict) -> None:
        """Cache scan result to database."""
        try:
            from sqlalchemy import text

            await self.session.execute(
                text(
                    "INSERT INTO image_scans (image, scan_result, scanned_at) "
                    "VALUES (:image, :result, :scanned_at) "
                    "ON CONFLICT(image) DO UPDATE SET "
                    "scan_result = :result2, scanned_at = :scanned_at2"
                ),
                {
                    "image": image,
                    "result": json.dumps(result),
                    "scanned_at": datetime.now(UTC).isoformat(),
                    "result2": json.dumps(result),
                    "scanned_at2": datetime.now(UTC).isoformat(),
                },
            )
            await self.session.commit()
            logger.info(f"Scan result cached for image: {image}")
        except Exception as e:
            logger.warning(f"Failed to cache scan result for {image}: {e}")
            await self.session.rollback()

    def _parse_trivy_json(self, raw_json: dict, image: str) -> ScanResult:
        """Parse Trivy JSON output into structured ScanResult."""
        vulnerabilities: list[TrivyVulnerability] = []

        results = raw_json.get("Results", [])
        for result_block in results:
            for vuln_data in result_block.get("Vulnerabilities", []):
                vulnerabilities.append(
                    TrivyVulnerability(
                        cve_id=vuln_data.get("VulnerabilityID", ""),
                        severity=vuln_data.get("Severity", "UNKNOWN"),
                        title=vuln_data.get("Title", ""),
                        description=vuln_data.get("Description", ""),
                        package_name=vuln_data.get("PkgName", ""),
                        installed_version=vuln_data.get("InstalledVersion", ""),
                        fixed_version=vuln_data.get("FixedVersion"),
                        published_date=vuln_data.get("PublishedDate", ""),
                        url=vuln_data.get("PrimaryURL", ""),
                    )
                )

        vulnerabilities.sort(
            key=lambda v: self.SEVERITY_ORDER.get(v.severity.upper(), 99)
        )

        severity_counts = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
            "UNKNOWN": 0,
        }
        for v in vulnerabilities:
            sev = v.severity.upper()
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return ScanResult(
            image=image,
            scan_time=datetime.now(UTC).isoformat(),
            vulnerabilities=vulnerabilities,
            severity_counts=severity_counts,
            total=len(vulnerabilities),
        )

    async def scan_image(self, image: str) -> dict:
        """Scan a container image for vulnerabilities using Trivy CLI.

        Args:
            image: Container image name with tag (e.g., "nginx:1.21")

        Returns:
            Structured scan result dict with vulnerabilities and severity breakdown

        Raises:
            RuntimeError: If trivy is not installed or scan fails
        """
        # 1. Check cache first
        cached = await self._get_cached_scan(image)
        if cached:
            return cached

        # 2. Check trivy installation
        if not self._check_trivy_installed():
            logger.error(
                "Trivy is not installed on this host; refusing to return mock scan data. "
                "Install Trivy or disable vulnerability scanning. (T1.2)"
            )
            raise TrivyNotInstalledError()


        # 3. Execute trivy scan
        trivy_cmd = self._trivy_path or "trivy"

        try:
            logger.info(f"Starting Trivy scan for image: {image}")

            cmd = [
                trivy_cmd,
                "image",
                "--format",
                "json",
                "--no-progress",
                "--quiet",
                image,
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
            except TimeoutError:
                proc.kill()
                raise RuntimeError(f"Trivy scan timed out for image: {image}")

            if proc.returncode != 0:
                stderr_text = stderr.decode("utf-8", errors="replace")
                logger.error(f"Trivy scan failed for {image}: {stderr_text}")
                raise RuntimeError(
                    f"Trivy scan failed (exit {proc.returncode}): {stderr_text[:500]}"
                )

            # 4. Parse JSON output
            raw_json = json.loads(stdout.decode("utf-8"))
            result = self._parse_trivy_json(raw_json, image)

            # 5. Cache result
            result_dict = result.to_dict()
            await self._cache_scan_result(image, result_dict)

            logger.info(
                f"Trivy scan complete for {image}: "
                f"{result.total} vulnerabilities "
                f"(CRIT:{result.severity_counts['CRITICAL']} "
                f"HIGH:{result.severity_counts['HIGH']} "
                f"MED:{result.severity_counts['MEDIUM']} "
                f"LOW:{result.severity_counts['LOW']})"
            )

            return result_dict

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Trivy JSON output: {e}")
            raise RuntimeError(f"Trivy output parse error: {e}")
        except FileNotFoundError:
            raise RuntimeError(
                f"Trivy command not found at '{trivy_cmd}'. "
                "Install: brew install trivy or apt install trivy"
            )


def get_trivy_service(session: AsyncSession) -> "TrivyService":
    """Factory function to create a TrivyService instance."""
    return TrivyService(session)

