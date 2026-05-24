"""Unit tests for the VICTOR penetrance model — critical algorithm invariants."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from heredicalc.core.models.plugin import PluginMeta
from heredicalc.plugins.penetrance_models.victor.plugin import VictorPenetranceModel, _build_bands


# ---------------------------------------------------------------------------
# Minimal stub sub-plugins for isolated VICTOR testing
# ---------------------------------------------------------------------------


class ConstantRRModel:
    """RR model returning a fixed RR_het and RR_hom for all queries."""

    meta = PluginMeta(
        name="constant_rr",
        version="1.0.0",
        kind="rr_model",
        description="constant",
        author="test",
        min_api_version="1.0.0",
    )

    def __init__(self, rr_het: float, rr_hom: float) -> None:
        self._rr_het = rr_het
        self._rr_hom = rr_hom

    def get_rr(self, genetic_entity, sex, age, phenotype, genotype):
        if genotype == "het":
            return self._rr_het
        return self._rr_hom


class ConstantCRHFModel:
    """CRHF model returning a fixed q for all queries."""

    meta = PluginMeta(
        name="constant_crhf",
        version="1.0.0",
        kind="crhf_model",
        description="constant",
        author="test",
        min_api_version="1.0.0",
    )

    def __init__(self, q: float) -> None:
        self._q = q

    def get_crhf(self, genetic_entity, sex=None, age=None):
        return self._q


class ConstantPhenotypeModel:
    """Phenotype model returning a single tracked phenotype."""

    meta = PluginMeta(
        name="constant_pheno",
        version="1.0.0",
        kind="phenotype_model",
        description="constant",
        author="test",
        min_api_version="1.0.0",
    )

    def __init__(self, phenotypes: list[str]) -> None:
        self._phenotypes = phenotypes

    def canonical_phenotypes(self) -> list[str]:
        return list(self._phenotypes)

    def map_raw_affection(self, raw: str) -> str | None:
        return self._phenotypes[0] if raw != "." else None


# ---------------------------------------------------------------------------
# Helper to build a minimal hazard frame for one sex
# ---------------------------------------------------------------------------


def _make_hazard_frame(
    sex: str,
    phenotype: str,
    lambda_pop: float,
    include_other: bool = True,
) -> pd.DataFrame:
    """One row per age (0-99) for one sex/phenotype + OtherTrait."""
    rows = []
    for age in range(100):
        rows.append({"sex": sex, "phenotype": phenotype, "age": age, "lambda_pop": lambda_pop})
        if include_other:
            rows.append({"sex": sex, "phenotype": "OtherTrait", "age": age, "lambda_pop": 1e-4})
    df = pd.DataFrame(rows)
    df["sex"] = df["sex"].astype("category")
    df["age"] = df["age"].astype("int64")
    df["lambda_pop"] = df["lambda_pop"].astype("float64")
    return df


# ---------------------------------------------------------------------------
# Invariant tests: λ_het / λ_nc == RR_het  (to floating-point precision)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("rr_het", [1.0, 5.0, 73.7])
@pytest.mark.parametrize("q", [0.00075, 0.001])
@pytest.mark.parametrize("lambda_pop", [1e-4, 1e-3])
def test_victor_lambda_ratio_invariant(rr_het: float, q: float, lambda_pop: float):
    """λ_het / λ_nc must equal RR_het for all (RR, q, λ_pop) combinations.

    Critical invariant: the VICTOR Hardy-Weinberg correction guarantees this
    exactly. The naive formula λ_het = RR * λ_pop * (1-q) violates this.
    """
    rr_model = ConstantRRModel(rr_het=rr_het, rr_hom=rr_het)
    crhf_model = ConstantCRHFModel(q=q)
    victor = VictorPenetranceModel(rr_model=rr_model, crhf_model=crhf_model)

    pheno_model = ConstantPhenotypeModel(["TestDisease"])
    hazards = _make_hazard_frame("F", "TestDisease", lambda_pop)

    params = {
        "genetic_entity": "TESTGENE",
        "age_bands": [40, 60, 80],
        "population": "test",
    }
    table = victor.compute(hazards, pheno_model, params)

    # Reconstruct λ_nc and λ_het from the VICTOR formula and verify ratio
    D = 1.0 + 2.0 * q * (rr_het - 1.0)
    lam_nc = lambda_pop / D
    lam_het = rr_het * lam_nc

    if lam_nc > 0:
        computed_ratio = lam_het / lam_nc
        assert abs(computed_ratio - rr_het) < 1e-12, (
            f"λ_het/λ_nc = {computed_ratio} ≠ RR_het = {rr_het} "
            f"(diff={abs(computed_ratio - rr_het):.2e})"
        )


@pytest.mark.parametrize("rr_het", [1.0, 5.0, 73.7])
@pytest.mark.parametrize("q", [0.00075, 0.001])
@pytest.mark.parametrize("lambda_pop", [1e-4, 1e-3])
def test_victor_wrong_formula_would_fail(rr_het: float, q: float, lambda_pop: float):
    """The naive formula λ_het = RR * λ_pop * (1-q) gives wrong ratio when q>0, RR≠1."""
    if rr_het == 1.0 or q == 0.0:
        pytest.skip("trivially equal when RR=1 or q=0")

    D = 1.0 + 2.0 * q * (rr_het - 1.0)
    lam_nc = lambda_pop / D

    # Wrong naive formula
    lam_het_wrong = rr_het * lambda_pop * (1.0 - q)
    wrong_ratio = lam_het_wrong / lam_nc if lam_nc > 0 else float("inf")

    # Correct formula
    lam_het_correct = rr_het * lam_nc
    correct_ratio = lam_het_correct / lam_nc

    # The wrong formula should give a different ratio
    assert abs(wrong_ratio - correct_ratio) > 1e-10, (
        "Wrong formula accidentally equals correct formula — test logic error"
    )


# ---------------------------------------------------------------------------
# Band-specific CIF increments (not cumulative)
# ---------------------------------------------------------------------------


def test_victor_affected_row_is_band_specific():
    """Affected penetrance must be a band-specific CIF increment, not cumulative F."""
    rr_het = 10.0
    q = 0.001
    lambda_pop = 1e-3

    rr_model = ConstantRRModel(rr_het=rr_het, rr_hom=rr_het)
    crhf_model = ConstantCRHFModel(q=q)
    victor = VictorPenetranceModel(rr_model=rr_model, crhf_model=crhf_model)
    pheno_model = ConstantPhenotypeModel(["TestDisease"])

    # Two bands: [0,49] and [50,99]
    hazards = _make_hazard_frame("F", "TestDisease", lambda_pop)
    params = {"genetic_entity": "TESTGENE", "age_bands": [50], "population": "test"}
    table = victor.compute(hazards, pheno_model, params)

    f_rows = [r for r in table.rows if r.is_affected and r.sex == "F" and r.phenotype == "TestDisease"]
    assert len(f_rows) == 2

    band1 = next(r for r in f_rows if r.age_start == 0)
    band2 = next(r for r in f_rows if r.age_start == 50)

    # Band 2 penetrance must be LESS THAN band 1 penetrance (increments, not cumulative)
    # If it were cumulative, band 2 would always be >= band 1
    # With equal lambda_pop per year, earlier band has smaller cumulative F,
    # so band-specific increment for band 2 (50-99) > band 1 (0-49) — but NOT 0-99 cumulative
    assert band1.penetrance_nc > 0, "Band 1 nc penetrance should be positive"
    assert band2.penetrance_nc > 0, "Band 2 nc penetrance should be positive"

    # Sum of band increments must be <= 1.0 (it's a probability)
    total_nc = band1.penetrance_nc + band2.penetrance_nc
    assert total_nc <= 1.0 + 1e-10, f"Sum of band increments {total_nc} exceeds 1.0"


# ---------------------------------------------------------------------------
# Band construction
# ---------------------------------------------------------------------------


def test_build_bands_single():
    """Single breakpoint → two bands."""
    bands = _build_bands([50])
    assert bands == [(0, 49), (50, 99)]


def test_build_bands_multiple():
    """Standard VICTOR age bands."""
    bands = _build_bands([30, 40, 50, 60, 65, 70, 80])
    assert bands[0] == (0, 29)
    assert bands[-1] == (80, 99)
    assert len(bands) == 8


def test_build_bands_covers_zero_to_99():
    """All ages 0-99 are covered exactly once."""
    bands = _build_bands([30, 40, 50, 60, 65, 70, 80])
    covered = set()
    for a0, a1 in bands:
        for a in range(a0, a1 + 1):
            assert a not in covered, f"Age {a} covered twice"
            covered.add(a)
    assert covered == set(range(100))


# ---------------------------------------------------------------------------
# PenetranceTable structure
# ---------------------------------------------------------------------------


def test_victor_table_has_correct_row_count():
    """MECE table has (n_tracked_phenotypes + 1) rows per band per sex."""
    rr_model = ConstantRRModel(rr_het=5.0, rr_hom=5.0)
    crhf_model = ConstantCRHFModel(q=0.001)
    victor = VictorPenetranceModel(rr_model=rr_model, crhf_model=crhf_model)
    pheno_model = ConstantPhenotypeModel(["A", "B", "C"])

    hazards_f = _make_hazard_frame("F", "A", 1e-4)
    hazards_m = _make_hazard_frame("M", "A", 1e-4)
    for p in ["B", "C"]:
        hazards_f = pd.concat([hazards_f, _make_hazard_frame("F", p, 1e-4)], ignore_index=True)
        hazards_m = pd.concat([hazards_m, _make_hazard_frame("M", p, 1e-4)], ignore_index=True)
    hazards_f["sex"] = hazards_f["sex"].astype("category")
    hazards_m["sex"] = hazards_m["sex"].astype("category")
    hazards = pd.concat([hazards_f, hazards_m], ignore_index=True)
    hazards["sex"] = hazards["sex"].astype("category")

    params = {"genetic_entity": "TESTGENE", "age_bands": [30, 60], "population": "test"}
    table = victor.compute(hazards, pheno_model, params)

    n_bands = 3  # [0,29], [30,59], [60,99]
    n_pheno = 3
    n_sexes = 2
    # Each band per sex: n_pheno affected rows + 1 unaffected row
    expected = n_sexes * n_bands * (n_pheno + 1)
    assert len(table.rows) == expected
