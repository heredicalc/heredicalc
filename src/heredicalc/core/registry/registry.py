"""Plugin registry — explicit object, no global singleton."""

from __future__ import annotations

import importlib
import importlib.metadata
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

import platformdirs
from packaging.version import Version

from heredicalc.core.exceptions import UnknownPluginKindError
from heredicalc.core.models.plugin import PluginMeta
from heredicalc.core.registry.resolver import (
    PluginEntry,
    check_circular,
    instantiate,
    resolve,
    validate_compatibility,
)

logger = logging.getLogger(__name__)

_BUILTIN_KINDS = frozenset(
    [
        "pedigree_format",
        "phenotype_model",
        "incidence_source",
        "trait_mapper",
        "hazard_model",
        "penetrance_model",
        "crhf_model",
        "rr_model",
        "liability_assigner",
        "flb_calculator",
    ]
)


class PluginRegistry:
    """In-memory registry of available plugins, keyed by kind → name → version."""

    def __init__(self) -> None:
        # kind → name → version_str → PluginEntry
        self._store: dict[str, dict[str, dict[str, PluginEntry]]] = {}
        self._kinds: set[str] = set()

        for kind in _BUILTIN_KINDS:
            self.register_kind(kind)

    # ------------------------------------------------------------------
    # Kind management
    # ------------------------------------------------------------------

    def register_kind(self, kind: str) -> None:
        """Register a plugin kind. Idempotent."""
        self._kinds.add(kind)
        if kind not in self._store:
            self._store[kind] = {}

    def known_kinds(self) -> list[str]:
        return sorted(self._kinds)

    # ------------------------------------------------------------------
    # Plugin registration
    # ------------------------------------------------------------------

    def register(
        self,
        plugin_class: type,
        source: str = "builtin",
    ) -> None:
        """Register a plugin class. Must have a class-level `meta: PluginMeta`."""
        meta: PluginMeta = plugin_class.meta
        if meta.kind not in self._kinds:
            raise UnknownPluginKindError(
                f"Plugin {meta.name!r} declares unknown kind {meta.kind!r}. "
                f"Call register_kind() first."
            )
        self._store[meta.kind].setdefault(meta.name, {})[meta.version] = PluginEntry(
            plugin_class=plugin_class,
            meta=meta,
            source=source,  # type: ignore[arg-type]
        )
        logger.debug("Registered plugin %s/%s v%s from %s", meta.kind, meta.name, meta.version, source)

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def discover_builtins(self) -> None:
        """Register all built-in plugins from heredicalc.plugins._BUILTIN_PLUGINS."""
        try:
            import heredicalc.plugins as _builtins

            for plugin_class in _builtins._BUILTIN_PLUGINS:
                self.register(plugin_class, source="builtin")
        except ImportError as exc:
            logger.warning("Could not import heredicalc.plugins: %s", exc)

    def discover_entrypoints(self) -> None:
        """Discover and register plugins registered via entry_points."""
        eps = importlib.metadata.entry_points(group="heredicalc.plugins")
        for ep in eps:
            try:
                plugin_class = ep.load()
                self.register(plugin_class, source="entrypoint")
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load entry point plugin %s: %s", ep.name, exc)

    def discover_copyin(self, directory: Path | None = None) -> None:
        """Scan the copy-in directory for plugin packages."""
        if directory is None:
            directory = Path(platformdirs.user_data_dir("heredicalc")) / "plugins"
        if not directory.exists():
            return
        for plugin_file in directory.rglob("plugin.py"):
            self._load_copyin_plugin(plugin_file)

    def discover_all(self) -> None:
        """Run all discovery phases in order."""
        self.discover_builtins()
        self.discover_entrypoints()
        self.discover_copyin()
        self._run_circular_dep_check()

    # ------------------------------------------------------------------
    # Resolution and instantiation
    # ------------------------------------------------------------------

    def resolve(self, kind: str, constraint_str: str) -> PluginEntry:
        return resolve(kind, constraint_str, self._store, self._kinds)

    def instantiate(self, kind: str, constraint_str: str, config: Any) -> Any:
        """Resolve, instantiate, and inject sub-plugins for a plugin."""
        entry = self.resolve(kind, constraint_str)
        return instantiate(entry.plugin_class, config, self._store, self._kinds)

    def validate_compatibility(self, plugins: dict[str, Any]) -> None:
        validate_compatibility(plugins)

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def list_plugins(self, kind: str | None = None) -> list[PluginEntry]:
        kinds = [kind] if kind else list(self._kinds)
        result = []
        for k in kinds:
            for name_versions in self._store.get(k, {}).values():
                result.extend(name_versions.values())
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_copyin_plugin(self, path: Path) -> None:
        module_name = f"_heredicalc_copyin_{path.parent.name}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                return
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            if hasattr(module, "plugin_class"):
                self.register(module.plugin_class, source="copyin")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load copy-in plugin %s: %s", path, exc)

    def _run_circular_dep_check(self) -> None:
        for kind_store in self._store.values():
            for name_versions in kind_store.values():
                for entry in name_versions.values():
                    check_circular(entry.plugin_class, self._store)
