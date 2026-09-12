"""Unit tests for the SegregatrFLBCalculator plugin."""

from __future__ import annotations

import subprocess

import pytest

from heredicalc.core.exceptions import SegregaError, ZeroPenetranceError
from heredicalc.core.models.pedigree import Affection, Pedigree, PedigreeMember
from heredicalc.core.models.penetrance import PenetranceRow, PenetranceTable
from heredicalc.plugins.flb_calculators.segregatr import plugin as segregatr_plugin
from heredicalc.plugins.flb_calculators.segregatr.plugin import SegregatrFLBCalculator

_PHENO = "BreastCancer"
_F_AFFECTED, _F_UNAFFECTED, _M_AFFECTED, _M_UNAFFECTED = 0, 1, 2, 3


def _row(sex, phenotype, nc, het, hom) -> PenetranceRow:
    return PenetranceRow(
        age_start=0,
        age_end=99,
        sex=sex,
        phenotype=phenotype,
        is_affected=phenotype != "unaffected",
        penetrance_nc=nc,
        penetrance_het=het,
        penetrance_hom=hom,
    )


def _table() -> PenetranceTable:
    """Female rows carry data; male rows are all zero (female-only model)."""
    rows = [
        _row("F", _PHENO, 0.05, 0.30, 0.30),
        _row("F", "unaffected", 0.10, 0.50, 0.50),
        _row("M", _PHENO, 0.0, 0.0, 0.0),
        _row("M", "unaffected", 0.0, 0.0, 0.0),
    ]
    return PenetranceTable(genetic_entity="TESTGENE", population="test", rows=rows)


def _pedigree(son_affected: bool) -> Pedigree:
    son_affections = [Affection(phenotype="BrCa", age_at_diagnosis=38)] if son_affected else []
    return Pedigree(
        pedigree_id="synthetic_family",
        members=[
            PedigreeMember(individual_id=1, sex="M", age_last_contact=70),
            PedigreeMember(
                individual_id=2,
                sex="F",
                age_last_contact=70,
                genotype="Het",
                is_proband=True,
                affections=[Affection(phenotype="BrCa", age_at_diagnosis=45)],
            ),
            PedigreeMember(
                individual_id=3,
                father_id=1,
                mother_id=2,
                sex="M",
                age_last_contact=40,
                genotype="Het",
                affections=son_affections,
            ),
        ],
    )


def _liability_map(son_affected: bool) -> dict[int, int]:
    return {1: _M_UNAFFECTED, 2: _F_AFFECTED, 3: _M_AFFECTED if son_affected else _M_UNAFFECTED}


def _no_rscript(*args, **kwargs):
    pytest.fail("Rscript must not be invoked when the zero-penetrance guard fires")


def test_affected_member_in_zero_penetrance_class_raises_before_rscript(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", _no_rscript)
    with pytest.raises(ZeroPenetranceError) as info:
        SegregatrFLBCalculator().compute(
            _pedigree(son_affected=True), _table(), _liability_map(son_affected=True), 0.001, {}
        )
    exc = info.value
    assert exc.individual_id == 3
    assert exc.pedigree_id == "synthetic_family"
    assert exc.group == {"sex": "M", "phenotype": _PHENO, "age_band": "0-99"}


def test_zero_penetrance_error_is_not_wrapped_in_segrega_error(monkeypatch) -> None:
    sentinel = ZeroPenetranceError(3, {"sex": "M"})

    def _raise(*args, **kwargs):
        raise sentinel

    monkeypatch.setattr(segregatr_plugin, "_write_pedigree_tsv", _raise)
    with pytest.raises(ZeroPenetranceError) as info:
        SegregatrFLBCalculator().compute(
            _pedigree(son_affected=False), _table(), _liability_map(son_affected=False), 0.001, {}
        )
    assert info.value is sentinel


def test_unaffected_member_in_zero_penetrance_class_reaches_rscript(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(cmd, **kwargs):
        calls.append(cmd)
        stdout = '{"flb": 2.5, "r_session": {"r_version": "R 4.4.1"}}\n'
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    calc = SegregatrFLBCalculator()
    flb = calc.compute(
        _pedigree(son_affected=False), _table(), _liability_map(son_affected=False), 0.001, {}
    )
    assert flb == 2.5
    assert len(calls) == 1
    assert calc.session_info() == {"r_version": "R 4.4.1"}


def test_other_failures_are_still_wrapped_in_segrega_error(monkeypatch) -> None:
    monkeypatch.setattr(subprocess, "run", _no_rscript)
    incomplete_map = {1: _M_UNAFFECTED, 2: _F_AFFECTED}
    with pytest.raises(SegregaError):
        SegregatrFLBCalculator().compute(
            _pedigree(son_affected=False), _table(), incomplete_map, 0.001, {}
        )
