"""Integration test: run_with_manifest for the primary BRCA1/Belman reference case.

Uses penetrance_model ``victor`` and the ``brca1_belman_latvia_ci5ix`` entry from
tests/fixtures/validation_fixtures.json. ``reference_flb`` and ``tolerance_pct`` are
read from the fixture entry, never hardcoded.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from heredicalc.core.pipeline.config import ComputationConfig, PipelineConfig, PluginConfig
from heredicalc.core.pipeline.manifest import RunManifest
from heredicalc.core.pipeline.runner import PipelineRunner
from heredicalc.core.registry.registry import PluginRegistry
from tests._ci5_support import requires_real_ci5_data

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_PEDIGREES_DIR = _FIXTURES_DIR / "pedigrees"
_FIXTURES_FILE = _FIXTURES_DIR / "validation_fixtures.json"
_CASE_ID = "brca1_belman_latvia_ci5ix"


def _load_case() -> dict[str, Any] | None:
    if not _FIXTURES_FILE.exists():
        return None
    with open(_FIXTURES_FILE) as f:
        cases = json.load(f)["validation_cases"]
    for case in cases:
        if case["id"] == _CASE_ID:
            return case
    return None


def _fixture_to_config(cfg: dict[str, Any]) -> PipelineConfig:
    params: dict[str, Any] = {
        "population": cfg.get("population", ""),
        "age_bands": cfg.get("age_bands", [30, 40, 50, 60, 65, 70, 80]),
        "rr_model": cfg.get("rr_model", "tabular"),
        "crhf_model": cfg.get("crhf_model", "lookup"),
    }
    return PipelineConfig(
        computation=ComputationConfig(
            genetic_entity=cfg["gene"],
            allele_freq=cfg["allele_freq"],
        ),
        plugins=PluginConfig(
            incidence_source=cfg["incidence_source"],
            phenotype_model=cfg["phenotype_model"],
            trait_mapper="ci5_ix_hbopc",
            penetrance_model=cfg["penetrance_model"],
            params=params,
        ),
    )


_CASE = _load_case()

_REGISTRY: PluginRegistry | None = None


def _get_registry() -> PluginRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PluginRegistry()
        _REGISTRY.discover_all()
    return _REGISTRY


@requires_real_ci5_data
@pytest.mark.skipif(_CASE is None, reason="reference case not found in validation_fixtures.json")
def test_run_with_manifest_reference_case() -> None:
    assert _CASE is not None
    ped_path = _PEDIGREES_DIR / _CASE["pedigree"]
    if not ped_path.exists():
        pytest.skip(f"Pedigree file not found: {ped_path}")

    config = _fixture_to_config(_CASE["config"])
    runner = PipelineRunner(registry=_get_registry())
    manifest = runner.run_with_manifest(ped_path, config)

    ref = _CASE["reference_flb"]
    tol = _CASE["tolerance_pct"] / 100.0
    assert manifest.flb == pytest.approx(ref, rel=tol), (
        f"manifest.flb {manifest.flb:.4f} deviates from reference {ref:.4f} "
        f"by more than {_CASE['tolerance_pct']}%"
    )

    # R session provenance is populated.
    assert manifest.r_session is not None
    assert manifest.r_session.r_version
    assert manifest.r_session.platform
    assert "segregatr" in manifest.r_session.loaded_namespaces

    # Python environment is captured.
    assert "pandas" in manifest.python_packages
    assert "pydantic" in manifest.python_packages
    assert manifest.python_version
    assert manifest.heredicalc_version

    # All ten plugin selections recorded, including injected sub-plugins.
    kinds = {p.kind for p in manifest.plugins}
    assert len(manifest.plugins) == 10
    assert {"rr_model", "crhf_model", "penetrance_model", "flb_calculator"} <= kinds

    # Input hash matches the raw pedigree bytes.
    assert manifest.inputs[0].filename == _CASE["pedigree"]
    assert manifest.inputs[0].sha256 == hashlib.sha256(ped_path.read_bytes()).hexdigest()

    # resolved_config reflects the effective parameters.
    assert manifest.resolved_config.plugins.penetrance_model == "victor"
    assert manifest.resolved_config.computation.genetic_entity == "BRCA1"

    # Manifest is fully serialisable and round-trips.
    RunManifest.model_validate_json(manifest.model_dump_json())
