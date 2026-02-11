"""Playbook module for SIEM query generation and remediation actions."""

from .playbook_engine import generate_siem_queries, generate_remediation_actions

__all__ = ["generate_siem_queries", "generate_remediation_actions"]
