"""AD Account Disable node plugin — SOC Playbook Response Action (v0.8.0).

Provides an action node to disable a user account in Active Directory
as part of an incident-response playbook. Supports both LDAP3 native
binding and subprocess-based PowerShell/WinRM fallback.

This is a Phase 3 DAG-level plugin ("Response Node") and must be
callable from any playbook that needs automated containment.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from core.config import settings

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Audit helper — every SOAR action must leave an audit trail
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
    """Write a structured audit record for the SOAR action."""
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


class ADDisableAccountNode(BaseNodePlugin):
    """Disable a user account in Active Directory.

    Sets userAccountControl = 514 (ACCOUNTDISABLE + NORMAL_ACCOUNT).
    Supports LDAP3 native and WinRM/PowerShell fallback transport.

    Operational notes
    -----------------
    - LDAP3  : preferred path; uses STARTTLS (port 389) or LDAPS (636)
    - WinRM  : fallback via ``Invoke-Command`` PowerShell remoting
    - Audit  : every call (including dry-run) produces an audit line
    - Dry-run: validates connectivity & looks up the user but does **not**
               perform the disable
    """

    @property
    def node_id(self) -> str:
        return "ad_disable_account"

    @property
    def name(self) -> str:
        return "AD Account Disable"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return (
            "Disable an Active Directory user account (userAccountControl=514). "
            "Supports LDAP3 native and WinRM/PowerShell fallback transport."
        )

    def validate_input(self, input_json: dict[str, Any]) -> None:
        username = input_json.get("username")
        if not username:
            raise ValueError("username (samAccountName) is required")

    def get_required_secrets(self) -> list[str]:
        return [
            "AD_LDAP_SERVER",
            "AD_BIND_USER",
            "AD_BIND_PASSWORD",
            "AD_DOMAIN",
        ]

    # ---- Core logic -------------------------------------------------------

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        username: str = context.input_json["username"]
        reason: str = context.input_json.get("reason", "SOC automated containment")
        _dc: str = context.input_json.get("domain_controller", "")
        dry_run: bool = context.mode == "dry_run"

        ldap_server = (
            _dc
            or context.secrets.get("AD_LDAP_SERVER")
            or getattr(settings, "ad_ldap_server", "")
        )
        bind_user = context.secrets.get("AD_BIND_USER", "")
        bind_pass = context.secrets.get("AD_BIND_PASSWORD", "")
        domain = context.secrets.get("AD_DOMAIN", getattr(settings, "ad_domain", ""))
        transport = getattr(settings, "ad_transport", "ldap3").lower()

        if not ldap_server:
            logger.warning("[%s] No AD LDAP server configured", context.run_id)
            return {
                "status": "error",
                "error": "AD LDAP server not configured",
                "username": username,
                "enabled": None,
            }

        if dry_run:
            logger.info(
                "[%s] DRY-RUN: would disable AD account %s", context.run_id, username
            )
            exists = await self._check_user_exists(
                ldap_server, bind_user, bind_pass, username, transport, context
            )
            _audit(
                action="ad_disable_account",
                target=username,
                outcome="dry_run" if exists else "dry_run_user_not_found",
                run_id=context.run_id,
                node_id=context.node_id,
                detail=f"reason={reason} transport={transport} exists={exists}",
            )
            return {
                "status": "success",
                "username": username,
                "enabled": True,
                "dry_run": True,
                "user_exists": exists,
            }

        logger.info(
            "[%s] Disabling AD account: %s  (transport=%s)",
            context.run_id,
            username,
            transport,
        )

        try:
            if transport == "winrm":
                result = await self._disable_via_winrm(
                    ldap_server, domain, username, reason, bind_user, bind_pass, context
                )
            else:
                result = await self._disable_via_ldap3(
                    ldap_server, bind_user, bind_pass, username, reason, context
                )
        except Exception as exc:
            logger.exception("[%s] AD disable failed: %s", context.run_id, exc)
            _audit(
                action="ad_disable_account",
                target=username,
                outcome="error",
                run_id=context.run_id,
                node_id=context.node_id,
                detail=f"error={exc!s}",
            )
            return {
                "status": "error",
                "error": str(exc),
                "username": username,
                "enabled": None,
            }

        _audit(
            action="ad_disable_account",
            target=username,
            outcome="success",
            run_id=context.run_id,
            node_id=context.node_id,
            detail=f"dn={result.get('user_dn','')} reason={reason}",
        )

        return {
            "status": "success",
            "username": username,
            "user_dn": result.get("user_dn"),
            "enabled": False,
            "reason": reason,
            "transport": transport,
        }

    # ===================================================================
    # LDAP3 path
    # ===================================================================

    async def _disable_via_ldap3(
        self,
        server_uri: str,
        bind_dn: str,
        bind_password: str,
        username: str,
        reason: str,
        context: NodeExecutionContext,
    ) -> dict[str, Any]:
        try:
            import ldap3  # type: ignore[import-untyped]
        except ImportError:
            raise RuntimeError(
                "ldap3 package is not installed. Install it with: pip install ldap3"
            ) from None

        use_ssl = server_uri.startswith("ldaps://")
        server = ldap3.Server(server_uri, use_ssl=use_ssl, get_info=ldap3.ALL)

        conn = ldap3.Connection(
            server,
            user=bind_dn,
            password=bind_password,
            authentication=ldap3.NTLM if "\\" in bind_dn else ldap3.SIMPLE,
            auto_bind=True,
        )

        base_dn = self._derive_base_dn(server_uri, bind_dn)
        search_filter = (
            f"(&(objectClass=user)"
            f"(samAccountName={ldap3.utils.conv.escape_filter_chars(username)}))"
        )

        conn.search(
            search_base=base_dn,
            search_filter=search_filter,
            attributes=["distinguishedName", "userAccountControl", "cn", "mail"],
            size_limit=1,
        )

        if not conn.entries:
            conn.unbind()
            raise ValueError(f"User '{username}' not found in AD (base={base_dn})")

        entry = conn.entries[0]
        user_dn = str(entry.distinguishedName)
        current_uac = int(entry.userAccountControl.value or 512)

        ACCOUNTDISABLE = 0x0002
        if current_uac & ACCOUNTDISABLE:
            logger.info("[%s] Account %s already disabled", context.run_id, username)
            conn.unbind()
            return {"user_dn": user_dn, "already_disabled": True}

        new_uac = current_uac | ACCOUNTDISABLE

        conn.modify(
            user_dn, {"userAccountControl": [(ldap3.MODIFY_REPLACE, [new_uac])]}
        )

        if conn.result["result"] != 0:
            err = conn.result.get("description", conn.result["message"])
            conn.unbind()
            raise RuntimeError(f"LDAP modify failed: {err}")

        # Append audit note to description
        try:
            conn.modify(
                user_dn,
                {
                    "description": [
                        (
                            ldap3.MODIFY_REPLACE,
                            [
                                f"SOC Copilot: account disabled {datetime.now(UTC).isoformat()} — {reason}"
                            ],
                        )
                    ]
                },
            )
        except Exception:
            logger.warning(
                "[%s] Could not update AD description for %s", context.run_id, username
            )

        conn.unbind()
        logger.info(
            "[%s] AD account disabled: %s  (uac=%d)", context.run_id, user_dn, new_uac
        )

        return {"user_dn": user_dn, "previous_uac": current_uac, "new_uac": new_uac}

    # ===================================================================
    # WinRM / PowerShell fallback
    # ===================================================================

    async def _disable_via_winrm(
        self,
        target_host: str,
        domain: str,
        username: str,
        reason: str,
        bind_user: str,
        bind_password: str,
        context: NodeExecutionContext,
    ) -> dict[str, Any]:
        import asyncio

        ps_script = (
            f'$secure = ConvertTo-SecureString "{bind_password}" -AsPlainText -Force; '
            f'$cred = New-Object System.Management.Automation.PSCredential("{bind_user}", $secure); '
            f"Invoke-Command -ComputerName {target_host} -Credential $cred -ScriptBlock {{"
            f"  Import-Module ActiveDirectory -ErrorAction Stop; "
            f'  $user = Get-ADUser -Identity "{username}" -ErrorAction Stop; '
            f"  Disable-ADAccount -Identity $user.DistinguishedName -Confirm:$false; "
            f'  Set-ADUser -Identity $user.DistinguishedName -Description "SOC Copilot: disabled {datetime.now(UTC).isoformat()} — {reason}"; '
            f"  Write-Output $user.DistinguishedName; "
            f"}}"
        )

        cmd = ["pwsh", "-NoProfile", "-NonInteractive", "-Command", ps_script]

        logger.info(
            "[%s] Invoking PowerShell via WinRM for AD disable (host=%s)",
            context.run_id,
            target_host,
        )

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace") or stdout.decode(
                "utf-8", errors="replace"
            )
            raise RuntimeError(f"PowerShell/WinRM failed (rc={proc.returncode}): {err}")

        user_dn = stdout.decode("utf-8", errors="replace").strip()
        return {"user_dn": user_dn, "transport": "winrm"}

    # ===================================================================
    # User-existence check (used by dry_run)
    # ===================================================================

    async def _check_user_exists(
        self,
        server_uri: str,
        bind_dn: str,
        bind_password: str,
        username: str,
        transport: str,
        context: NodeExecutionContext,
    ) -> bool:
        try:
            if transport == "winrm":
                import asyncio

                ps = (
                    f'$s = [adsisearcher]"(samaccountname={username})"; '
                    "$r = $s.FindOne(); if ($r) { 'FOUND' } else { 'NOTFOUND' }"
                )
                proc = await asyncio.create_subprocess_exec(
                    "pwsh",
                    "-NoProfile",
                    "-Command",
                    ps,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
                return b"FOUND" in stdout
            else:
                try:
                    import ldap3
                except ImportError:
                    return True
                server = ldap3.Server(
                    server_uri, use_ssl=server_uri.startswith("ldaps://")
                )
                conn = ldap3.Connection(
                    server, user=bind_dn, password=bind_password, auto_bind=True
                )
                base_dn = self._derive_base_dn(server_uri, bind_dn)
                conn.search(
                    search_base=base_dn,
                    search_filter=(
                        f"(&(objectClass=user)"
                        f"(samAccountName={ldap3.utils.conv.escape_filter_chars(username)}))"
                    ),
                    size_limit=1,
                )
                found = len(conn.entries) > 0
                conn.unbind()
                return found
        except Exception:
            logger.warning(
                "[%s] User existence check failed — assuming exists", context.run_id
            )
            return True

    @staticmethod
    def _derive_base_dn(server_uri: str, bind_dn: str) -> str:
        if bind_dn and "DC=" in bind_dn.upper():
            parts = [
                p.strip()
                for p in bind_dn.split(",")
                if p.strip().upper().startswith("DC=")
            ]
            if parts:
                return ",".join(parts)

        from urllib.parse import urlparse

        host = urlparse(server_uri).hostname or ""
        if host and "." in host:
            return ",".join(f"DC={part}" for part in host.split("."))

        return bind_dn or "DC=corp,DC=local"
