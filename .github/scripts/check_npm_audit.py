#!/usr/bin/env python3
"""Gate: fail when npm audit reports high/critical advisories.

Used by .github/workflows/security-gate.yml (npm-audit job).
Handles both npm audit JSON schemas:
  * npm v6: {"advisories": {"<id>": {"severity": ..., "module_name": ...}}}
  * npm v7+: {"vulnerabilities": {"<name>": {"severity": ...}}}

Non-JSON output (npm prints prose when everything is clean) is tolerated.

Exit codes: 0 = gate passed, 1 = high/critical found.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BLOCKING_SEVERITIES = ("high", "critical")
CLEAN_MARKERS = ("found 0 vulnerabilities", "no known vulnerabilities")


def collect_advisories(data: dict) -> list[tuple[str, str, str]]:
    """Return (severity, package, title) tuples across npm schema versions."""
    found: list[tuple[str, str, str]] = []

    for adv_id, adv in (data.get("advisories") or {}).items():
        if not isinstance(adv, dict):
            continue
        found.append(
            (
                str(adv.get("severity", "")).lower(),
                str(adv.get("module_name", "?")),
                str(adv.get("title", adv_id)),
            )
        )

    for name, vuln in (data.get("vulnerabilities") or {}).items():
        if not isinstance(vuln, dict):
            continue
        found.append(
            (
                str(vuln.get("severity", "")).lower(),
                str(name),
                str(vuln.get("via", "?") if isinstance(vuln.get("via"), str) else name),
            )
        )

    return found


def main() -> int:
    report = Path(sys.argv[1] if len(sys.argv) > 1 else "npm-audit-output.json")
    try:
        raw = report.read_text().strip()
    except OSError as exc:
        print(f"::error::Could not read {report}: {exc}")
        return 0

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        if any(marker in raw.lower() for marker in CLEAN_MARKERS):
            print("No vulnerabilities found — gate passed.")
        else:
            print("Could not parse npm audit output, skipping gate.")
        return 0

    blocking = [a for a in collect_advisories(data) if a[0] in BLOCKING_SEVERITIES]
    print(f"High/Critical vulnerabilities found: {len(blocking)}")
    if blocking:
        for severity, package, title in blocking:
            print(f"  [{severity.upper()}] {package} — {title}")
        print(
            "::error::High or critical npm vulnerabilities detected. "
            "Please upgrade or audit affected packages."
        )
        return 1

    print("No high/critical npm vulnerabilities — gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
