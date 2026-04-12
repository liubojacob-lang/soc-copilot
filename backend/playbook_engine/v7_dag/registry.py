"""Node Registry for dynamic plugin loading (v0.7.4).

This module provides the NodeRegistry class which manages dynamic
loading and registration of node plugins from the plugins/ directory.
"""

import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Optional

from .base_node import BaseNodePlugin

logger = logging.getLogger(__name__)


# Global registry instance
_node_registry: Optional["NodeRegistry"] = None


class NodeRegistry:
    """Registry for node plugins with auto-loading support."""

    def __init__(self) -> None:
        """Initialize an empty node registry."""
        self._plugins: dict[str, type[BaseNodePlugin]] = {}

    def register(self, node_id: str, plugin_class: type[BaseNodePlugin]) -> None:
        """Register a node plugin class.

        Args:
            node_id: Unique identifier for the node type
            plugin_class: Plugin class (not instance) to register
        """
        if node_id in self._plugins:
            logger.warning(f"Plugin '{node_id}' already registered, overwriting")

        self._plugins[node_id] = plugin_class
        logger.info(f"Registered node plugin: {node_id}")

    def get_plugin(self, node_id: str) -> BaseNodePlugin:
        """Get a new instance of a registered plugin.

        Args:
            node_id: Unique identifier for the node type

        Returns:
            New instance of the requested plugin

        Raises:
            ValueError: If plugin is not registered
        """
        if node_id not in self._plugins:
            available = list(self._plugins.keys())
            raise ValueError(
                f"Plugin not registered: {node_id}. " f"Available plugins: {available}"
            )
        return self._plugins[node_id]()

    def list_plugins(self) -> list[str]:
        """Get list of all registered plugin IDs.

        Returns:
            List of registered plugin identifiers
        """
        return list(self._plugins.keys())

    def get_plugin_info(self, node_id: str) -> dict[str, str]:
        """Get metadata about a registered plugin.

        Args:
            node_id: Unique identifier for the node type

        Returns:
            Dictionary with plugin metadata (name, type, description)

        Raises:
            ValueError: If plugin is not registered
        """
        if node_id not in self._plugins:
            raise ValueError(f"Plugin not registered: {node_id}")

        plugin = self._plugins[node_id]()
        return {
            "node_id": plugin.node_id,
            "name": plugin.name,
            "node_type": plugin.node_type,
            "description": plugin.description,
        }

    def list_all_info(self) -> list[dict[str, str]]:
        """Get metadata for all registered plugins.

        Returns:
            List of plugin metadata dictionaries
        """
        return [self.get_plugin_info(node_id) for node_id in self.list_plugins()]

    def auto_load_plugins(self, plugin_dir: Path) -> int:
        """Automatically load all plugins from a directory.

        Args:
            plugin_dir: Path to directory containing plugin modules

        Returns:
            Number of plugins loaded
        """
        if not plugin_dir.exists():
            logger.warning(f"Plugin directory does not exist: {plugin_dir}")
            return 0

        count = 0
        package_name = "playbook_engine.v7_dag.plugins"

        for module_info in pkgutil.iter_modules([str(plugin_dir)]):
            module_name = f"{package_name}.{module_info.name}"
            try:
                module = importlib.import_module(module_name)

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseNodePlugin)
                        and attr != BaseNodePlugin
                    ):
                        plugin = attr()
                        self._plugins[plugin.node_id] = attr
                        count += 1
                        logger.info(
                            f"Auto-loaded plugin: {plugin.node_id} from {module_name}"
                        )

            except Exception as e:
                logger.error(f"Failed to load plugin module {module_name}: {e}")

        logger.info(f"Auto-loaded {count} plugins from {plugin_dir}")
        return count


# Global singleton functions
def set_node_registry(registry: NodeRegistry) -> None:
    """Set the global node registry instance."""
    global _node_registry
    _node_registry = registry


def get_node_registry() -> NodeRegistry | None:
    """Get the global node registry instance."""
    return _node_registry


# Create default instance
default_registry = NodeRegistry()
set_node_registry(default_registry)
