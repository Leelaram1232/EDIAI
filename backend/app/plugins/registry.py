"""
Plugin Registry — discovers, registers, and routes to plugins.
"""
from typing import Optional
from app.plugins.base import BasePlugin, PluginResponse
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PluginRegistry:
    """Central registry for all platform plugins."""

    def __init__(self):
        self._plugins: dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin):
        """Register a plugin."""
        self._plugins[plugin.name] = plugin
        logger.info(f"Plugin registered: {plugin.name} v{plugin.version}")

    def unregister(self, name: str):
        """Unregister a plugin."""
        if name in self._plugins:
            del self._plugins[name]
            logger.info(f"Plugin unregistered: {name}")

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a registered plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> list[dict]:
        """List all registered plugins with their capabilities."""
        return [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "capabilities": p.get_capabilities(),
            }
            for p in self._plugins.values()
        ]

    async def route(self, plugin_name: str, intent: str, payload: dict) -> PluginResponse:
        """Route a request to the appropriate plugin."""
        plugin = self._plugins.get(plugin_name)
        if not plugin:
            return PluginResponse(
                content=f"Plugin '{plugin_name}' not found. Available: {list(self._plugins.keys())}",
                confidence=0.0,
            )

        if intent not in plugin.get_capabilities():
            return PluginResponse(
                content=f"Intent '{intent}' not supported by {plugin_name}. "
                        f"Available: {plugin.get_capabilities()}",
                confidence=0.0,
            )

        return await plugin.process(intent, payload)

    async def initialize_all(self):
        """Initialize all registered plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.initialize()
                logger.info(f"Plugin initialized: {name}")
            except Exception as e:
                logger.error(f"Plugin init failed: {name}: {e}")

    async def shutdown_all(self):
        """Shut down all registered plugins."""
        for name, plugin in self._plugins.items():
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error(f"Plugin shutdown failed: {name}: {e}")


# Singleton
plugin_registry = PluginRegistry()
