"""Unit tests for the Trivy image-scanning service (subprocess fully mocked)."""

import json
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from services.integration.trivy_service import (
    ScanResult,
    TrivyService,
    TrivyVulnerability,
    get_trivy_service,
)

pytestmark = [pytest.mark.unit]


def make_session() -> AsyncMock:
    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = Mock(fetchone=Mock(return_value=None))
    return session


def vuln(severity="HIGH", cve="CVE-2024-0001", pkg="openssl") -> dict:
    return {
        "VulnerabilityID": cve,
        "Severity": severity,
        "Title": f"Title for {cve}",
        "Description": "desc",
        "PkgName": pkg,
        "InstalledVersion": "1.0.0",
        "FixedVersion": "1.0.1",
        "PublishedDate": "2024-01-01T00:00:00Z",
        "PrimaryURL": f"https://nvd.example/{cve}",
    }


def trivy_json(*vulns: dict) -> dict:
    return {"Results": [{"Vulnerabilities": list(vulns)}]}


def make_proc(returncode=0, stdout=b"", stderr=b"", error=None) -> MagicMock:
    proc = MagicMock()
    if error is not None:
        proc.communicate = AsyncMock(side_effect=error)
    else:
        proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    proc.kill = MagicMock()
    return proc


class TestDataclasses:
    def test_vulnerability_to_dict(self):
        v = TrivyVulnerability(
            cve_id="CVE-1",
            severity="HIGH",
            title="t",
            description="d",
            package_name="p",
            installed_version="1",
            fixed_version="2",
            published_date="2024-01-01",
            url="https://nvd.example/CVE-1",
        )
        d = v.to_dict()
        assert d["cve_id"] == "CVE-1"
        assert d["fixed_version"] == "2"

    def test_scan_result_to_dict(self):
        v = TrivyVulnerability(
            cve_id="CVE-1",
            severity="LOW",
            title="t",
            description="d",
            package_name="p",
            installed_version="1",
            fixed_version=None,
            published_date="",
            url="",
        )
        result = ScanResult(
            image="img",
            scan_time="now",
            vulnerabilities=[v],
            severity_counts={"LOW": 1},
            total=1,
        )
        d = result.to_dict()
        assert d["image"] == "img"
        assert d["total_vulnerabilities"] == 1
        assert d["vulnerabilities"][0]["fixed_version"] is None


class TestParseTrivyJson:
    def setup_method(self):
        self.service = TrivyService(make_session())

    def test_sorts_by_severity_and_counts(self):
        result = self.service._parse_trivy_json(
            trivy_json(
                vuln(severity="LOW", cve="CVE-L"),
                vuln(severity="CRITICAL", cve="CVE-C"),
                vuln(severity="HIGH", cve="CVE-H"),
                vuln(severity="MEDIUM", cve="CVE-M"),
                vuln(severity="CRITICAL", cve="CVE-C2"),
            ),
            "nginx:1.21",
        )
        assert [v.cve_id for v in result.vulnerabilities] == [
            "CVE-C",
            "CVE-C2",
            "CVE-H",
            "CVE-M",
            "CVE-L",
        ]
        assert result.severity_counts["CRITICAL"] == 2
        assert result.severity_counts["HIGH"] == 1
        assert result.severity_counts["MEDIUM"] == 1
        assert result.severity_counts["LOW"] == 1
        assert result.total == 5

    def test_unknown_severity_bucketed(self):
        result = self.service._parse_trivy_json(
            trivy_json(vuln(severity="weird", cve="CVE-W")),
            "img",
        )
        assert result.severity_counts["WEIRD"] == 1
        assert result.total == 1

    def test_empty_results(self):
        result = self.service._parse_trivy_json({"Results": []}, "img")
        assert result.total == 0
        assert result.vulnerabilities == []

    def test_missing_vulnerabilities_key(self):
        result = self.service._parse_trivy_json({"Results": [{}]}, "img")
        assert result.total == 0


class TestCheckTrivyInstalled:
    def test_cached_path_short_circuits(self):
        service = TrivyService(make_session())
        service._trivy_path = "/custom/trivy"
        assert service._check_trivy_installed() is True

    def test_found_in_path(self, monkeypatch):
        monkeypatch.setattr(
            "subprocess.run",
            Mock(return_value=Mock(returncode=0)),
        )
        service = TrivyService(make_session())
        assert service._check_trivy_installed() is True
        assert service._trivy_path == "trivy"

    def test_falls_back_to_known_alt_paths(self, monkeypatch):
        monkeypatch.setattr(
            "subprocess.run",
            Mock(return_value=Mock(returncode=1)),
        )
        monkeypatch.setattr(
            "os.path.exists", lambda p: p == "/opt/homebrew/bin/trivy"
        )
        service = TrivyService(make_session())
        assert service._check_trivy_installed() is True
        assert service._trivy_path == "/opt/homebrew/bin/trivy"

    def test_not_installed(self, monkeypatch):
        monkeypatch.setattr(
            "subprocess.run",
            Mock(return_value=Mock(returncode=1)),
        )
        monkeypatch.setattr("os.path.exists", lambda p: False)
        service = TrivyService(make_session())
        assert service._check_trivy_installed() is False


class TestScanImage:
    async def test_returns_cached_scan_within_ttl(self):
        session = make_session()
        cached = {"image": "nginx:1.21", "total_vulnerabilities": 3}
        session.execute.return_value = Mock(
            fetchone=Mock(return_value=(json.dumps(cached), "2026-01-01T00:00:00Z"))
        )
        service = TrivyService(session)

        result = await service.scan_image("nginx:1.21")

        assert result == cached

    async def test_refuses_mock_data_when_trivy_missing(self, monkeypatch):
        """T1.2 contract: a missing scanner must surface as an error.

        Returning fabricated CVE results from a security scanner misleads
        analysts, so the service refuses instead of degrading to mock data.
        """
        from services.integration.trivy_service import TrivyNotInstalledError

        session = make_session()
        service = TrivyService(session)
        monkeypatch.setattr(
            service, "_check_trivy_installed", Mock(return_value=False)
        )

        with pytest.raises(TrivyNotInstalledError):
            await service.scan_image("nginx:1.21")

        # No scan result may be cached from a refused scan
        assert session.commit.await_count == 0

    async def test_successful_scan_parses_and_caches(self, monkeypatch):

        session = make_session()
        service = TrivyService(session)
        service._trivy_path = "trivy"
        payload = json.dumps(
            trivy_json(vuln(severity="HIGH"), vuln(severity="LOW"))
        ).encode()
        proc = make_proc(returncode=0, stdout=payload)
        monkeypatch.setattr(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
        )

        result = await service.scan_image("nginx:1.21")

        assert result["total_vulnerabilities"] == 2
        assert result["severity_counts"]["HIGH"] == 1
        proc.communicate.assert_awaited_once()
        session.commit.assert_awaited()

    async def test_nonzero_exit_raises_with_stderr(self, monkeypatch):

        service = TrivyService(make_session())
        service._trivy_path = "trivy"
        proc = make_proc(returncode=1, stderr=b"scan boom")
        monkeypatch.setattr(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
        )

        with pytest.raises(RuntimeError, match="Trivy scan failed \\(exit 1\\)"):
            await service.scan_image("nginx:1.21")

    async def test_timeout_kills_process_and_raises(self, monkeypatch):

        service = TrivyService(make_session())
        service._trivy_path = "trivy"
        proc = make_proc(error=TimeoutError())
        monkeypatch.setattr(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
        )

        with pytest.raises(RuntimeError, match="timed out"):
            await service.scan_image("nginx:1.21")
        proc.kill.assert_called_once()

    async def test_invalid_json_output_raises(self, monkeypatch):

        service = TrivyService(make_session())
        service._trivy_path = "trivy"
        proc = make_proc(returncode=0, stdout=b"not json")
        monkeypatch.setattr(
            "asyncio.create_subprocess_exec", AsyncMock(return_value=proc)
        )

        with pytest.raises(RuntimeError, match="parse error"):
            await service.scan_image("nginx:1.21")

    async def test_missing_binary_raises(self, monkeypatch):

        service = TrivyService(make_session())
        service._trivy_path = "trivy"
        monkeypatch.setattr(
            "asyncio.create_subprocess_exec",
            AsyncMock(side_effect=FileNotFoundError()),
        )

        with pytest.raises(RuntimeError, match="Trivy command not found"):
            await service.scan_image("nginx:1.21")


def test_get_trivy_service_factory():
    session = make_session()
    assert isinstance(get_trivy_service(session), TrivyService)
