#!/usr/bin/env python3
"""Gate: fail when pip-audit reports high/critical vulnerabilities.

Used by .github/workflows/security-gate.yml (pip-audit job).
Handles both pip-audit JSON schemas:
  * modern: {"dependencies": [{"name": ..., "vulnerabilities": [...]}]}
  * legacy: [{"name": ..., "vulnerabilities": [...]}]

Exit codes: 0 = gate passed, 1 = high/critical found, 2 = report unreadable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SEVERITY_PREFIXES = ("GHSA-", "CVE-", "RUSTSEC-", "PYSEC-")


def load_dependencies(path: Path) -> list[dict]:
    """Return the dependency list from either supported report shape."""
    data = json.loads(path.read_text())
    if isinstance(data, dict):
        deps = data.get("dependencies", [])
    else:
        deps = data
    return [dep for dep in deps if isinstance(dep, dict)]


def count_serious(deps: list[dict]) -> tuple[int, list[str]]:
    """Count vulnerabilities carrying a serious advisory alias."""
    count = 0
    details: list[str] = []
    for dep in deps:
        for vuln in dep.get("vulnerabilities", []):
            if not isinstance(vuln, dict):
                continue
            aliases = vuln.get("aliases", [])
            if any(str(a).startswith(SEVERITY_PREFIXES) for a in aliases):
                count += 1
                details.append(
                    f"  {dep.get('name', '?')} {dep.get('version', '?')} — "
                    f"{', '.join(aliases) or vuln.get('id', '?')}"
                )
    return count, details


def main() -> int:
    report = Path(sys.argv[1] if len(sys.argv) > 1 else "pip-audit-report.json")
    try:
        deps = load_dependencies(report)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"::error::Could not parse {report}: {exc}")
        return 2

    high_critical, details = count_serious(deps)
    print(f"High/Critical vulnerabilities found: {high_critical}")
    if high_critical:
        for line in details:
            print(line)
        print(
            "::error::High or critical vulnerabilities detected. "
            "Please upgrade affected dependencies."
        )
        return 1
    print("No high/critical vulnerabilities — gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
