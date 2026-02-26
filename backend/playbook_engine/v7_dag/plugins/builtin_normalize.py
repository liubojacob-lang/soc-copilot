"""Normalize IOC input node plugin (v0.7.4)."""

from typing import Any, Dict
import logging
import re

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class NormalizePlugin(BaseNodePlugin):
    """Normalize IOC input for consistent processing.
    
    This node cleans and standardizes IOC values:
    - Removes whitespace and converts to lowercase
    - Removes trailing slashes from URLs
    - Validates IOC format
    """

    @property
    def node_id(self) -> str:
        return "builtin_normalize"

    @property
    def name(self) -> str:
        return "Normalize IOC"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Normalize and validate IOC input"

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """Validate input before execution."""
        if not input_json.get("ioc"):
            raise ValueError("ioc is required")

    async def execute(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Execute IOC normalization.

        Args:
            context: Execution context

        Returns:
            Normalized IOC and detected type
        """
        ioc = str(context.input_json.get("ioc", "")).strip()
        ioc_type = context.input_json.get("ioc_type", "auto")

        logger.info(f"[{context.run_id}] Normalizing IOC: {ioc}")

        # Normalize based on type
        normalized = ioc.lower()
        detected_type = ioc_type

        if ioc_type == "auto":
            detected_type = self._detect_ioc_type(normalized)
        
        # Type-specific normalization
        if detected_type == "url":
            normalized = self._normalize_url(normalized)
        elif detected_type == "domain":
            normalized = self._normalize_domain(normalized)
        elif detected_type == "ip":
            normalized = self._normalize_ip(normalized)
        elif detected_type == "hash":
            normalized = normalized.lower()

        # Validate
        is_valid = self._validate_ioc(normalized, detected_type)

        logger.info(f"[{context.run_id}] Normalized: {normalized} (type: {detected_type}, valid: {is_valid})")

        return {
            "status": "success" if is_valid else "invalid",
            "original_ioc": ioc,
            "normalized_ioc": normalized,
            "original_type": ioc_type,
            "normalized_type": detected_type,
            "is_valid": is_valid,
            "validation_message": "IOC normalized successfully" if is_valid else f"Invalid {detected_type} format"
        }

    def _detect_ioc_type(self, ioc: str) -> str:
        """Auto-detect IOC type."""
        # URL
        if ioc.startswith(("http://", "https://")):
            return "url"
        
        # IP address
        if re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ioc):
            return "ip"
        
        # Hash (MD5, SHA1, SHA256)
        if re.match(r'^[a-f0-9]{32}$', ioc):
            return "hash"
        if re.match(r'^[a-f0-9]{40}$', ioc):
            return "hash"
        if re.match(r'^[a-f0-9]{64}$', ioc):
            return "hash"
        
        # Domain
        if re.match(r'^([a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$', ioc):
            return "domain"
        
        # Email
        if re.match(r'^[^@]+@[^@]+\.[^@]+$', ioc):
            return "email"
        
        return "unknown"

    def _normalize_url(self, url: str) -> str:
        """Normalize URL."""
        # Remove trailing slashes
        url = url.rstrip('/')
        # Remove fragment
        if '#' in url:
            url = url.split('#')[0]
        return url

    def _normalize_domain(self, domain: str) -> str:
        """Normalize domain."""
        # Remove www. prefix for consistency
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain

    def _normalize_ip(self, ip: str) -> str:
        """Normalize IP address."""
        # Validate and return as-is (already lowercase)
        return ip

    def _validate_ioc(self, ioc: str, ioc_type: str) -> bool:
        """Validate IOC format."""
        if not ioc:
            return False
        
        if ioc_type == "url":
            return ioc.startswith(("http://", "https://"))
        elif ioc_type == "domain":
            return bool(re.match(r'^([a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$', ioc))
        elif ioc_type == "ip":
            return bool(re.match(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ioc))
        elif ioc_type == "hash":
            return bool(re.match(r'^[a-f0-9]{32}$', ioc) or re.match(r'^[a-f0-9]{40}$', ioc) or re.match(r'^[a-f0-9]{64}$', ioc))
        
        return ioc_type != "unknown"
