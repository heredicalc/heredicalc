"""Unit tests for the VictorStandardLiabilityAssigner plugin."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from heredicalc.core.exceptions import UnknownAgeError, ZeroPenetranceError
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


# --- composite classes: an affection that is one of several tracked phenotypes -------------

_OTHER = "OvarianCancer"


class _MultiPhenotypeModel:
    """Tracks two phenotypes; ``BC_any`` means "one of them, subtype unknown"."""

    def canonical_phenotypes(self) -> list[str]:
        return [_PHENO, _OTHER]

    def map_raw_affection(self, raw: str) -> str | list[str] | None:
        return {
            ".": None,
            "unaff": None,
            "BrCa": _PHENO,
            "OvCa": _OTHER,
            "BC_any": [_PHENO, _OTHER],
            "BC_single_list": [_PHENO],
            "BC_dup_list": [_PHENO, _PHENO],
        }[raw]


def _two_phenotype_table() -> PenetranceTable:
    rows = [
        _row("F", _PHENO, 0, 49, 0.010, 0.050, 0.060),
        _row("F", _OTHER, 0, 49, 0.002, 0.004, 0.005),
        _row("F", "unaffected", 0, 49, 0.020, 0.100, 0.110),
        _row("F", _PHENO, 50, 99, 0.030, 0.120, 0.130),
        _row("F", _OTHER, 50, 99, 0.008, 0.016, 0.017),
        _row("F", "unaffected", 50, 99, 0.080, 0.300, 0.310),
        _row("M", _PHENO, 0, 49, 0.001, 0.002, 0.002),
        _row("M", _OTHER, 0, 49, 0.0, 0.0, 0.0),
        _row("M", "unaffected", 0, 49, 0.003, 0.004, 0.004),
        _row("M", _PHENO, 50, 99, 0.0, 0.0, 0.0),
        _row("M", _OTHER, 50, 99, 0.0, 0.0, 0.0),
        _row("M", "unaffected", 50, 99, 0.0, 0.0, 0.0),
    ]
    return PenetranceTable(genetic_entity="TESTGENE", population="test", rows=rows)


def _member(individual_id: int, sex: str, age: int, raw: str | None) -> PedigreeMember:
    affections = [] if raw is None else [Affection(phenotype=raw, age_at_diagnosis=age)]
    known = raw != "."
    return PedigreeMember(
        individual_id=individual_id,
        sex=sex,
        age_last_contact=age,
        affections=affections,
        affection_known=known,
    )


def _assign_multi(member: PedigreeMember, table: PenetranceTable) -> int:
    return VictorStandardLiabilityAssigner().assign(member, table, _MultiPhenotypeModel(), {})


@pytest.mark.parametrize(
    ("sex", "age", "band"), [("F", 30, (0, 49)), ("F", 60, (50, 99)), ("M", 30, (0, 49))]
)
def test_composite_row_is_the_column_wise_sum(sex: str, age: int, band: tuple[int, int]) -> None:
    table = _two_phenotype_table()
    n_before = len(table.rows)
    idx = _assign_multi(_member(1, sex, age, "BC_any"), table)
    row = table.rows[idx]
    parts = [
        r
        for r in table.rows[:n_before]
        if r.sex == sex and r.phenotype in (_PHENO, _OTHER) and (r.age_start, r.age_end) == band
    ]
    assert len(parts) == 2
    assert row.penetrance_nc == pytest.approx(sum(r.penetrance_nc for r in parts))
    assert row.penetrance_het == pytest.approx(sum(r.penetrance_het for r in parts))
    assert row.penetrance_hom == pytest.approx(sum(r.penetrance_hom for r in parts))
    assert (row.sex, row.age_start, row.age_end) == (sex, *band)
    assert row.phenotype == f"{_PHENO}|{_OTHER}"


def test_composite_row_is_an_affected_class_appended_to_the_table() -> None:
    table = _two_phenotype_table()
    n_before = len(table.rows)
    idx = _assign_multi(_member(1, "F", 30, "BC_any"), table)
    assert idx == n_before and len(table.rows) == n_before + 1
    assert table.rows[idx].is_affected is True
    assert table.rows[idx].has_penetrance
    # a second member with the same sex and band reuses the class instead of appending
    assert _assign_multi(_member(2, "F", 45, "BC_any"), table) == idx
    assert len(table.rows) == n_before + 1
    # a different band gets its own composite class
    idx2 = _assign_multi(_member(3, "F", 70, "BC_any"), table)
    assert idx2 == n_before + 1 and table.rows[idx2].age_start == 50


def test_single_phenotype_is_unchanged_by_the_composite_path() -> None:
    table = _two_phenotype_table()
    plain = _assign_multi(_member(1, "F", 30, "BrCa"), table)
    assert table.rows[plain].phenotype == _PHENO and plain < 12
    assert _assign_multi(_member(2, "F", 30, "BC_single_list"), table) == plain
    assert _assign_multi(_member(3, "F", 30, "BC_dup_list"), table) == plain
    assert len(table.rows) == 12  # nothing appended


def test_unknown_affection_stays_on_the_unaffected_path() -> None:
    table = _two_phenotype_table()
    idx = _assign_multi(_member(1, "F", 30, "."), table)
    assert table.rows[idx].phenotype == "unaffected" and not table.rows[idx].is_affected
    assert _assign_multi(_member(2, "F", 30, "unaff"), table) == idx
    assert len(table.rows) == 12


def test_composite_without_penetrance_raises_like_a_single_class() -> None:
    table = _two_phenotype_table()
    with pytest.raises(ZeroPenetranceError) as info:
        _assign_multi(_member(1, "M", 60, "BC_any"), table)  # both male rows 50-99 are zero
    assert info.value.group["phenotype"] == f"{_PHENO}|{_OTHER}"


def test_composite_candidate_without_row_raises_value_error() -> None:
    table = _two_phenotype_table()
    table.rows = [r for r in table.rows if r.phenotype != _OTHER]
    with pytest.raises(ValueError, match="No penetrance row"):
        _assign_multi(_member(1, "F", 30, "BC_any"), table)


# --- unaffected members without age: no silent 99 any more ------------------------------


def _unaffected(individual_id: int, sex: str, age: int | None) -> PedigreeMember:
    return PedigreeMember(individual_id=individual_id, sex=sex, age_last_contact=age)


def _assign_params(member: PedigreeMember, table: PenetranceTable, params: dict) -> int:
    return VictorStandardLiabilityAssigner().assign(member, table, _PhenotypeModel(), params)


def test_unaffected_without_age_and_without_policy_raises() -> None:
    with pytest.raises(UnknownAgeError) as info:
        _assign_params(_unaffected(7, "F", None), _table(), {})
    assert info.value.individual_id == 7
    assert "unaffected_unknown_age" in str(info.value)


def test_unaffected_without_age_uninformative_policy_uses_the_sex_u_slot() -> None:
    table = _table()
    idx = _assign_params(
        _unaffected(7, "F", None), table, {"unaffected_unknown_age": "uninformative"}
    )
    u_member = PedigreeMember(individual_id=8, sex="U", age_last_contact=None)
    assert idx == _assign_params(u_member, table, {})
    row = table.rows[idx]
    assert row.penetrance_nc == row.penetrance_het == row.penetrance_hom


def test_unaffected_without_age_fixed_policy_reproduces_the_old_behaviour() -> None:
    table = _table()
    idx = _assign_params(_unaffected(7, "F", None), table, {"unaffected_unknown_age": 99})
    assert idx == _assign_params(_unaffected(9, "F", 99), table, {})
    assert table.rows[idx].phenotype == "unaffected" and table.rows[idx].age_end == 99
    idx_young = _assign_params(_unaffected(7, "F", None), table, {"unaffected_unknown_age": 30})
    assert idx_young == _assign_params(_unaffected(9, "F", 30), table, {})


@pytest.mark.parametrize(
    "params", [{}, {"unaffected_unknown_age": "uninformative"}, {"unaffected_unknown_age": 99}]
)
def test_known_age_is_unchanged_by_the_policy(params: dict) -> None:
    table = _table()
    assert _assign_params(_unaffected(1, "F", 30), table, params) == 1
    assert _assign_params(_unaffected(2, "F", 60), table, params) == 3
    assert _assign_params(_affected(3, "F", 45), table, params) == 0  # affected path untouched


def test_invalid_policy_raises_value_error() -> None:
    with pytest.raises(ValueError, match="unaffected_unknown_age"):
        _assign_params(_unaffected(7, "F", None), _table(), {"unaffected_unknown_age": "guess"})
    with pytest.raises(ValueError, match="unaffected_unknown_age"):
        _assign_params(_unaffected(7, "F", None), _table(), {"unaffected_unknown_age": True})


def test_untracked_affection_without_age_follows_the_same_policy() -> None:
    """The untracked-affection path is an unaffected path too (v4.4.0) and must not assume 99."""
    member = PedigreeMember(
        individual_id=7, sex="F", age_last_contact=None,
        affections=[Affection(phenotype=".", age_at_diagnosis=None)],
    )  # fmt: skip
    with pytest.raises(UnknownAgeError):
        _assign_params(member, _table(), {})
    assert _assign_params(member, _table(), {"unaffected_unknown_age": 99}) == 3
