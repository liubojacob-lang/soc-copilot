"""Regression tests for .github/scripts/check_pip_audit.py.

The gate once read only the legacy "vulnerabilities" key while pip-audit
>= 2.8 emits "vulns", silently passing real advisories (2026-11-21: 32
advisories were counted as zero). These tests pin both schema shapes.
"""

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "check_pip_audit.py"

_spec = importlib.util.spec_from_file_location("check_pip_audit", SCRIPT)
check_pip_audit = importlib.util.module_from_spec(_spec)
assert _spec and _spec.loader
_spec.loader.exec_module(check_pip_audit)


def _vuln(aliases):
    return {
        "id": "ADV-1",
        "fix_versions": ["1.0.1"],
        "aliases": aliases,
        "description": "test advisory",
    }


def test_count_serious_reads_modern_vulns_key():
    deps = [{"name": "aiohttp", "version": "3.14.3", "vulns": [_vuln(["CVE-2026-111064"])]}]
    count, details = check_pip_audit.count_serious(deps)
    assert count == 1
    assert "aiohttp" in details[0]


def test_count_serious_reads_legacy_vulnerabilities_key():
    deps = [
        {
            "name": "pkg",
            "version": "1.0",
            "vulnerabilities": [_vuln(["GHSA-1234-abcd"])],
        }
    ]
    count, _ = check_pip_audit.count_serious(deps)
    assert count == 1


def test_count_serious_ignores_advisories_without_serious_aliases():
    deps = [{"name": "pkg", "version": "1.0", "vulns": [_vuln([])]}]
    count, _ = check_pip_audit.count_serious(deps)
    assert count == 0


def test_count_serious_tolerates_missing_keys():
    deps = [{"name": "pkg", "version": "1.0"}]
    count, _ = check_pip_audit.count_serious(deps)
    assert count == 0
