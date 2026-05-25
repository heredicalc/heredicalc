"""Integration tests: validate FLB against COOL3 v3 reference values using COOL3-compatible plugins.

All 226 Belman pedigree permutations are parametrized from
tests/fixtures/validation_fixtures_cool3.json. Each case asserts that the
computed FLB (using ``annual_rate_cool3`` + ``victor_cool3`` + ``ci5_hbopc_cool3``) is
within ``tolerance_pct`` of ``reference_flb`` (COOL3 v3 reference values).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from heredicalc.core.pipeline.config import ComputationConfig, PipelineConfig, PluginConfig
from heredicalc.core.pipeline.runner import PipelineRunner
from heredicalc.core.registry.registry import PluginRegistry

_FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
_PEDIGREES_DIR = _FIXTURES_DIR / "pedigrees"
_FIXTURES_FILE = _FIXTURES_DIR / "validation_fixtures_cool3.json"


def _load_cases() -> list[dict[str, Any]]:
    if not _FIXTURES_FILE.exists():
        return []
    with open(_FIXTURES_FILE) as f:
        return json.load(f)["validation_cases"]


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
            hazard_model="annual_rate_cool3",
            penetrance_model="victor_cool3",
            params=params,
        ),
    )


_CASES = _load_cases()

_REGISTRY: PluginRegistry | None = None


def _get_registry() -> PluginRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = PluginRegistry()
        _REGISTRY.discover_all()
    return _REGISTRY


@pytest.mark.skipif(not _CASES, reason="validation_fixtures_cool3.json not found")
@pytest.mark.parametrize(
    "case",
    _CASES,
    ids=[c["id"] for c in _CASES],
)
def test_flb_within_tolerance_cool3(case: dict[str, Any]) -> None:
    ped_path = _PEDIGREES_DIR / case["pedigree"]
    if not ped_path.exists():
        pytest.skip(f"Pedigree file not found: {ped_path}")

    config = _fixture_to_config(case["config"])
    runner = PipelineRunner(registry=_get_registry())
    flb = runner.run(ped_path, config)

    ref = case["reference_flb"]
    tol = case["tolerance_pct"] / 100.0

    assert flb == pytest.approx(ref, rel=tol), (
        f"FLB {flb:.4f} deviates from COOL3 reference {ref:.4f} "
        f"by more than {case['tolerance_pct']}% "
        f"(case: {case['id']})"
    )
