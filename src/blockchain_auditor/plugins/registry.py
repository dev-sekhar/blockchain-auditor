from __future__ import annotations

from pathlib import Path

from .contracts import EcosystemPlugin, PluginResult
from .ecosystems import BUILTIN_PLUGINS


class PluginRegistry:
    def __init__(self, plugins: list[EcosystemPlugin] | None = None): self._plugins = list(plugins or [])
    def register(self, plugin: EcosystemPlugin):
        if any(item.plugin_id == plugin.plugin_id for item in self._plugins): raise ValueError(f"Duplicate plugin ID: {plugin.plugin_id}")
        self._plugins.append(plugin)
    def plugins(self) -> list[EcosystemPlugin]: return list(self._plugins)
    def plan(self, project: dict) -> list[EcosystemPlugin]: return [plugin for plugin in self._plugins if plugin.matches(project)]
    def run(self, root: Path, project: dict) -> tuple[list[PluginResult], list[dict]]:
        selected = self.plan(project); results=[]
        for plugin in selected:
            try: results.append(plugin.analyze(root))
            except Exception as exc: results.append(PluginResult(plugin.plugin_id, plugin.version, "failed", error=str(exc)))
        coverage = [plugin.coverage(plugin in selected) for plugin in self._plugins]
        return results, coverage
    def capabilities(self) -> list[dict]: return [plugin.coverage(False) for plugin in self._plugins]


default_registry = PluginRegistry(BUILTIN_PLUGINS)
