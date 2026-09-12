"""Unit tests for the VictorStandardLiabilityAssigner plugin."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from heredicalc.core.exceptions import ZeroPenetranceError
from heredicalc.core.models.pedigree import Affection, PedigreeMember
from heredicalc.core.models.penetrance import PenetranceRow, PenetranceTable
from heredicalc.plugins.liability_assigners.victor_standard.plugin import (
    VictorStandardLiabilityAssigner,
)
from heredicalc.plugins.penetrance_models.victor.plugin import VictorPenetranceModel
from tests.unit.test_victor import ConstantCRHFModel, ConstantPhenotypeModel, ConstantRRModel

_PHENO = "BreastCancer"


class _PhenotypeModel:
    def canonical_phenotypes(self) -> list[str]:
        return [_PHENO]

    def map_raw_affection(self, raw: str) -> str | None:
        return None if raw == "." else _PHENO


def _row(sex, phenotype, age_start, age_end, nc, het, hom) -> PenetranceRow:
    return PenetranceRow(
        age_start=age_start,
        age_end=age_end,
        sex=sex,
        phenotype=phenotype,
        is_affected=phenotype != "unaffected",
        penetrance_nc=nc,
        penetrance_het=het,
        penetrance_hom=hom,
    )


def _table(male_value: float = 0.0) -> PenetranceTable:
    """Female rows carry data; male rows carry *male_value* everywhere (female-only model)."""
    rows = [
        _row("F", _PHENO, 0, 49, 0.01, 0.05, 0.05),
        _row("F", "unaffected", 0, 49, 0.02, 0.10, 0.10),
        _row("F", _PHENO, 50, 99, 0.03, 0.12, 0.12),
        _row("F", "unaffected", 50, 99, 0.08, 0.30, 0.30),
        _row("M", _PHENO, 0, 49, male_value, male_value, male_value),
        _row("M", "unaffected", 0, 49, male_value, male_value, male_value),
        _row("M", _PHENO, 50, 99, male_value, male_value, male_value),
        _row("M", "unaffected", 50, 99, male_value, male_value, male_value),
    ]
    return PenetranceTable(genetic_entity="TESTGENE", population="test", rows=rows)


def _affected(individual_id: int, sex: str, age: int) -> PedigreeMember:
    return PedigreeMember(
        individual_id=individual_id,
        sex=sex,
        age_last_contact=age,
        affections=[Affection(phenotype="BrCa", age_at_diagnosis=age)],
    )


def _assign(member: PedigreeMember, table: PenetranceTable) -> int:
    return VictorStandardLiabilityAssigner().assign(member, table, _PhenotypeModel(), {})


def test_affected_member_with_zero_penetrance_raises() -> None:
    with pytest.raises(ZeroPenetranceError) as info:
        _assign(_affected(3, "M", 38), _table())
    exc = info.value
    assert exc.individual_id == 3
    assert exc.group == {"sex": "M", "phenotype": _PHENO, "age_band": "0-49"}
    assert exc.pedigree_id is None


def test_affected_member_with_undefined_penetrance_raises() -> None:
    with pytest.raises(ZeroPenetranceError):
        _assign(_affected(3, "M", 38), _table(male_value=math.nan))


def test_unaffected_member_with_zero_penetrance_is_assigned() -> None:
    member = PedigreeMember(individual_id=1, sex="M", age_last_contact=70)
    assert _assign(member, _table()) == 7


def test_affected_member_with_penetrance_is_assigned() -> None:
    assert _assign(_affected(2, "F", 45), _table()) == 0


def test_female_only_victor_model_raises_only_for_affected_males() -> None:
    """VICTOR emits all-zero male rows when the hazards have no male data."""
    ages = range(100)
    hazards = pd.DataFrame(
        [{"sex": "F", "phenotype": _PHENO, "age": a, "lambda_pop": 1e-3} for a in ages]
        + [{"sex": "F", "phenotype": "OtherTrait", "age": a, "lambda_pop": 1e-4} for a in ages]
    )
    hazards["sex"] = hazards["sex"].astype("category")
    victor = VictorPenetranceModel(
        rr_model=ConstantRRModel(rr_het=5.0, rr_hom=5.0), crhf_model=ConstantCRHFModel(q=0.001)
    )
    pheno_model = ConstantPhenotypeModel([_PHENO])
    params = {"genetic_entity": "TESTGENE", "age_bands": [50], "population": "test"}
    table = victor.compute(hazards, pheno_model, params)
    assigner = VictorStandardLiabilityAssigner()

    with pytest.raises(ZeroPenetranceError) as info:
        assigner.assign(_affected(3, "M", 38), table, pheno_model, params)
    assert info.value.group["sex"] == "M"

    unaffected_male = PedigreeMember(individual_id=1, sex="M", age_last_contact=70)
    index = assigner.assign(unaffected_male, table, pheno_model, params)
    assert table.rows[index].sex == "M"
    assert not table.rows[index].is_affected

    index = assigner.assign(_affected(2, "F", 45), table, pheno_model, params)
    assert table.rows[index].has_penetrance
