"""COOL3 TSV pedigree format plugin."""

from __future__ import annotations

from pathlib import Path

from heredicalc.core.models.pedigree import Affection, Pedigree, PedigreeMember
from heredicalc.core.models.plugin import PluginMeta

_HEADER = "PedID\tIndID\tMother\tFather\tSex\tAff\tAge\tGeno\tFPTP"


class Cool3TsvPedigreeFormat:
    """Load and save pedigrees in COOL3 tab-separated format.

    Expected header: PedID, IndID, Mother, Father, Sex, Aff, Age, Geno, FPTP.
    """

    meta = PluginMeta(
        name="cool3_tsv",
        version="1.0.0",
        kind="pedigree_format",
        description="COOL3 TSV pedigree format (tab-separated, one header row)",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    def load(self, path: Path) -> Pedigree:
        """Load a pedigree from a COOL3 TSV file.

        :raises ValueError: If the file is empty or has malformed rows.
        :raises FileNotFoundError: If *path* does not exist.
        """
        text = path.read_text(encoding="utf-8")
        lines = [l for l in text.splitlines() if l.strip()]
        if not lines:
            raise ValueError(f"Empty pedigree file: {path}")

        data_lines = lines[1:]  # skip header
        pedigree_id: str | None = None
        members: list[PedigreeMember] = []

        for line in data_lines:
            parts = line.split("\t")
            if len(parts) < 9:
                raise ValueError(f"COOL3 TSV row has fewer than 9 columns: {line!r}")

            ped_id, ind_id, mother, father, sex, aff, age, geno, fptp = parts[:9]

            if pedigree_id is None:
                pedigree_id = ped_id

            mother_id = int(mother) if mother.strip() not in ("0", "") else None
            father_id = int(father) if father.strip() not in ("0", "") else None
            age_val = int(age) if age.strip() not in (".", "") else None

            sex_val: str = sex.strip()
            if sex_val not in ("M", "F"):
                sex_val = "U"

            geno_val = geno.strip() if geno.strip() in ("Het", "Neg", "Hom") else None
            is_proband = fptp.strip() == "1"

            affections: list[Affection] = []
            aff_stripped = aff.strip()
            if aff_stripped not in (".", "unaff", ""):
                affections = [Affection(phenotype=aff_stripped)]

            members.append(
                PedigreeMember(
                    individual_id=int(ind_id),
                    mother_id=mother_id,
                    father_id=father_id,
                    sex=sex_val,  # type: ignore[arg-type]
                    affections=affections,
                    age_last_contact=age_val,
                    genotype=geno_val,  # type: ignore[arg-type]
                    is_proband=is_proband,
                )
            )

        return Pedigree(pedigree_id=pedigree_id or path.stem, members=members)

    def save(self, pedigree: Pedigree, path: Path) -> None:
        """Serialise *pedigree* to a COOL3 TSV file."""
        lines = [_HEADER]
        for m in pedigree.members:
            if m.affections:
                aff = m.affections[0].phenotype
            else:
                aff = "unaff"
            age = str(m.age_last_contact) if m.age_last_contact is not None else "."
            geno = m.genotype if m.genotype else "."
            fptp = "1" if m.is_proband else "0"
            mother = str(m.mother_id) if m.mother_id is not None else "0"
            father = str(m.father_id) if m.father_id is not None else "0"
            lines.append(
                f"{pedigree.pedigree_id}\t{m.individual_id}\t"
                f"{mother}\t{father}\t{m.sex}\t{aff}\t{age}\t{geno}\t{fptp}"
            )
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def supports(self, path: Path) -> bool:
        """Return True if *path* has a ``.ped`` extension."""
        return path.suffix.lower() == ".ped"
