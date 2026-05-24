"""Version resolution, sub-plugin injection, and dependency validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from packaging.version import Version

from heredicalc.core.exceptions import (
    CircularDependencyError,
    PluginCompatibilityError,
    PluginResolutionError,
    UnknownPluginKindError,
)
from heredicalc.core.models.plugin import PluginMeta

if TYPE_CHECKING:
    from heredicalc.core.pipeline.config import PipelineConfig
    from heredicalc.core.registry.registry import PluginRegistry

_API_VERSION = "1.0.0"


@dataclass
class PluginEntry:
    plugin_class: type
    meta: PluginMeta
    source: Literal["builtin", "copyin", "entrypoint", "data_driven"]


def resolve(
    kind: str,
    constraint_str: str,
    store: dict[str, dict[str, dict[str, PluginEntry]]],
    kinds: set[str],
) -> PluginEntry:
    """Resolve a plugin by kind and name/version constraint."""
    if kind not in kinds:
        raise UnknownPluginKindError(f"Unknown plugin kind: {kind!r}")

    name, specifier = _parse_constraint(constraint_str)
    kind_store = store.get(kind, {})

    if name not in kind_store:
        raise PluginResolutionError(
            kind=kind,
            constraint=constraint_str,
            available=list(kind_store.keys()),
            reason="name not found",
        )

    versions = kind_store[name]
    compatible = [
        v
        for v in versions
        if Version(v) in specifier and _api_compatible(versions[v].meta)
    ]

    if not compatible:
        raise PluginResolutionError(
            kind=kind,
            constraint=constraint_str,
            available=list(versions.keys()),
            reason="no compatible version found",
        )

    best = max(compatible, key=Version)
    return versions[best]


def instantiate(
    plugin_class: type,
    config: PipelineConfig,
    store: dict[str, dict[str, dict[str, PluginEntry]]],
    kinds: set[str],
    _path: list[tuple[str, str]] | None = None,
) -> Any:
    """Recursively instantiate a plugin with sub-plugin injection."""
    if _path is None:
        _path = []

    meta: PluginMeta = plugin_class.meta
    key = (meta.kind, meta.name)

    if key in _path:
        raise CircularDependencyError(
            f"Circular dependency detected: {_path + [key]}"
        )

    kwargs: dict[str, Any] = {}
    for dep_kind, dep_constraint in meta.requires.items():
        constraint = (
            dep_constraint
            or config.plugins.params.get(dep_kind)
            or getattr(config.plugins, dep_kind, None)
        )
        if not constraint:
            raise PluginResolutionError(
                kind=dep_kind,
                constraint="",
                reason=f"required by {meta.name} but not found in config",
            )
        dep_entry = resolve(dep_kind, str(constraint), store, kinds)
        kwargs[dep_kind] = instantiate(
            dep_entry.plugin_class, config, store, kinds, _path + [key]
        )

    return plugin_class(**kwargs)


def validate_compatibility(plugins: dict[str, Any]) -> None:
    """Validate declared compatible_with constraints across all active plugins."""
    for plugin in plugins.values():
        meta: PluginMeta = plugin.meta
        for kind, allowed_names in meta.compatible_with.items():
            if kind not in plugins:
                continue
            active_name = plugins[kind].meta.name
            if active_name not in allowed_names:
                raise PluginCompatibilityError(
                    f"{meta.name!r} requires {kind!r} in {allowed_names}, "
                    f"but active plugin is {active_name!r}"
                )


def check_circular(
    plugin_class: type,
    store: dict[str, dict[str, dict[str, PluginEntry]]],
    _path: list[tuple[str, str]] | None = None,
) -> None:
    """Recursively check for circular dependencies starting from plugin_class."""
    if _path is None:
        _path = []

    meta: PluginMeta = plugin_class.meta
    key = (meta.kind, meta.name)

    if key in _path:
        raise CircularDependencyError(
            f"Circular dependency: {' -> '.join(f'{k}/{n}' for k, n in _path + [key])}"
        )

    for dep_kind, dep_name in meta.requires.items():
        if dep_name and dep_kind in store and dep_name in store[dep_kind]:
            versions = store[dep_kind][dep_name]
            if versions:
                latest = max(versions.keys(), key=Version)
                check_circular(versions[latest].plugin_class, store, _path + [key])


def _parse_constraint(constraint_str: str):
    """Split 'name>=1.0' into (name, SpecifierSet)."""
    from packaging.specifiers import SpecifierSet

    for op in (">=", "<=", "!=", "~=", "==", ">", "<"):
        if op in constraint_str:
            name, spec = constraint_str.split(op, 1)
            return name.strip(), SpecifierSet(op + spec.strip())

    return constraint_str.strip(), SpecifierSet("")


def _api_compatible(meta: PluginMeta) -> bool:
    """Check whether a plugin's declared API version range includes current API."""
    current = Version(_API_VERSION)
    if Version(meta.min_api_version) > current:
        return False
    if meta.max_api_version and Version(meta.max_api_version) < current:
        return False
    return True
