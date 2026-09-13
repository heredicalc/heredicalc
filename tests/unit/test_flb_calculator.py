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


def _capture_pedigree_tsv(monkeypatch) -> list[dict[str, str]]:
    """Run the calculator with a fake Rscript and return the pedigree TSV rows it received."""
    rows: list[dict[str, str]] = []

    def _fake_run(cmd, **kwargs):
        with open(cmd[3], encoding="utf-8") as fh:
            header = fh.readline().rstrip("\n").split("\t")
            rows.extend(
                dict(zip(header, line.rstrip("\n").split("\t"), strict=True)) for line in fh
            )
        return subprocess.CompletedProcess(cmd, 0, stdout='{"flb": 1.0}\n', stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    return rows


def test_affected_flag_follows_the_assigned_liability_class(monkeypatch) -> None:
    """An affection the phenotype model does not track leaves the member in an unaffected
    class; the flag handed to R must then say unaffected, not the raw pedigree status."""
    rows = _capture_pedigree_tsv(monkeypatch)
    # member 2 is affected in the pedigree but was assigned the female *unaffected* class
    liability_map = {1: _M_UNAFFECTED, 2: _F_UNAFFECTED, 3: _M_UNAFFECTED}
    SegregatrFLBCalculator().compute(
        _pedigree(son_affected=False), _table(), liability_map, 0.001, {}
    )
    by_id = {r["individual_id"]: r for r in rows}
    assert by_id["2"]["is_affected"] == "0"
    assert by_id["2"]["affection_known"] == "1"
    assert by_id["2"]["liability_class"] == str(_F_UNAFFECTED)


def test_tracked_affection_is_still_passed_as_affected(monkeypatch) -> None:
    rows = _capture_pedigree_tsv(monkeypatch)
    SegregatrFLBCalculator().compute(
        _pedigree(son_affected=False), _table(), _liability_map(son_affected=False), 0.001, {}
    )
    by_id = {r["individual_id"]: r for r in rows}
    assert by_id["2"]["is_affected"] == "1" and by_id["2"]["liability_class"] == str(_F_AFFECTED)
    assert by_id["1"]["is_affected"] == "0" and by_id["3"]["is_affected"] == "0"


def test_untracked_affection_in_zero_penetrance_class_does_not_raise(monkeypatch) -> None:
    """A male with an untracked affection sits in the (all-zero) male unaffected class: he is
    passed as unaffected and contributes a factor of 1, so the guard must not fire."""
    rows = _capture_pedigree_tsv(monkeypatch)
    liability_map = {1: _M_UNAFFECTED, 2: _F_AFFECTED, 3: _M_UNAFFECTED}
    flb = SegregatrFLBCalculator().compute(
        _pedigree(son_affected=True), _table(), liability_map, 0.001, {}
    )
    assert flb == 1.0
    assert {r["individual_id"]: r["is_affected"] for r in rows}["3"] == "0"


def test_composite_class_member_is_passed_as_affected(monkeypatch) -> None:
    """A member in a composite (one-of-several) class is affected for the R hand-off, and the
    composite row appended by the assigner reaches R through the penetrance TSV."""
    from heredicalc.plugins.liability_assigners.victor_standard.plugin import (
        VictorStandardLiabilityAssigner,
    )

    class _Model:
        def canonical_phenotypes(self) -> list[str]:
            return [_PHENO, "OvarianCancer"]

        def map_raw_affection(self, raw: str) -> list[str] | None:
            return [_PHENO, "OvarianCancer"] if raw == "BC_any" else None

    table = _table()
    table.rows.append(_row("F", "OvarianCancer", 0.02, 0.04, 0.04))
    pedigree = _pedigree(son_affected=False)
    pedigree.members[1].affections = [Affection(phenotype="BC_any", age_at_diagnosis=45)]
    assigner = VictorStandardLiabilityAssigner()
    liability_map = {
        m.individual_id: assigner.assign(m, table, _Model(), {}) for m in pedigree.members
    }
    assert liability_map[2] == 5 and table.rows[5].is_affected

    ped_rows: list[dict[str, str]] = []
    pen_rows: list[str] = []

    def _fake_run(cmd, **kwargs):
        with open(cmd[3], encoding="utf-8") as fh:
            header = fh.readline().rstrip("\n").split("\t")
            ped_rows.extend(
                dict(zip(header, line.rstrip("\n").split("\t"), strict=True)) for line in fh
            )
        with open(cmd[4], encoding="utf-8") as fh:
            pen_rows.extend(line.rstrip("\n") for line in fh)
        return subprocess.CompletedProcess(cmd, 0, stdout='{"flb": 1.0}\n', stderr="")

    monkeypatch.setattr(subprocess, "run", _fake_run)
    SegregatrFLBCalculator().compute(pedigree, table, liability_map, 0.001, {})
    by_id = {r["individual_id"]: r for r in ped_rows}
    assert by_id["2"]["is_affected"] == "1" and by_id["2"]["liability_class"] == "5"
    assert len(pen_rows) == 1 + 6
    composite = [float(v) for v in pen_rows[6].split("\t")]
    assert composite == pytest.approx([0.05 + 0.02, 0.30 + 0.04, 0.30 + 0.04])
