"""Run-provenance manifest models for reproducible FLB runs."""

from __future__ import annotations

import hashlib
import platform
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import BaseModel

from heredicalc.core.pipeline.config import PipelineConfig

# Runtime dependencies declared in pyproject, plus heredicalc itself.
_RUNTIME_PACKAGES = (
    "pandas",
    "numpy",
    "pydantic",
    "packaging",
    "platformdirs",
    "PyYAML",
    "typer",
    "rich",
    "heredicalc",
)


class RSessionInfo(BaseModel):
    """R version, platform, and loaded namespaces captured after the FLB call."""

    r_version: str
    platform: str
    loaded_namespaces: dict[str, str]


class InputFile(BaseModel):
    """A pedigree input file recorded by filename and content hash."""

    filename: str
    sha256: str


class PluginRef(BaseModel):
    """A plugin actually used in a run, by kind, name, and version."""

    kind: str
    name: str
    version: str


class RunManifest(BaseModel):
    """Machine-readable record fully documenting one FLB run for reproduction."""

    heredicalc_version: str
    python_version: str
    python_packages: dict[str, str]
    r_session: RSessionInfo | None
    resolved_config: PipelineConfig
    inputs: list[InputFile]
    plugins: list[PluginRef]
    timestamp_utc: str
    flb: float


def file_sha256(path: Path) -> str:
    """Return the hex SHA-256 over the raw bytes of *path*."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect_python_packages() -> dict[str, str]:
    """Resolve installed versions of the declared runtime dependencies."""
    result: dict[str, str] = {}
    for pkg in _RUNTIME_PACKAGES:
        try:
            result[pkg] = version(pkg)
        except PackageNotFoundError:
            continue
    return result


def heredicalc_version() -> str:
    """Return the installed heredicalc version, or ``"unknown"``."""
    try:
        return version("heredicalc")
    except PackageNotFoundError:
        return "unknown"


def python_version() -> str:
    """Return the running CPython version, e.g. ``"3.12.4"``."""
    return platform.python_version()


def current_timestamp_utc() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()
