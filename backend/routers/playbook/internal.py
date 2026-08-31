"""Internal API endpoints used by playbook DAG nodes during execution.

These endpoints provide IOC normalization, extraction, mock blocklisting,
report generation, and case-system integration for playbook nodes.

Extracted from routers/playbook_definitions.py (v0.9.0 refactor).
"""

import re
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from core.logger import get_logger
from dependencies.auth import get_current_user
from models.user import UserModel

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/playbook-definitions", tags=["playbook-internal"])

# ═══════════════════════════════════════════════════════════════════════════
# Request / Response Models
# ═══════════════════════════════════════════════════════════════════════════


class NormalizeRequest(BaseModel):
    ioc: str
    ioc_type: str = "auto"


class NormalizeResponse(BaseModel):
    status: str
    original_ioc: str
    normalized_ioc: str
    normalized_type: str
    is_valid: bool


class ExtractIOCsRequest(BaseModel):
    otx_result: dict
    case_id: str = ""


class ExtractIOCsResponse(BaseModel):
    status: str
    total_extracted: int
    extracted_iocs: dict
    summary: dict


class GenerateReportRequest(BaseModel):
    case_id: str
    ioc: str
    ioc_type: str
    alert_source: str = "email-gateway"
    severity: str = "medium"
    reporter: str = "soc@company.com"
    otx_result: dict = {}
    secondary_iocs: dict = {}
    action_result: dict = {}
    note: str = ""


class GenerateReportResponse(BaseModel):
    status: str
    report_id: str
    case_id: str
    markdown: str
    report_url: str
    threat_level: str


class CaseUpdateRequest(BaseModel):
    case_id: str
    status: str
    reason: str = ""
    playbook_run_id: str = ""
    report_url: str = ""


class CaseUpdateResponse(BaseModel):
    status: str
    case_id: str
    updated_at: str
    message: str


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════


@router.post("/internal/normalize", response_model=NormalizeResponse)
async def internal_normalize(
    data: NormalizeRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Normalize IOC input."""
    ioc = data.ioc.strip().lower()
    ioc_type = data.ioc_type

    # Auto-detect if needed
    if ioc_type == "auto":
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ioc):
            ioc_type = "ip"
        elif ioc.startswith(("http://", "https://")):
            ioc_type = "url"
        elif (
            re.match(r"^[a-f0-9]{32}$", ioc)
            or re.match(r"^[a-f0-9]{40}$", ioc)
            or re.match(r"^[a-f0-9]{64}$", ioc)
        ):
            ioc_type = "hash"
        else:
            ioc_type = "domain"

    # Normalize
    normalized = ioc
    if ioc_type == "url":
        normalized = ioc.rstrip("/").split("#")[0]
    elif ioc_type == "domain":
        if normalized.startswith("www."):
            normalized = normalized[4:]

    is_valid = bool(normalized)

    return NormalizeResponse(
        status="success" if is_valid else "invalid",
        original_ioc=data.ioc,
        normalized_ioc=normalized,
        normalized_type=ioc_type,
        is_valid=is_valid,
    )


@router.post("/internal/extract-iocs", response_model=ExtractIOCsResponse)
async def internal_extract_iocs(
    data: ExtractIOCsRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Extract secondary IOCs from OTX result."""
    ti_result = data.otx_result
    extracted = {"ips": [], "domains": [], "urls": [], "hashes": [], "emails": []}

    if isinstance(ti_result, dict):
        pulses = ti_result.get("matches", [])
        for pulse in pulses:
            text = f"{pulse.get('name', '')} {pulse.get('description', '')}"

            # Extract IPs
            ips = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
            extracted["ips"].extend(ips)

            # Extract domains
            domains = re.findall(
                r"\b(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b", text
            )
            extracted["domains"].extend(domains)

            # Extract hashes
            hashes = re.findall(
                r"\b[a-fA-F0-9]{32}\b|\b[a-fA-F0-9]{40}\b|\b[a-fA-F0-9]{64}\b", text
            )
            extracted["hashes"].extend(hashes)

    # Deduplicate
    for key in extracted:
        extracted[key] = list(set(extracted[key]))

    total = sum(len(v) for v in extracted.values())

    return ExtractIOCsResponse(
        status="success",
        total_extracted=total,
        extracted_iocs=extracted,
        summary={k: len(v) for k, v in extracted.items()},
    )


@router.post("/internal/generate-report", response_model=GenerateReportResponse)
async def internal_generate_report(
    data: GenerateReportRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Generate markdown incident response report."""
    ti_result = data.otx_result if isinstance(data.otx_result, dict) else {}
    threat_score = ti_result.get("threat_score", 0)
    is_malicious = threat_score >= 3
    threat_level = "high" if is_malicious else "low"

    # Generate markdown
    lines = [
        f"# Incident Response Report: {data.case_id}",
        "",
        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
        "## Executive Summary",
        "",
        f"{'⚠️ **THREAT CONFIRMED**' if is_malicious else 'ℹ️ **LOW CONFIDENCE**'} - IOC `{data.ioc}`",
        "",
        "## IOC Details",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Case ID** | {data.case_id} |",
        f"| **IOC** | `{data.ioc}` |",
        f"| **Type** | {data.ioc_type} |",
        f"| **Source** | {data.alert_source} |",
        f"| **Severity** | {data.severity} |",
        "",
        "## Threat Intelligence",
        "",
        f"- **Threat Score:** {threat_score}/10",
        f"- **OTX Matches:** {ti_result.get('match_count', 0)} pulses",
        "",
        "## Recommendations",
        "",
    ]

    if is_malicious:
        lines.extend([
            "1. ✅ Block the IOC at network perimeter",
            "2. 🔍 Hunt for secondary IOCs",
            "3. 📧 Check for related phishing emails",
        ])
    else:
        lines.extend([
            "1. 👁️ Continue monitoring",
            "2. 📊 Review alert source configuration",
        ])

    if data.note:
        lines.extend(["", "## Notes", "", data.note])

    lines.extend(["", "---", "*Auto-generated by SOC Copilot*"])

    report_id = f"RPT-{data.case_id}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"

    return GenerateReportResponse(
        status="success",
        report_id=report_id,
        case_id=data.case_id,
        markdown="\n".join(lines),
        report_url=f"/api/v1/reports/{report_id}",
        threat_level=threat_level,
    )


@router.post("/internal/case-update", response_model=CaseUpdateResponse)
async def internal_case_update(
    data: CaseUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """Internal API: Mock case system callback."""
    logger.info(f"[MOCK] Case update: {data.case_id} -> {data.status}")

    return CaseUpdateResponse(
        status="success",
        case_id=data.case_id,
        updated_at=datetime.now(UTC).isoformat(),
        message=f"Case {data.case_id} updated to {data.status}",
    )
