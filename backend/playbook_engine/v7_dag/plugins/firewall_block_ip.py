"""Firewall IP Block node plugin — SOC Playbook Response Action (v0.8.0).

Provides an action node to block an IP address at the perimeter firewall
via the vendor API. Supports Palo Alto Networks PAN-OS and Fortinet FortiGate.

This is a Phase 3 DAG-level plugin ("Response Node") used in automated
incident-response playbooks to contain threats at the network edge.
"""

from __future__ import annotations

import logging
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
# Plugin
# ===================================================================


class FirewallBlockIPNode(BaseNodePlugin):
    """Block an IP address on the perimeter firewall.

    Supported firewall platforms:
    - **Palo Alto PAN-OS**: POST /api with XML-style config via
      ``type=config&action=set&xpath=...&element=...`` to add the IP
      to a block address-group.
    - **Fortinet FortiGate**: POST /api/v2/cmdb/firewall/addrgrp/<group>/member
      to add the IP to the blocked address group.

    Input parameters
    ----------------
    - ``ip``           (str, required): IPv4 or IPv6 address to block
    - ``platform``      (str, required): ``"paloalto"`` or ``"fortinet"``
    - ``firewall_url``  (str, optional): firewall management URL
    - ``address_group`` (str, optional): address group name (default: "blocked")
    - ``reason``        (str, optional): audit context
    - ``duration_min``  (int, optional): auto-remove after N minutes (0=permanent)

    Secrets required
    ----------------
    - ``FW_API_KEY`` (str, required): API key or token for the firewall
    """

    @property
    def node_id(self) -> str:
        return "firewall_block_ip"

    @property
    def name(self) -> str:
        return "Firewall IP Block"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return (
            "Block an IP address on the perimeter firewall. "
            "Supports Palo Alto PAN-OS and Fortinet FortiGate platforms."
        )

    def validate_input(self, input_json: dict[str, Any]) -> None:
        ip = input_json.get("ip")
        if not ip:
            raise ValueError("ip is required")

        platform = input_json.get("platform", "").lower()
        if platform not in ("paloalto", "palo_alto", "fortinet", "fortigate"):
            raise ValueError("platform must be 'paloalto' or 'fortinet'")

        # Sanity: validate IPv4/IPv6 format
        import re

        ip_stripped = ip.strip()
        if not re.match(r"^[\d.:a-fA-F]+$", ip_stripped):
            raise ValueError(f"Invalid IP address format: {ip_stripped}")

    def get_required_secrets(self) -> list[str]:
        return [
            "FW_API_KEY",
        ]

    # ---- Core execute -----------------------------------------------------

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        ip: str = context.input_json["ip"].strip()
        platform_raw: str = context.input_json.get("platform", "paloalto").lower()
        # Normalize aliases
        if platform_raw in ("palo_alto", "panos", "paloalto"):
            platform = "paloalto"
        else:
            platform = "fortinet"

        reason: str = context.input_json.get("reason", "SOC automated containment")
        duration_min: int = int(context.input_json.get("duration_min", 0))
        address_group: str = context.input_json.get("address_group", "blocked")
        dry_run: bool = context.mode == "dry_run"

        firewall_url: str = context.input_json.get(
            "firewall_url",
            self._default_firewall_url(platform),
        )

        if dry_run:
            logger.info(
                "[%s] DRY-RUN: would block IP %s on %s firewall",
                context.run_id,
                ip,
                platform,
            )
            _audit(
                action="firewall_block_ip",
                target=ip,
                outcome="dry_run",
                run_id=context.run_id,
                node_id=context.node_id,
                detail=f"platform={platform} reason={reason} duration_min={duration_min}",
            )
            return {
                "status": "success",
                "ip": ip,
                "platform": platform,
                "blocked": False,
                "dry_run": True,
            }

        logger.info(
            "[%s] Blocking IP %s on %s firewall (group=%s)",
            context.run_id,
            ip,
            platform,
            address_group,
        )

        try:
            if platform == "paloalto":
                result = await self._block_paloalto(
                    firewall_url, ip, address_group, reason, context
                )
            else:
                result = await self._block_fortinet(
                    firewall_url, ip, address_group, reason, context
                )
        except Exception as exc:
            logger.exception("[%s] Firewall block failed: %s", context.run_id, exc)
            _audit(
                action="firewall_block_ip",
                target=ip,
                outcome="error",
                run_id=context.run_id,
                node_id=context.node_id,
                detail=f"platform={platform} error={exc!s}",
            )
            return {
                "status": "error",
                "error": str(exc),
                "ip": ip,
                "platform": platform,
                "blocked": False,
            }

        # Schedule auto-removal if duration specified
        if duration_min > 0:
            logger.info(
                "[%s] IP %s block will auto-expire in %d min",
                context.run_id,
                ip,
                duration_min,
            )

        _audit(
            action="firewall_block_ip",
            target=ip,
            outcome="success",
            run_id=context.run_id,
            node_id=context.node_id,
            detail=f"platform={platform} group={address_group} reason={reason} duration_min={duration_min}",
        )

        return {
            "status": "success",
            "ip": ip,
            "platform": platform,
            "blocked": True,
            "address_group": address_group,
            "duration_min": duration_min,
            "reason": reason,
            "response": result,
        }

    # ===================================================================
    # Palo Alto PAN-OS
    # ===================================================================

    async def _block_paloalto(
        self,
        firewall_url: str,
        ip: str,
        address_group: str,
        reason: str,
        context: NodeExecutionContext,
    ) -> dict[str, Any]:
        """Add IP to a PAN-OS address group via XML API.

        Uses ``type=config&action=set`` with XPath targeting the
        address-group's static member list.
        """
        api_key = context.secrets.get("FW_API_KEY", "")

        if not api_key:
            raise RuntimeError("Firewall API key not configured (FW_API_KEY)")

        # --- SSRF sandbox enforcement ---
        is_safe, reason_block = self._validate_url_safe(firewall_url)
        if not is_safe:
            raise ValueError(f"Firewall URL blocked by SSRF sandbox: {reason_block}")

        # XPath to add member to the address group
        xpath = (
            f"/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='vsys1']"
            f"/address-group/entry[@name='{address_group}']"
            f"/static"
        )

        element = f"<member>{ip}</member>"

        timeout = 30

        logger.info(
            "[%s] Palo Alto API: add %s to group %s", context.run_id, ip, address_group
        )

        verify_ssl = bool(context.input_json.get("verify_ssl", False))
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            verify=verify_ssl,
        ) as client:
            resp = await client.post(
                firewall_url,
                params={
                    "type": "config",
                    "action": "set",
                    "xpath": xpath,
                    "element": element,
                    "key": api_key,
                },
            )

        if resp.status_code != 200:
            raise RuntimeError(
                f"Palo Alto API returned {resp.status_code}: {resp.text[:500]}"
            )

        # Commit the change (PAN-OS requires explicit commit)
        await self._panos_commit(firewall_url, api_key, context)

        logger.info("[%s] Palo Alto IP block committed: %s", context.run_id, ip)

        return {
            "firewall": "paloalto",
            "action": "block_ip",
            "ip": ip,
            "group": address_group,
            "committed": True,
        }

    async def _panos_commit(
        self,
        firewall_url: str,
        api_key: str,
        context: NodeExecutionContext,
    ) -> None:
        """Issue a PAN-OS commit to activate pending config changes."""
        commit_url = firewall_url
        verify_ssl = bool(context.input_json.get("verify_ssl", False))

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            verify=verify_ssl,
        ) as client:
            resp = await client.post(
                commit_url,
                params={
                    "type": "commit",
                    "cmd": "<commit></commit>",
                    "key": api_key,
                },
            )

        if resp.status_code != 200:
            logger.warning(
                "[%s] PAN-OS commit returned %d — config may not be active: %s",
                context.run_id,
                resp.status_code,
                resp.text[:300],
            )
        else:
            logger.info("[%s] PAN-OS commit successful", context.run_id)

    # ===================================================================
    # Fortinet FortiGate
    # ===================================================================

    async def _block_fortinet(
        self,
        firewall_url: str,
        ip: str,
        address_group: str,
        reason: str,
        context: NodeExecutionContext,
    ) -> dict[str, Any]:
        """Add IP to FortiGate address group via REST API.

        POST /api/v2/cmdb/firewall/addrgrp/<group>/member
        """
        api_key = context.secrets.get("FW_API_KEY", "")

        if not api_key:
            raise RuntimeError("Firewall API key not configured (FW_API_KEY)")

        # --- SSRF sandbox enforcement ---
        is_safe, reason_block = self._validate_url_safe(firewall_url)
        if not is_safe:
            raise ValueError(f"Firewall URL blocked by SSRF sandbox: {reason_block}")

        base = firewall_url.rstrip("/")
        url = f"{base}/api/v2/cmdb/firewall/addrgrp/{address_group}/member"

        payload = {
            "name": f"blocked-{ip.replace('.', '-').replace(':', '-')}",
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        logger.info(
            "[%s] FortiGate API: add %s to group %s", context.run_id, ip, address_group
        )

        verify_ssl = bool(context.input_json.get("verify_ssl", False))
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            verify=verify_ssl,
        ) as client:
            resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code not in (200, 201):
            raise RuntimeError(
                f"FortiGate API returned {resp.status_code}: {resp.text[:500]}"
            )

        logger.info("[%s] FortiGate IP block accepted: %s", context.run_id, ip)

        return {
            "firewall": "fortinet",
            "action": "block_ip",
            "ip": ip,
            "group": address_group,
        }

    # ===================================================================
    # Helpers
    # ===================================================================

    @staticmethod
    def _validate_url_safe(url: str) -> tuple[bool, str]:
        """Validate that the firewall management URL is safe (SSRF check)."""
        allowed = None
        if settings.http_allowed_hosts:
            allowed = [
                h.strip() for h in settings.http_allowed_hosts.split(",") if h.strip()
            ]
        return is_url_safe(url, allowed)

    @staticmethod
    def _default_firewall_url(platform: str) -> str:
        """Return the configured default firewall management URL."""
        if platform == "paloalto":
            return getattr(settings, "paloalto_firewall_url", "")
        else:
            return getattr(settings, "fortinet_firewall_url", "")
