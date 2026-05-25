"""Unit tests for the Cool3TsvPedigreeFormat plugin."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from heredicalc.plugins.pedigree_formats.cool3_tsv.plugin import Cool3TsvPedigreeFormat


SAMPLE_PED = textwrap.dedent("""\
    PedID\tIndID\tMother\tFather\tSex\tAff\tAge\tGeno\tFPTP
    Belman\t1\t0\t0\tM\t.\t80\t.\t0
    Belman\t2\t0\t0\tF\tBrCa\t65\t.\t0
    Belman\t3\t2\t1\tF\t.\t81\t.\t0
    Belman\t4\t2\t1\tM\tunaff\t41\t.\t0
    Belman\t6\t2\t1\tF\tunaff\t75\tHet\t0
    Belman\t7\t0\t0\tM\tunaff\t80\t.\t0
    Belman\t8\t2\t1\tF\tunaff\t60\tNeg\t0
    Belman\t12\t6\t7\tF\tBrCa\t49\tHet\t1
""")


@pytest.fixture()
def ped_file(tmp_path: Path) -> Path:
    p = tmp_path / "Belman.ped"
    p.write_text(SAMPLE_PED, encoding="utf-8")
    return p


class TestCool3TsvLoad:
    def test_returns_pedigree_with_correct_id(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        assert ped.pedigree_id == "Belman"

    def test_member_count(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        assert len(ped.members) == 8

    def test_proband_identified(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        probands = [m for m in ped.members if m.is_proband]
        assert len(probands) == 1
        assert probands[0].individual_id == 12

    def test_genotype_het_parsed(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m6 = next(m for m in ped.members if m.individual_id == 6)
        assert m6.genotype == "Het"

    def test_genotype_neg_parsed(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m8 = next(m for m in ped.members if m.individual_id == 8)
        assert m8.genotype == "Neg"

    def test_genotype_unknown_is_none(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m1 = next(m for m in ped.members if m.individual_id == 1)
        assert m1.genotype is None

    def test_affection_brcа_parsed(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m2 = next(m for m in ped.members if m.individual_id == 2)
        assert len(m2.affections) == 1
        assert m2.affections[0].phenotype == "BrCa"

    def test_dot_affection_is_empty(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m1 = next(m for m in ped.members if m.individual_id == 1)
        assert m1.affections == []

    def test_unaff_affection_is_empty(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m4 = next(m for m in ped.members if m.individual_id == 4)
        assert m4.affections == []

    def test_mother_father_ids(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m3 = next(m for m in ped.members if m.individual_id == 3)
        assert m3.mother_id == 2
        assert m3.father_id == 1

    def test_founder_parent_ids_are_none(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m1 = next(m for m in ped.members if m.individual_id == 1)
        assert m1.mother_id is None
        assert m1.father_id is None

    def test_age_last_contact_parsed(self, ped_file: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        m2 = next(m for m in ped.members if m.individual_id == 2)
        assert m2.age_last_contact == 65

    def test_empty_file_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "empty.ped"
        p.write_text("", encoding="utf-8")
        fmt = Cool3TsvPedigreeFormat()
        with pytest.raises(ValueError, match="Empty"):
            fmt.load(p)

    def test_short_row_raises(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.ped"
        p.write_text("PedID\tIndID\n1\t2\n", encoding="utf-8")
        fmt = Cool3TsvPedigreeFormat()
        with pytest.raises(ValueError, match="fewer than 9"):
            fmt.load(p)

    def test_supports_ped_extension(self) -> None:
        fmt = Cool3TsvPedigreeFormat()
        assert fmt.supports(Path("foo.ped"))
        assert not fmt.supports(Path("foo.tsv"))


class TestCool3TsvRoundTrip:
    def test_save_and_reload_preserves_pedigree_id(self, ped_file: Path, tmp_path: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        out = tmp_path / "out.ped"
        fmt.save(ped, out)
        reloaded = fmt.load(out)
        assert reloaded.pedigree_id == ped.pedigree_id

    def test_save_and_reload_member_count(self, ped_file: Path, tmp_path: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        out = tmp_path / "out.ped"
        fmt.save(ped, out)
        reloaded = fmt.load(out)
        assert len(reloaded.members) == len(ped.members)

    def test_save_and_reload_proband_intact(self, ped_file: Path, tmp_path: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        out = tmp_path / "out.ped"
        fmt.save(ped, out)
        reloaded = fmt.load(out)
        orig_prob = next(m for m in ped.members if m.is_proband)
        new_prob = next(m for m in reloaded.members if m.is_proband)
        assert orig_prob.individual_id == new_prob.individual_id

    def test_save_and_reload_genotypes_intact(self, ped_file: Path, tmp_path: Path) -> None:
        fmt = Cool3TsvPedigreeFormat()
        ped = fmt.load(ped_file)
        out = tmp_path / "out.ped"
        fmt.save(ped, out)
        reloaded = fmt.load(out)
        orig_genos = {m.individual_id: m.genotype for m in ped.members}
        new_genos = {m.individual_id: m.genotype for m in reloaded.members}
        assert orig_genos == new_genos
