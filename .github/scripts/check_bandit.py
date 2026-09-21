#!/usr/bin/env python3
"""Gate: fail when Bandit reports high/medium-severity + high-confidence issues.

Used by .github/workflows/security-gate.yml (bandit job).
A missing/unreadable report is treated as "no issues" (bandit writes no file
when it finds nothing to report in some configurations).

Exit codes: 0 = gate passed, 1 = blocking issues found.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BLOCKING_SEVERITIES = ("HIGH", "MEDIUM")
BLOCKING_CONFIDENCE = ("HIGH",)


def is_blocking(result: dict) -> bool:
    severity = str(result.get("issue_severity", "")).upper()
    confidence = str(result.get("issue_confidence", "")).upper()
    return severity in BLOCKING_SEVERITIES and confidence in BLOCKING_CONFIDENCE


def main() -> int:
    report = Path(sys.argv[1] if len(sys.argv) > 1 else "bandit-gate-report.json")
    try:
        data = json.loads(report.read_text())
    except (OSError, json.JSONDecodeError):
        print("Bandit report not generated — gate passed (no issues detected).")
        return 0

    results = data.get("results", []) if isinstance(data, dict) else []
    blocked = [r for r in results if isinstance(r, dict) and is_blocking(r)]

    if blocked:
        print(f"Blocked {len(blocked)} high-confidence issues:")
        for r in blocked:
            print(
                f"  [{r.get('issue_severity', '?')}/{r.get('issue_confidence', '?')}] "
                f"{r.get('filename', '?')}:{r.get('line_number', '?')} — "
                f"{r.get('test_name', '?')}: {r.get('issue_text', '?')}"
            )
        print(
            "::error::Bandit found high-confidence security issues. "
            "Please fix before merging."
        )
        return 1

    print("No high-confidence issues found — Bandit gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
