"""VICTOR standard liability assigner plugin."""

from __future__ import annotations

import logging
from typing import Any

from heredicalc.core.models.penetrance import PenetranceRow, PenetranceTable
from heredicalc.core.models.pedigree import PedigreeMember
from heredicalc.core.models.plugin import PluginMeta

logger = logging.getLogger(__name__)

_UNAFFECTED_PHENO = "unaffected"


class VictorStandardLiabilityAssigner:
    """Standard VICTOR liability assigner.

    Maps each pedigree member to the zero-based row index in a
    ``PenetranceTable`` that corresponds to their sex, affected status,
    primary phenotype, and age band.

    For affected members: uses the member's primary affection phenotype
    (raw code, mapped through the phenotype_model) and age_at_diagnosis.
    For unaffected members: uses age_last_contact or 99 if unknown.
    For sex="U" members: returns the uninformative slot (penetrance_nc ==
    penetrance_het == penetrance_hom) and logs a mandatory warning.
    """

    meta = PluginMeta(
        name="victor_standard",
        version="1.0.0",
        kind="liability_assigner",
        description="VICTOR standard liability assigner for PenetranceTable",
        author="HerediCalc",
        min_api_version="1.0.0",
        compatible_with={
            "penetrance_model": ["victor", "victor_cool3"],
            "flb_calculator": ["segregatr"],
        },
    )

    def assign(
        self,
        member: PedigreeMember,
        penetrance_output: Any,
        phenotype_model: Any,
        params: dict[str, Any],
    ) -> int:
        """Return the zero-based liability class index for *member*.

        :raises ValueError: If no matching penetrance row is found.
        """
        table: PenetranceTable = penetrance_output

        sex = member.sex
        if sex == "U":
            logger.warning(
                "Member %s has unknown sex (sex='U') — assigning uninformative "
                "liability slot. This may reduce FLB information.",
                member.individual_id,
            )
            return _find_uninformative_index(table)

        if member.is_affected:
            primary = member.primary_affection
            if primary is None:
                return _find_unaffected_index(table, sex, member.age_last_contact or 99)

            raw_pheno = primary.phenotype
            canonical = phenotype_model.map_raw_affection(raw_pheno)

            if canonical is None:
                logger.warning(
                    "Member %s has affection %r not mapped to a canonical phenotype; "
                    "treating as unaffected for liability assignment.",
                    member.individual_id,
                    raw_pheno,
                )
                return _find_unaffected_index(table, sex, member.age_last_contact or 99)

            age = primary.age_at_diagnosis
            if age is None:
                age = member.age_last_contact or 0

            return _find_affected_index(table, sex, canonical, age)
        else:
            return _find_unaffected_index(table, sex, member.age_last_contact or 99)


def _find_affected_index(
    table: PenetranceTable,
    sex: str,
    phenotype: str,
    age: int,
) -> int:
    for i, row in enumerate(table.rows):
        if (
            row.is_affected
            and row.sex == sex
            and row.phenotype == phenotype
            and row.age_start <= age <= row.age_end
        ):
            return i
    raise ValueError(
        f"No penetrance row for affected member: sex={sex!r}, phenotype={phenotype!r}, "
        f"age={age}. Available rows: {[(r.sex, r.phenotype, r.age_start, r.age_end) for r in table.rows if r.is_affected]}"
    )


def _find_unaffected_index(table: PenetranceTable, sex: str, age: int) -> int:
    for i, row in enumerate(table.rows):
        if (
            not row.is_affected
            and row.sex == sex
            and row.age_start <= age <= row.age_end
        ):
            return i
    raise ValueError(
        f"No penetrance row for unaffected member: sex={sex!r}, age={age}. "
        f"Unaffected rows: {[(r.sex, r.age_start, r.age_end) for r in table.rows if not r.is_affected]}"
    )


def _find_uninformative_index(table: PenetranceTable) -> int:
    """Return index of a row where nc == het == hom (uninformative).

    Falls back to the first unaffected row for F if no exact match found.
    """
    for i, row in enumerate(table.rows):
        if abs(row.penetrance_nc - row.penetrance_het) < 1e-15 and abs(
            row.penetrance_nc - row.penetrance_hom
        ) < 1e-15:
            return i
    # Fallback: first unaffected row for F
    for i, row in enumerate(table.rows):
        if not row.is_affected and row.sex == "F":
            return i
    return 0
