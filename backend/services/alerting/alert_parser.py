"""
Alert Parser — Parse CEF, Syslog, JSON, and CSV alert formats.

Supports format auto-detection and normalization to the standard
SecurityAlert schema used by AlertCRUDService.create_alert().
"""

import csv
import io
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Severity mappings
# ---------------------------------------------------------------------------

# Syslog PRI severity → human-readable label
SYSLOG_SEVERITY_MAP: dict[int, str] = {
    0: "critical",  # Emergency
    1: "critical",  # Alert
    2: "critical",  # Critical
    3: "high",  # Error
    4: "high",  # Warning
    5: "medium",  # Notice
    6: "low",  # Informational
    7: "info",  # Debug
}

# CEF severity (0-10) → our severity label
CEF_SEVERITY_MAP: dict[int, str] = {
    **dict.fromkeys(range(9, 11), "critical"),
    **dict.fromkeys(range(7, 9), "high"),
    **dict.fromkeys(range(4, 7), "medium"),
    **dict.fromkeys(range(1, 4), "low"),
    **dict.fromkeys(range(0, 1), "info"),
}


# ---------------------------------------------------------------------------
# Parsed result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ParsedAlert:
    """Normalised alert produced by any parser."""

    source: str = "manual"
    event_type: str = "unknown"
    severity: str = "info"
    title: str = ""
    description: str = ""
    source_ip: str | None = None
    destination_ip: str | None = None
    protocol: str | None = None
    agent_name: str | None = None
    agent_id: str | None = None
    agent_ip: str | None = None
    rule_id: str | None = None
    rule_level: int | None = None
    full_log: str | None = None
    raw_data: dict[str, Any] | None = None
    tags: list[str] = field(default_factory=list)
    event_timestamp: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict suitable for AlertCreate."""
        return {
            "source": self.source,
            "event_type": self.event_type,
            "severity": self.severity,
            "title": self.title,
            "description": self.description,
            "source_ip": self.source_ip,
            "destination_ip": self.destination_ip,
            "protocol": self.protocol,
            "agent_name": self.agent_name,
            "agent_id": self.agent_id,
            "agent_ip": self.agent_ip,
            "rule_id": self.rule_id,
            "rule_level": self.rule_level,
            "full_log": self.full_log,
            "raw_data": self.raw_data,
            "tags": self.tags,
        }


# ---------------------------------------------------------------------------
# Alert Parser
# ---------------------------------------------------------------------------


class AlertParser:
    """Parse security alerts in CEF, Syslog, JSON, and CSV formats."""

    # CEF header pattern: CEF:Version|Device Vendor|Device Product|Device Version|...
    # We split on '|' up to the Extension field
    CEF_PATTERN = re.compile(
        r"^CEF:(\d+)\|"  # CEF:Version|
        r"([^|]*)\|"  # Device Vendor
        r"([^|]*)\|"  # Device Product
        r"([^|]*)\|"  # Device Version
        r"([^|]*)\|"  # Signature ID
        r"([^|]*)\|"  # Name
        r"([^|]*)\|"  # Severity
        r"(.*)$"  # Extension
    )

    # Syslog header: <PRI>TIMESTAMP HOSTNAME MSG
    SYSLOG_PATTERN = re.compile(
        r"^<(\d{1,3})>"  # <PRI>
        r"(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})"  # Timestamp (e.g. "Jan  1 12:00:00")
        r"\s+(\S+)"  # Hostname
        r"\s+(.+)$"  # Message
    )

    # IPv4 regex for extracting IPs from raw text
    IPV4_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

    # ── Format detection ──────────────────────────────────────────

    @staticmethod
    def detect_format(text: str) -> str:
        """Detect the format of a raw alert string.

        Returns one of: 'cef', 'syslog', 'json', 'csv', 'raw'
        """
        stripped = text.strip()
        if not stripped:
            return "raw"

        if stripped.startswith("CEF:"):
            return "cef"
        if stripped.startswith("<") and AlertParser.SYSLOG_PATTERN.match(stripped):
            return "syslog"
        try:
            json.loads(stripped)
            return "json"
        except (json.JSONDecodeError, ValueError):
            pass
        # Heuristic: if it has commas and multiple quoted fields, treat as CSV
        if "," in stripped and ('"' in stripped or stripped.count(",") >= 2):
            return "csv"
        return "raw"

    # ── CEF Parser ────────────────────────────────────────────────

    @staticmethod
    def parse_cef(line: str) -> ParsedAlert:
        """Parse a CEF (Common Event Format) log line.

        CEF format:
            CEF:Version|Device Vendor|Device Product|Device Version|
            Signature ID|Name|Severity|Extension

        Extension is key=value pairs separated by spaces.
        """
        match = AlertParser.CEF_PATTERN.match(line.strip())
        if not match:
            raise ValueError(f"Invalid CEF format: {line[:120]}...")

        version, vendor, product, dev_version, sig_id, name, sev_str, extension = (
            match.groups()
        )

        # Parse severity
        try:
            sev_num = int(sev_str)
            severity = CEF_SEVERITY_MAP.get(sev_num, "info")
        except (ValueError, TypeError):
            severity = "info"

        # Parse extension key=value pairs
        ext_pairs = AlertParser._parse_cef_extension(extension)

        # Extract IPs
        src_ip = (
            ext_pairs.get("src")
            or ext_pairs.get("spt")
            or ext_pairs.get("sourceAddress")
        )
        dst_ip = (
            ext_pairs.get("dst")
            or ext_pairs.get("dpt")
            or ext_pairs.get("destinationAddress")
        )

        # Extract agent info
        agent_name = ext_pairs.get("dhost") or ext_pairs.get("shost") or vendor
        agent_ip = ext_pairs.get("dvc") or ext_pairs.get("dvchost")

        # Build title
        title = name or f"CEF Alert from {vendor}/{product}"
        description = f"Product: {vendor}/{product} v{dev_version} | Signature: {sig_id} | Extension: {extension[:200]}"

        # Parse timestamp
        event_ts = AlertParser._parse_cef_timestamp(
            ext_pairs.get("rt") or ext_pairs.get("start") or ext_pairs.get("end")
        )

        return ParsedAlert(
            source=f"cef-{vendor.lower()}" if vendor else "cef",
            event_type=sig_id or "cef_event",
            severity=severity,
            title=title,
            description=description,
            source_ip=src_ip,
            destination_ip=dst_ip,
            protocol=ext_pairs.get("proto") or ext_pairs.get("app"),
            agent_name=agent_name,
            agent_ip=agent_ip,
            rule_id=sig_id,
            full_log=line.strip(),
            raw_data={
                "cef_header": dict(match.groupdict().items()),
                "extensions": ext_pairs,
            },
            event_timestamp=event_ts,
        )

    @staticmethod
    def _parse_cef_extension(ext_str: str) -> dict[str, str]:
        """Parse CEF extension key=value pairs, handling escapes."""
        pairs: dict[str, str] = {}
        if not ext_str:
            return pairs

        # CEF extension: key=value (delimited by space, but values can contain \= and \s)
        # Simplified parser: split on space, then split on first =
        for token in ext_str.strip().split():
            if "=" in token:
                key, _, value = token.partition("=")
                # Unescape CEF escapes
                value = (
                    value.replace("\\=", "=").replace("\\|", "|").replace("\\\\", "\\")
                )
                pairs[key] = value

        return pairs

    @staticmethod
    def _parse_cef_timestamp(ts_str: str | None) -> datetime | None:
        """Parse CEF timestamp (milliseconds since epoch)."""
        if not ts_str:
            return None
        try:
            ts = int(ts_str)
            # Could be milliseconds or seconds
            if ts > 1_000_000_000_000:
                ts = ts // 1000
            return datetime.fromtimestamp(ts, tz=UTC)
        except (ValueError, OSError):
            return None

    # ── Syslog Parser ─────────────────────────────────────────────

    @staticmethod
    def parse_syslog(line: str) -> ParsedAlert:
        """Parse a Syslog (RFC 3164) log line.

        Format: <PRI>TIMESTAMP HOSTNAME MSG
        PRI = facility * 8 + severity
        """
        match = AlertParser.SYSLOG_PATTERN.match(line.strip())
        if not match:
            # Try more lenient parsing
            return AlertParser._parse_syslog_fallback(line)

        pri_str, ts_str, hostname, message = match.groups()

        # Parse PRI
        pri = int(pri_str)
        facility = pri >> 3
        severity_num = pri & 0x07
        severity = SYSLOG_SEVERITY_MAP.get(severity_num, "info")

        # Detect event type from message
        event_type = AlertParser._detect_syslog_event_type(message, facility)

        # Extract IPs from message
        ips = AlertParser.IPV4_PATTERN.findall(message)
        src_ip = ips[0] if ips else None
        dst_ip = ips[1] if len(ips) > 1 else None

        # Build a title from the first line of the message
        title = message.split(":")[0].strip() if ":" in message else message[:120]

        return ParsedAlert(
            source=f"syslog-facility{facility}",
            event_type=event_type,
            severity=severity,
            title=title,
            description=message[:500],
            source_ip=src_ip,
            destination_ip=dst_ip,
            agent_name=hostname,
            full_log=line.strip(),
            raw_data={
                "facility": facility,
                "severity_num": severity_num,
                "hostname": hostname,
                "syslog_timestamp": ts_str,
            },
        )

    @staticmethod
    def _parse_syslog_fallback(line: str) -> ParsedAlert:
        """Fallback parser for malformed syslog lines."""
        stripped = line.strip()

        # Try <PRI> only
        pri_match = re.match(r"^<(\d{1,3})>(.*)", stripped)
        if pri_match:
            pri = int(pri_match.group(1))
            severity_num = pri & 0x07
            severity = SYSLOG_SEVERITY_MAP.get(severity_num, "info")
            message = pri_match.group(2)
        else:
            severity = "info"
            message = stripped

        ips = AlertParser.IPV4_PATTERN.findall(message)
        event_type = AlertParser._detect_syslog_event_type(message)

        return ParsedAlert(
            source="syslog",
            event_type=event_type,
            severity=severity,
            title=message.split(":")[0].strip() if ":" in message else message[:120],
            description=message[:500],
            source_ip=ips[0] if ips else None,
            destination_ip=ips[1] if len(ips) > 1 else None,
            full_log=stripped,
            raw_data={"message": message},
        )

    @staticmethod
    def _detect_syslog_event_type(message: str, facility: int | None = None) -> str:
        """Detect event type from syslog message content."""
        msg_lower = message.lower()

        # Security-related patterns
        if any(
            kw in msg_lower
            for kw in [
                "failed password",
                "authentication failure",
                "invalid user",
                "break-in",
            ]
        ):
            return "authentication_failure"
        if any(
            kw in msg_lower
            for kw in ["accepted password", "successful login", "session opened"]
        ):
            return "authentication_success"
        if any(kw in msg_lower for kw in ["sudo", "su:", "privilege"]):
            return "privilege_escalation"
        if any(
            kw in msg_lower
            for kw in ["firewall", "iptables", "denied", "blocked", "drop"]
        ):
            return "firewall"
        if any(kw in msg_lower for kw in ["segfault", "oops", "kernel panic", "bug"]):
            return "system_error"
        if any(kw in msg_lower for kw in ["cron", "job", "schedule"]):
            return "cron"
        if any(kw in msg_lower for kw in ["dhcp", "dns", "ntp"]):
            return "network_service"

        # Facility-based
        if facility is not None:
            if facility == 4:  # auth
                return "authentication"
            if facility == 10:  # security/authorization
                return "authorization"
            if facility == 0:  # kernel
                return "kernel"
            if facility == 1:  # user
                return "user"

        return "syslog"

    # ── JSON Parser ────────────────────────────────────────────────

    @staticmethod
    def parse_json(payload: dict | str) -> ParsedAlert:
        """Parse and normalize a JSON alert payload.

        Accepts either a dict or a JSON string. Tries to map common
        field names (e.g. 'src_ip' / 'source_ip' / 'src') to the
        standard schema.
        """
        if isinstance(payload, str):
            payload = json.loads(payload)

        # Normalize field names: map common variants to our schema
        severity = AlertParser._normalize_severity(
            payload.get("severity")
            or payload.get("level")
            or payload.get("priority")
            or "info"
        )

        title = (
            payload.get("title")
            or payload.get("name")
            or payload.get("event")
            or payload.get("message")
            or payload.get("summary")
            or "JSON Alert"
        )
        description = (
            payload.get("description")
            or payload.get("detail")
            or payload.get("message")
            or payload.get("summary")
            or ""
        )

        return ParsedAlert(
            source=payload.get("source") or "json",
            event_type=payload.get("event_type")
            or payload.get("type")
            or payload.get("category")
            or "json_event",
            severity=severity,
            title=str(title),
            description=str(description)[:1000] if description else "",
            source_ip=(
                payload.get("source_ip")
                or payload.get("src_ip")
                or payload.get("src")
                or payload.get("sourceAddress")
            ),
            destination_ip=(
                payload.get("destination_ip")
                or payload.get("dst_ip")
                or payload.get("dst")
                or payload.get("dest")
                or payload.get("destinationAddress")
            ),
            protocol=payload.get("protocol") or payload.get("proto"),
            agent_name=(
                payload.get("agent_name")
                or payload.get("hostname")
                or payload.get("host")
                or payload.get("computer")
            ),
            agent_ip=payload.get("agent_ip") or payload.get("host_ip"),
            rule_id=payload.get("rule_id")
            or payload.get("rule")
            or payload.get("signature_id"),
            rule_level=payload.get("rule_level") or payload.get("level"),
            full_log=json.dumps(payload, ensure_ascii=False),
            raw_data=payload,
            tags=payload.get("tags") if isinstance(payload.get("tags"), list) else None,
        )

    @staticmethod
    def _normalize_severity(value: Any) -> str:
        """Normalize severity value to one of: critical, high, medium, low, info."""
        if isinstance(value, int | float):
            sev_num = int(value)
            if sev_num >= 9:
                return "critical"
            if sev_num >= 7:
                return "high"
            if sev_num >= 4:
                return "medium"
            if sev_num >= 2:
                return "low"
            return "info"

        if isinstance(value, str):
            v = value.lower().strip()
            if v in {"critical", "emergency", "fatal", "alert"}:
                return "critical"
            if v in {"high", "error", "err"}:
                return "high"
            if v in {"medium", "warning", "warn", "notice"}:
                return "medium"
            if v in {"low", "minor"}:
                return "low"
            return "info"

        return "info"

    # ── CSV Parser ─────────────────────────────────────────────────

    @staticmethod
    def parse_csv(content: str, has_header: bool = True) -> list[ParsedAlert]:
        """Parse CSV alert data, returning a list of ParsedAlert objects.

        The CSV should have columns matching the ParsedAlert schema.
        Automatically detects delimiter (comma, tab, or pipe).
        """
        # Detect delimiter
        sample = content[:2048]
        delimiter = ","
        if "\t" in sample and sample.count("\t") >= sample.count(","):
            delimiter = "\t"
        elif "|" in sample and sample.count("|") >= sample.count(","):
            delimiter = "|"

        reader = csv.reader(io.StringIO(content), delimiter=delimiter)

        rows = list(reader)
        if not rows:
            return []

        # Determine if header is present
        if has_header:
            header = [h.strip().lower() for h in rows[0]]
            data_rows = rows[1:]
        else:
            # Auto-detect: treat as header only if typical column names appear
            first_row = [h.strip().lower() for h in rows[0]]
            header_keywords = {
                "title",
                "severity",
                "source",
                "event_type",
                "description",
                "timestamp",
            }
            if header_keywords & set(first_row):
                header = first_row
                data_rows = rows[1:]
            else:
                # No header – use positional mapping
                header = [
                    "title",
                    "severity",
                    "source",
                    "event_type",
                    "description",
                    "source_ip",
                    "destination_ip",
                    "agent_name",
                    "full_log",
                ]
                data_rows = rows

        alerts: list[ParsedAlert] = []
        for row in data_rows:
            if not row or all(c.strip() == "" for c in row):
                continue

            row_dict = AlertParser._csv_row_to_dict(header, row)
            alerts.append(AlertParser._csv_to_parsed(row_dict))

        return alerts

    @staticmethod
    def _csv_row_to_dict(header: list[str], row: list[str]) -> dict[str, str]:
        """Map a CSV row to a dict using header names."""
        result: dict[str, str] = {}
        for i, h in enumerate(header):
            if i < len(row):
                result[h.strip().lower()] = row[i].strip()
        return result

    @staticmethod
    def _csv_to_parsed(row: dict[str, str]) -> ParsedAlert:
        """Convert a CSV row dict to a ParsedAlert."""
        severity = AlertParser._normalize_severity(row.get("severity", "info"))

        return ParsedAlert(
            source=row.get("source", "csv"),
            event_type=row.get("event_type", row.get("type", "csv_event")),
            severity=severity,
            title=row.get("title", row.get("name", "CSV Alert")),
            description=row.get(
                "description", row.get("detail", row.get("message", ""))
            )[:1000],
            source_ip=row.get("source_ip") or row.get("src_ip") or row.get("src"),
            destination_ip=row.get("destination_ip")
            or row.get("dst_ip")
            or row.get("dst"),
            protocol=row.get("protocol") or row.get("proto"),
            agent_name=row.get("agent_name") or row.get("host") or row.get("hostname"),
            agent_ip=row.get("agent_ip") or row.get("host_ip"),
            rule_id=row.get("rule_id") or row.get("rule"),
            rule_level=(
                int(row["rule_level"]) if row.get("rule_level", "").isdigit() else None
            ),
            full_log=row.get("full_log") or row.get("raw") or row.get("log"),
            raw_data=row,
        )

    # ── Batch parse ────────────────────────────────────────────────

    @classmethod
    def parse_batch(cls, content: str, fmt: str = "auto") -> list[ParsedAlert]:
        """Parse a batch of alerts from multiline content.

        Args:
            content: Raw alert content (multiple lines for CEF/syslog,
                     JSON array, or CSV)
            fmt: Format hint – "auto", "cef", "syslog", "json", "csv"

        Returns:
            List of normalized ParsedAlert objects
        """
        if fmt == "auto":
            fmt = AlertParser.detect_format(content.split("\n")[0])

        if fmt == "json":
            # Try JSON array first, then JSON lines
            stripped = content.strip()
            try:
                data = json.loads(stripped)
                if isinstance(data, list):
                    return [cls.parse_json(item) for item in data]
                return [cls.parse_json(data)]
            except json.JSONDecodeError:
                # JSON lines (one JSON object per line)
                alerts: list[ParsedAlert] = []
                for line in stripped.split("\n"):
                    line = line.strip()
                    if line:
                        try:
                            alerts.append(cls.parse_json(line))
                        except (json.JSONDecodeError, ValueError):
                            continue
                return alerts

        if fmt == "csv":
            return cls.parse_csv(content)

        # CEF / Syslog / Raw — one alert per line
        alerts: list[ParsedAlert] = []
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                line_fmt = (
                    "auto" if fmt in ("cef", "syslog") else cls.detect_format(line)
                )
                if line_fmt == "cef":
                    alerts.append(cls.parse_cef(line))
                elif line_fmt == "syslog":
                    alerts.append(cls.parse_syslog(line))
                elif line_fmt == "json":
                    alerts.append(cls.parse_json(line))
                else:
                    # Raw fallback
                    alerts.append(
                        ParsedAlert(
                            source="raw",
                            event_type="unknown",
                            severity="info",
                            title=line[:120],
                            full_log=line,
                        )
                    )
            except Exception:
                # Skip lines that can't be parsed
                continue
        return alerts

    # ── Single parse ───────────────────────────────────────────────

    @classmethod
    def parse_single(cls, content: str, fmt: str = "auto") -> ParsedAlert:
        """Parse a single alert and return exactly one ParsedAlert.

        Raises ValueError if parsing fails.
        """
        if fmt == "auto":
            fmt = cls.detect_format(content.split("\n")[0])

        if fmt == "cef":
            return cls.parse_cef(content.split("\n")[0])
        if fmt == "syslog":
            return cls.parse_syslog(content.split("\n")[0])
        if fmt == "json":
            return cls.parse_json(content)
        if fmt == "csv":
            results = cls.parse_csv(content)
            if results:
                return results[0]
            raise ValueError("No alerts found in CSV content")

        raise ValueError(f"Unsupported format: {fmt}")
