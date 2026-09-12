"""Unit tests for core domain exceptions."""

from __future__ import annotations

import pytest

from heredicalc.core.exceptions import HerediCalcError, ZeroPenetranceError


def test_zero_penetrance_error_carries_context() -> None:
    exc = ZeroPenetranceError(
        7,
        {"sex": "M", "phenotype": "BreastCancer", "age_band": "0-49"},
        reason="all values zero",
        pedigree_id="fam_a",
    )
    assert exc.individual_id == 7
    assert exc.group == {"sex": "M", "phenotype": "BreastCancer", "age_band": "0-49"}
    assert exc.reason == "all values zero"
    assert exc.pedigree_id == "fam_a"
    msg = str(exc)
    assert "member 7" in msg
    assert "pedigree 'fam_a'" in msg
    assert "sex='M'" in msg
    assert "phenotype='BreastCancer'" in msg
    assert "age_band='0-49'" in msg
    assert msg.endswith(": all values zero")


def test_zero_penetrance_error_without_optional_context() -> None:
    exc = ZeroPenetranceError(3, {"sex": "M"})
    assert exc.pedigree_id is None
    assert exc.reason == ""
    assert str(exc) == "Affected member 3 has no penetrance data for liability class sex='M'"


def test_zero_penetrance_error_is_a_heredicalc_error() -> None:
    with pytest.raises(HerediCalcError):
        raise ZeroPenetranceError(1, {"sex": "F"})


def test_zero_penetrance_error_copies_group() -> None:
    group = {"sex": "M"}
    exc = ZeroPenetranceError(1, group)
    group["sex"] = "F"
    assert exc.group == {"sex": "M"}
