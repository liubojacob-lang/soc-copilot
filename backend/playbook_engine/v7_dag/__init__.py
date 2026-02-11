"""v7 DAG Node Plugin System for SOC Copilot v0.7.4.

This module provides dynamic plugin loading for playbook nodes,
allowing new node types to be added without modifying core code.
"""

from .registry import NodeRegistry
from .base_node import BaseNodePlugin, NodeExecutionContext

__all__ = [
    "NodeRegistry",
    "BaseNodePlugin",
    "NodeExecutionContext",
]
