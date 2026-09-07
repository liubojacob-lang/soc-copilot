"""
告警导入 API 路由

为前端 ImportAlertModal 提供 CEF/Syslog/JSON/CSV 文本告警的解析与入库能力。
解析复用 services.alerting.alert_parser.AlertParser；落库直接复用
security-alerts 的 ingest_alert（自带去重、提交、缓存失效与消息队列发布），
本模块不编写任何 SQL。
"""

import hashlib
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.security_alert import SecurityAlert
from models.user import UserModel
from schemas.security_alert import SecurityAlertIngest, SecurityAlertResponse
from services.alerting.alert_parser import AlertParser, ParsedAlert
from services.security.security_alert_schema import ensure_security_alerts_schema

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["Alerts Import"])

_VALID_IMPORT_FORMATS = {"cef", "syslog", "json", "csv"}


class AlertImportPayload(BaseModel):
    content: str = Field(..., min_length=1, max_length=2_000_000)
    format: str | None = None
    source: str | None = None


class AlertBatchImportPayload(AlertImportPayload):
    preview_only: bool = False


def _resolve_format(content: str, hint: str | None) -> str:
    if hint and hint.lower() in _VALID_IMPORT_FORMATS:
        return hint.lower()
    return AlertParser.detect_format(content)


def _parsed_to_dict(parsed: ParsedAlert) -> dict[str, Any]:
    data = parsed.to_dict()
    if data.get("event_timestamp") is not None:
        data["event_timestamp"] = data["event_timestamp"].isoformat()
    return data


def _raw_fallback(content: str) -> ParsedAlert:
    """检测不出的内容按 raw 处理，保留原文便于后续人工研判。"""
    first_line = content.strip().split("\n")[0]
    return ParsedAlert(
        source="raw",
        event_type="unknown",
        severity="info",
        title=first_line[:120],
        full_log=content,
    )


def _external_event_id(parsed: ParsedAlert) -> str:
    """基于内容生成稳定 ID：同一份内容重复导入时被 ingest 去重逻辑跳过。"""
    basis = parsed.full_log or parsed.title or "empty"
    digest = hashlib.sha256(basis.encode("utf-8", "replace")).hexdigest()[:16]
    return f"IMPORT-{digest}"


def _to_ingest_schema(parsed: ParsedAlert) -> SecurityAlertIngest:
    return SecurityAlertIngest(
        source=parsed.source or "manual",
        event_id=_external_event_id(parsed),
        timestamp=(parsed.event_timestamp or datetime.now(UTC)).isoformat(),
        event_type=parsed.event_type or "unknown",
        severity=(parsed.severity or "info").lower(),
        title=parsed.title or "Imported alert",
        description=parsed.description,
        source_ip=parsed.source_ip,
        destination_ip=parsed.destination_ip,
        protocol=parsed.protocol,
        agent_name=parsed.agent_name,
        agent_id=parsed.agent_id,
        agent_ip=parsed.agent_ip,
        rule_id=parsed.rule_id,
        rule_level=parsed.rule_level,
        full_log=parsed.full_log,
        raw_data=parsed.raw_data,
    )


async def _ingest_parsed(
    db: AsyncSession, current_user: UserModel, parsed: ParsedAlert
) -> tuple[SecurityAlert | None, bool]:
    """复用 ingest_alert 落库；返回 (alert, created)。"""
    # 函数内导入，避免 routers 之间的模块级循环依赖
    from routers.security_alerts import ingest_alert

    result = await ingest_alert(_to_ingest_schema(parsed), db, current_user)
    alert_id = result.get("alert_id")
    alert = await db.get(SecurityAlert, alert_id) if alert_id is not None else None
    return alert, result.get("status") == "success"


async def _serialize_alert(alert: SecurityAlert | None) -> dict[str, Any] | None:
    if alert is None:
        return None
    return SecurityAlertResponse.model_validate(alert).model_dump(mode="json")


@router.post("/import", response_model=dict)
async def import_alert(
    payload: AlertImportPayload,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """导入单条告警（CEF/Syslog/JSON/CSV 文本），解析并入库。"""
    await ensure_security_alerts_schema(db)
    fmt = _resolve_format(payload.content, payload.format)
    try:
        parsed = AlertParser.parse_single(payload.content, fmt)
    except ValueError:
        parsed = _raw_fallback(payload.content)

    if payload.source:
        parsed.source = payload.source

    alert, created = await _ingest_parsed(db, current_user, parsed)
    return {
        "success": True,
        "data": {
            "alert": await _serialize_alert(alert if created else None),
            "parsed": _parsed_to_dict(parsed),
            "format_detected": fmt,
            "duplicate": not created,
        },
    }


@router.post("/import/preview", response_model=dict)
async def preview_alert_import(
    payload: AlertImportPayload,
    current_user: UserModel = Depends(get_current_user),
):
    """解析单条告警但不入库。"""
    fmt = _resolve_format(payload.content, payload.format)
    try:
        parsed = AlertParser.parse_single(payload.content, fmt)
    except ValueError:
        parsed = _raw_fallback(payload.content)
    return {
        "success": True,
        "data": {"parsed": _parsed_to_dict(parsed), "format_detected": fmt},
    }


@router.post("/import/batch", response_model=dict)
async def import_alerts_batch(
    payload: AlertBatchImportPayload,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """批量导入告警；preview_only=true 时仅解析不入库。"""
    await ensure_security_alerts_schema(db)
    fmt = _resolve_format(payload.content, payload.format)
    parsed_alerts = AlertParser.parse_batch(payload.content, fmt)
    if not parsed_alerts:
        raise HTTPException(
            status_code=400, detail="No alerts could be parsed from content"
        )

    preview = [_parsed_to_dict(p) for p in parsed_alerts[:10]]
    errors: list[dict] = []
    created_count = 0

    if not payload.preview_only:
        for idx, parsed in enumerate(parsed_alerts, start=1):
            try:
                if payload.source:
                    parsed.source = payload.source
                _, created = await _ingest_parsed(db, current_user, parsed)
                if created:
                    created_count += 1
            except Exception as e:  # 逐条容错，失败不阻断其余行
                errors.append({"row": idx, "error": str(e)})

    return {
        "success": True,
        "data": {
            "total_parsed": len(parsed_alerts),
            "total_created": created_count,
            "format_detected": fmt,
            "preview": preview,
            "errors": errors,
        },
    }


@router.post("/import/batch/preview", response_model=dict)
async def preview_alerts_batch(
    payload: AlertBatchImportPayload,
    current_user: UserModel = Depends(get_current_user),
):
    """批量解析告警但不入库。"""
    fmt = _resolve_format(payload.content, payload.format)
    parsed_alerts = AlertParser.parse_batch(payload.content, fmt)
    return {
        "success": True,
        "data": {
            "total_parsed": len(parsed_alerts),
            "format_detected": fmt,
            "preview": [_parsed_to_dict(p) for p in parsed_alerts[:10]],
        },
    }
