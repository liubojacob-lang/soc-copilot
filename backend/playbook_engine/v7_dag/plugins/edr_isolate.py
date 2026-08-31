"""EDR Endpoint Isolate node plugin — SOC Playbook Response Action (v0.8.0).

Provides an action node to isolate (contain) an endpoint via the EDR
platform's API. Supports CrowdStrike Falcon and SentinelOne.

This is a Phase 3 DAG-level plugin ("Response Node") used in automated
incident-response playbooks to stop lateral movement or data exfiltration.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from core.config import settings
from core.ssrf_protection import is_url_safe
from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Audit helper
# ---------------------------------------------------------------------------

_AUDIT_LOGGER = logging.getLogger("soar_audit")


def _audit(
    action: str,
    target: str,
    outcome: str,
    run_id: str,
    node_id: str,
    detail: str = "",
) -> None:
    _AUDIT_LOGGER.info(
        "SOAR_AUDIT action=%s target=%s outcome=%s run_id=%s node_id=%s detail=%s",
        action,
        target,
        outcome,
        run_id,
        node_id,
        detail,
    )


# ===================================================================
# CrowdStrike + SentinelOne constants
# ===================================================================

_CROWDSTRIKE_ISOLATE_URL = "/devices/entities/devices-action/v2"
_SENTINELONE_DISCONNECT_URL = "/web/api/v2.1/agents/actions/disconnect"

# Well-known EDR SaaS endpoints (for SSRF whitelist)
_EDR_KNOWN_HOSTS = frozenset(
    {
        "api.crowdstrike.com",
        "api.eu-1.crowdstrike.com",
        "api.us-2.crowdstrike.com",
        "usea1-001.sentinelone.net",
    }
)


def _resolve_host(base_url: str) -> str:
    """Extract hostname for SSRF sandbox whitelist."""
    from urllib.parse import urlparse

    return urlparse(base_url).hostname or ""


# ===================================================================
# Plugin
# ===================================================================


class EDRIsolateNode(BaseNodePlugin):
    """Isolate (contain) an endpoint via EDR platform API.

    Supported platforms:
    - **CrowdStrike Falcon**: POST /devices/entities/devices-action/v2
      with ``action_name: "contain"``.
    - **SentinelOne**: POST /web/api/v2.1/agents/actions/disconnect
      with ``{filter: {ids: "..."}}``.

    Input parameters
    ----------------
    - ``agent_id`` / ``device_id`` (str, required): endpoint identifier
    - ``platform`` (str, required): ``"crowdstrike"`` or ``"sentinelone"``
    - ``reason``  (str, optional): audit context
    - ``base_url`` (str, optional): override default SaaS endpoint

    Secrets required
    ----------------
    - ``EDR_API_KEY`` (str)
    - ``EDR_API_SECRET`` (str, CrowdStrike only)
    - ``S1_API_TOKEN`` (str, SentinelOne only)
    """

    @property
    def node_id(self) -> str:
        return "edr_isolate"

    @property
    def name(self) -> str:
        return "EDR Endpoint Isolate"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return (
            "Isolate an endpoint via CrowdStrike Falcon or SentinelOne API. "
            "Supports contain (CrowdStrike) and firewall-isolation (SentinelOne)."
        )

    def validate_input(self, input_json: dict[str, Any]) -> None:
        agent_id = input_json.get("agent_id") or input_json.get("device_id")
        if not agent_id:
            raise ValueError("agent_id or device_id is required")

        platform = input_json.get("platform", "").lower()
        if platform not in ("crowdstrike", "sentinelone"):
            raise ValueError("platform must be 'crowdstrike' or 'sentinelone'")

    def get_required_secrets(self) -> list[str]:
        return [
            "EDR_API_KEY",
            "EDR_API_SECRET",
            "S1_API_TOKEN",
        ]

    # ---- Core execute -----------------------------------------------------

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        agent_id: str = context.input_json.get("agent_id") or context.input_json["device_id"]
        platform: str = context.input_json["platform"].lower()
        reason: str = context.input_json.get("reason", "SOC automated containment")
        dry_run: bool = context.mode == "dry_run"

        base_url: str = context.input_json.get(
            "base_url",
            self._default_base_url(platform),
        )

        if dry_run:
            logger.info(
                "[%s] DRY-RUN: would isolate endpoint %s on %s",
                context.run_id,
                agent_id,
                platform,
            )
            _audit(
                action="edr_isolate",
                target=agent_id,
                outcome="dry_run",
                run_id=context.run_id,
                node_id=context.node_id,
                detail=f"platform={platform} reason={reason}",
            )
            return {
                "status": "success",
                "agent_id": agent_id,
                "platform": platform,
                "isolated": False,
                "dry_run": True,
            }

        logger.info(
            "[%s] Isolating endpoint %s on platform %s",
            context.run_id,
            agent_id,
            platform,
        )

        try:
            if platform == "crowdstrike":
                result = await self._isolate_crowdstrike(
                    base_url, agent_id, reason, context
                )
            else:  # sentinelone
                result = await self._isolate_sentinelone(
                    base_url, agent_id, reason, context
                )
        except Exception as exc:
            logger.exception("[%s] EDR isolate failed: %s", context.run_id, exc)
            _audit(
                action="edr_isolate",
                target=agent_id,
                outcome="error",
                run_id=context.run_id,
                node_id=context.node_id,
                detail=f"platform={platform} error={exc!s}",
            )
            return {
                "status": "error",
                "error": str(exc),
                "agent_id": agent_id,
                "platform": platform,
                "isolated": False,
            }

        _audit(
            action="edr_isolate",
            target=agent_id,
            outcome="success",
            run_id=context.run_id,
            node_id=context.node_id,
            detail=f"platform={platform} reason={reason}",
        )

        return {
            "status": "success",
            "agent_id": agent_id,
            "platform": platform,
            "isolated": True,
            "response": result,
            "reason": reason,
        }

    # ===================================================================
    # CrowdStrike
    # ===================================================================

    async def _isolate_crowdstrike(
        self,
        base_url: str,
        device_id: str,
        reason: str,
        context: NodeExecutionContext,
    ) -> dict[str, Any]:
        """POST /devices/entities/devices-action/v2 with action_name=contain."""
        api_key = context.secrets.get("EDR_API_KEY", "")
        api_secret = context.secrets.get("EDR_API_SECRET", "")

        if not api_key or not api_secret:
            raise RuntimeError("CrowdStrike credentials not configured (EDR_API_KEY / EDR_API_SECRET)")

        # --- SSRF sandbox enforcement ---
        host = _resolve_host(base_url)
        if host and host not in _EDR_KNOWN_HOSTS:
            allowed = None
            if settings.http_allowed_hosts:
                allowed = [h.strip() for h in settings.http_allowed_hosts.split(",") if h.strip()]
            is_safe, reason_block = is_url_safe(base_url, allowed)
            if not is_safe:
                raise ValueError(f"EDR base_url blocked by SSRF sandbox: {reason_block}")

        url = f"{base_url.rstrip('/')}{_CROWDSTRIKE_ISOLATE_URL}"

        payload = {
            "action_name": "contain",
            "ids": [device_id],
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        logger.info("[%s] CrowdStrike isolate: %s", context.run_id, url)

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            auth=httpx.BasicAuth(api_key, api_secret),
        ) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code not in (200, 201, 202):
            raise RuntimeError(
                f"CrowdStrike API returned {resp.status_code}: {resp.text[:500]}"
            )

        logger.info("[%s] CrowdStrike isolate accepted for device %s", context.run_id, device_id)
        return resp.json()

    # ===================================================================
    # SentinelOne
    # ===================================================================

    async def _isolate_sentinelone(
        self,
        base_url: str,
        agent_id: str,
        reason: str,
        context: NodeExecutionContext,
    ) -> dict[str, Any]:
        """POST /web/api/v2.1/agents/actions/disconnect (firewall isolation)."""
        api_token = context.secrets.get("S1_API_TOKEN", "")

        if not api_token:
            raise RuntimeError("SentinelOne API token not configured (S1_API_TOKEN)")

        # --- SSRF sandbox enforcement ---
        host = _resolve_host(base_url)
        if host and host not in _EDR_KNOWN_HOSTS:
            allowed = None
            if settings.http_allowed_hosts:
                allowed = [h.strip() for h in settings.http_allowed_hosts.split(",") if h.strip()]
            is_safe, reason_block = is_url_safe(base_url, allowed)
            if not is_safe:
                raise ValueError(f"EDR base_url blocked by SSRF sandbox: {reason_block}")

        url = f"{base_url.rstrip('/')}{_SENTINELONE_DISCONNECT_URL}"

        payload = {
            "filter": {
                "ids": agent_id,
            },
        }

        headers = {
            "Authorization": f"APIToken {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        logger.info("[%s] SentinelOne isolate (disconnect): %s", context.run_id, url)

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"SentinelOne API returned {resp.status_code}: {resp.text[:500]}"
            )

        logger.info("[%s] SentinelOne isolate accepted for agent %s", context.run_id, agent_id)
        return resp.json()

    # ===================================================================
    # Helpers
    # ===================================================================

    @staticmethod
    def _default_base_url(platform: str) -> str:
        """Return the default SaaS endpoint if none is configured."""
        if platform == "crowdstrike":
            return getattr(settings, "crowdstrike_base_url", "https://api.crowdstrike.com")
        else:
            return getattr(settings, "sentinelone_base_url", "https://usea1-001.sentinelone.net")
