"""Shared construction of a PipelineConfig from a plain dict."""

from __future__ import annotations

from typing import Any

from heredicalc.core.pipeline.config import ComputationConfig, PipelineConfig, PluginConfig


def build_config_from_dict(raw: dict[str, Any]) -> PipelineConfig:
    """Build a PipelineConfig from a ``{"computation": {...}, "plugins": {...}}`` dict.

    Shared by the CLI (after merging YAML + flags) and the web app (from widgets)
    so both produce an identical resolved configuration for the same inputs.
    """
    computation = raw.get("computation", {})
    plugins = raw.get("plugins", {})
    return PipelineConfig(
        computation=ComputationConfig(**computation),
        plugins=PluginConfig(**plugins),
    )
