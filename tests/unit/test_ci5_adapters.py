"""Unit tests for CI5 edition adapters."""

from __future__ import annotations

import pytest


class TestCI5IX:
    def test_list_sources_returns_300(self):
        from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource

        s = CI5IXIncidenceSource()
        assert len(s.list_sources()) == 300

    def test_find_source_id_by_name(self):
        from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource

        s = CI5IXIncidenceSource()
        sid = s.find_source_id("Latvia")
        assert sid == "54280099"

    def test_find_source_id_exact_id(self):
        from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource

        s = CI5IXIncidenceSource()
        assert s.find_source_id("54280099") == "54280099"

    def test_find_source_id_ambiguous_raises(self):
        from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource

        s = CI5IXIncidenceSource()
        with pytest.raises(ValueError, match="Ambiguous"):
            s.find_source_id("Switzerland")

    def test_load_returns_valid_frame(self):
        from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource

        s = CI5IXIncidenceSource()
        df = s.load("54280099")
        assert set(df.columns) == {"sex", "trait", "age_start", "age_end", "cases", "person_years"}
        assert str(df["sex"].dtype) == "category"
        assert (df["person_years"] > 0).all()
        assert df["trait"].str.len().max() == 3

    def test_load_trait_codes_zero_padded(self):
        from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource

        s = CI5IXIncidenceSource()
        df = s.load("54280099")
        assert df["trait"].str.match(r"^\d{3}$").all()

    def test_load_has_breast_cancer_trait(self):
        from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource

        s = CI5IXIncidenceSource()
        df = s.load("54280099")
        assert "113" in df["trait"].values  # BreastCancer in CI5-IX

    def test_age_group_19_excluded(self):
        from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource

        s = CI5IXIncidenceSource()
        df = s.load("54280099")
        # Max age_end should be 99 (group 18 = 85-99)
        assert df["age_end"].max() == 99
        # Age group 19 (unknown) should be excluded — no age_start = NaN etc.
        assert df["age_start"].notna().all()


class TestCI5VIII:
    def test_list_sources_returns_229(self):
        from heredicalc.plugins.incidence_sources.ci5_viii.plugin import CI5VIIIIncidenceSource

        s = CI5VIIIIncidenceSource()
        assert len(s.list_sources()) == 229

    def test_find_source_by_sequential_id(self):
        from heredicalc.plugins.incidence_sources.ci5_viii.plugin import CI5VIIIIncidenceSource

        s = CI5VIIIIncidenceSource()
        sources = s.list_sources()
        first_id = sources[0].source_id
        assert s.find_source_id(first_id) == first_id

    def test_trait_codes_zero_padded(self):
        from heredicalc.plugins.incidence_sources.ci5_viii.plugin import CI5VIIIIncidenceSource

        s = CI5VIIIIncidenceSource()
        df = s.load("1")
        assert df["trait"].str.match(r"^\d{3}$").all()

    def test_breast_cancer_trait_normalized(self):
        from heredicalc.plugins.incidence_sources.ci5_viii.plugin import CI5VIIIIncidenceSource

        s = CI5VIIIIncidenceSource()
        df = s.load("1")
        assert "116" in df["trait"].values  # VIII breast = 116


class TestCI5XIMappings:
    def test_cancer_detailed_parsed(self):
        from heredicalc.plugins.incidence_sources.ci5_xi.plugin import CI5XIIncidenceSource

        s = CI5XIIncidenceSource()
        info = s.get_trait_info("111")  # Breast in XI
        assert "Breast" in info.name or info.trait_code == "111"

    def test_load_returns_valid_frame(self):
        from heredicalc.plugins.incidence_sources.ci5_xi.plugin import CI5XIIncidenceSource

        s = CI5XIIncidenceSource()
        sources = s.list_sources()
        df = s.load(sources[0].source_id)
        assert (df["person_years"] > 0).all()


class TestCI5XIIAggregateOvary:
    def test_ovary_aggregate_present(self):
        from heredicalc.plugins.incidence_sources.ci5_xii.plugin import CI5XIIIncidenceSource

        s = CI5XIIIncidenceSource()
        sources = s.list_sources()
        df = s.load(sources[0].source_id)
        # Trait 178 (Ovary aggregate) must be present
        assert "178" in df["trait"].values

    def test_ovary_sub_sites_excluded(self):
        from heredicalc.plugins.incidence_sources.ci5_xii.plugin import CI5XIIIncidenceSource

        s = CI5XIIIncidenceSource()
        sources = s.list_sources()
        df = s.load(sources[0].source_id)
        # Sub-sites 179-189 must NOT be present
        for code in range(179, 190):
            assert f"{code:03d}" not in df["trait"].values, f"Sub-site {code:03d} should be excluded"
