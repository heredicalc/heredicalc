"""Plugin metadata and specification models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class PluginMeta(BaseModel):
    """Metadata declared by every plugin."""

    name: str
    version: str
    kind: str
    description: str
    author: str
    min_api_version: str
    max_api_version: str | None = None
    requires: dict[str, str | None] = {}
    compatible_with: dict[str, list[str]] = {}


class PluginSpec(BaseModel):
    """Generic serialisable plugin specification for data-driven plugins."""

    meta: PluginMeta
    spec_type: str
    spec_data: dict[str, Any] = {}


class SourceInfo(BaseModel):
    """Metadata about one incidence data source (registry)."""

    source_id: str
    name: str
    study_period: str
    edition: str


class TraitInfo(BaseModel):
    """Metadata about one trait code in an incidence source."""

    trait_code: str
    name: str
    icd_code: str | None = None
