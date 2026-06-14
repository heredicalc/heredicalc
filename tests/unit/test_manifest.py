"""Unit tests for the run-provenance manifest model and the runner cascade."""

from __future__ import annotations

import hashlib
from pathlib import Path

from heredicalc.core.pipeline.config import ComputationConfig, PipelineConfig, PluginConfig
from heredicalc.core.pipeline.manifest import (
    InputFile,
    PluginRef,
    RSessionInfo,
    RunManifest,
    collect_python_packages,
    file_sha256,
)
from heredicalc.core.pipeline.runner import PipelineRunner
from heredicalc.core.registry.registry import PluginRegistry

_REGISTRY: PluginRegistry | None = None


def _registry() -> PluginRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PluginRegistry()
        _REGISTRY.discover_all()
    return _REGISTRY


def _config(penetrance_model: str = "victor") -> PipelineConfig:
    return PipelineConfig(
        computation=ComputationConfig(genetic_entity="BRCA1", allele_freq=0.0001),
        plugins=PluginConfig(
            incidence_source="ci5_ix",
            phenotype_model="hbopc",
            trait_mapper="ci5_ix_hbopc",
            penetrance_model=penetrance_model,
            params={"population": "Latvia", "rr_model": "tabular", "crhf_model": "lookup"},
        ),
    )


def _manifest() -> RunManifest:
    return RunManifest(
        heredicalc_version="4.0.0",
        python_version="3.12.4",
        python_packages={"pandas": "2.2.0", "heredicalc": "4.0.0"},
        r_session=RSessionInfo(
            r_version="R version 4.4.1 (2024-06-14)",
            platform="aarch64-apple-darwin20",
            loaded_namespaces={"segregatr": "0.5.0", "pedtools": "2.7.0"},
        ),
        resolved_config=_config(),
        inputs=[InputFile(filename="Belman.ped", sha256="0" * 64)],
        plugins=[PluginRef(kind="flb_calculator", name="segregatr", version="1.0.0")],
        timestamp_utc="2026-06-14T12:00:00+00:00",
        flb=25.6540503665,
    )


def test_manifest_round_trips_through_json() -> None:
    manifest = _manifest()
    restored = RunManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest
    assert restored.resolved_config.computation.genetic_entity == "BRCA1"
    assert restored.r_session is not None
    assert restored.r_session.loaded_namespaces["segregatr"] == "0.5.0"


def test_manifest_coerces_r_session_dict() -> None:
    # The runner passes the raw parsed dict straight into the constructor, which
    # validates and coerces it into an RSessionInfo (model_copy would not).
    base = _manifest()
    manifest = RunManifest(
        heredicalc_version=base.heredicalc_version,
        python_version=base.python_version,
        python_packages=base.python_packages,
        r_session={
            "r_version": "R version 4.4.1 (2024-06-14)",
            "platform": "aarch64-apple-darwin20",
            "loaded_namespaces": {"segregatr": "0.5.0"},
        },
        resolved_config=base.resolved_config,
        inputs=base.inputs,
        plugins=base.plugins,
        timestamp_utc=base.timestamp_utc,
        flb=base.flb,
    )
    assert isinstance(manifest.r_session, RSessionInfo)
    assert manifest.r_session.platform == "aarch64-apple-darwin20"


def test_file_sha256_matches_hashlib_and_is_reproducible(tmp_path: Path) -> None:
    data = b"individual_id\tfather_id\n1\t0\n2\t1\n"
    ped = tmp_path / "sample.ped"
    ped.write_bytes(data)
    expected = hashlib.sha256(data).hexdigest()
    assert file_sha256(ped) == expected
    assert file_sha256(ped) == file_sha256(ped)


def test_collect_python_packages_includes_core_deps() -> None:
    packages = collect_python_packages()
    assert "pandas" in packages
    assert "pydantic" in packages
    assert all(isinstance(v, str) and v for v in packages.values())


def test_resolved_config_reflects_penetrance_defaults_cascade() -> None:
    runner = PipelineRunner(registry=_registry())
    # victor_cool3 declares defaults={"hazard_model": "annual_rate_cool3"}.
    resolved = runner._resolve_config(_config(penetrance_model="victor_cool3"))
    assert resolved.plugins.hazard_model == "annual_rate_cool3"


def test_resolved_config_unchanged_when_no_defaults() -> None:
    runner = PipelineRunner(registry=_registry())
    # victor declares no defaults; the field default must be left untouched.
    config = _config(penetrance_model="victor")
    resolved = runner._resolve_config(config)
    assert resolved.plugins.hazard_model == "annual_rate"
    assert resolved == config


def test_explicit_field_overrides_cascade() -> None:
    runner = PipelineRunner(registry=_registry())
    config = PipelineConfig(
        computation=ComputationConfig(genetic_entity="BRCA1", allele_freq=0.0001),
        plugins=PluginConfig(
            incidence_source="ci5_ix",
            phenotype_model="hbopc",
            trait_mapper="ci5_ix_hbopc",
            penetrance_model="victor_cool3",
            hazard_model="annual_rate",
            params={"population": "Latvia"},
        ),
    )
    # hazard_model was set explicitly, so the cascade must not override it.
    resolved = runner._resolve_config(config)
    assert resolved.plugins.hazard_model == "annual_rate"


def test_collect_plugins_covers_all_ten_kinds() -> None:
    runner = PipelineRunner(registry=_registry())
    refs = runner._collect_plugins(_config())
    kinds = {r.kind for r in refs}
    assert len(refs) == 10
    assert {"rr_model", "crhf_model", "flb_calculator", "penetrance_model"} <= kinds
    by_kind = {r.kind: r for r in refs}
    assert by_kind["flb_calculator"].name == "segregatr"
    assert by_kind["rr_model"].name == "tabular"
    assert by_kind["crhf_model"].name == "lookup"
    assert all(r.version for r in refs)
