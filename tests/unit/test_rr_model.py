"""Unit tests for the TabularRRModel plugin."""

from __future__ import annotations

import pytest

from heredicalc.plugins.rr_models.tabular.plugin import TabularRRModel


class TestTabularRRModelBRCA1:
    def test_brca1_female_breast_young(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "F", 20, "BreastCancer", "het")
        assert val == pytest.approx(73.7)

    def test_brca1_female_breast_30s(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "F", 35, "BreastCancer", "het")
        assert val == pytest.approx(46.2)

    def test_brca1_female_breast_40s(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "F", 45, "BreastCancer", "het")
        assert val == pytest.approx(17.2)

    def test_brca1_female_breast_50s(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "F", 55, "BreastCancer", "het")
        assert val == pytest.approx(9.7)

    def test_brca1_female_breast_open_ended(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "F", 85, "BreastCancer", "het")
        assert val == pytest.approx(1.0)

    def test_brca1_female_ovarian_40s(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "F", 45, "OvarianCancer", "het")
        assert val == pytest.approx(56.7)

    def test_brca1_male_breast(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "M", 50, "BreastCancer", "het")
        assert val == pytest.approx(8.0)

    def test_brca1_sex_u_falls_back_to_male(self) -> None:
        rr = TabularRRModel()
        val_u = rr.get_rr("BRCA1", "U", 50, "BreastCancer", "het")
        val_m = rr.get_rr("BRCA1", "M", 50, "BreastCancer", "het")
        assert val_u == val_m

    def test_unknown_phenotype_returns_1(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "F", 40, "UnknownCancer", "het")
        assert val == pytest.approx(1.0)

    def test_brca1_pancreatic_young(self) -> None:
        rr = TabularRRModel()
        val = rr.get_rr("BRCA1", "F", 30, "PancreaticCancer", "het")
        assert val == pytest.approx(4.68)


class TestTabularRRModelStubs:
    def test_unknown_gene_raises_key_error(self) -> None:
        rr = TabularRRModel()
        with pytest.raises(KeyError, match="No RR data"):
            rr.get_rr("UNKNOWNGENE", "F", 40, "BreastCancer", "het")

    def test_unknown_gene_error_mentions_add_trait(self) -> None:
        rr = TabularRRModel()
        with pytest.raises(KeyError, match="add trait"):
            rr.get_rr("UNKNOWNGENE2", "F", 40, "BreastCancer", "het")

    def test_cache_reuse(self) -> None:
        rr = TabularRRModel()
        v1 = rr.get_rr("BRCA1", "F", 40, "BreastCancer", "het")
        v2 = rr.get_rr("BRCA1", "F", 40, "BreastCancer", "het")
        assert v1 == v2
