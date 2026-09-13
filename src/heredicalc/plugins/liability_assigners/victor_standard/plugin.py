"""VICTOR standard liability assigner plugin."""

from __future__ import annotations

import logging
from typing import Any

from heredicalc.core.exceptions import ZeroPenetranceError
from heredicalc.core.models.pedigree import PedigreeMember
from heredicalc.core.models.penetrance import PenetranceRow, PenetranceTable
from heredicalc.core.models.plugin import PluginMeta

logger = logging.getLogger(__name__)

_UNAFFECTED_PHENO = "unaffected"


class VictorStandardLiabilityAssigner:
    """Standard VICTOR liability assigner.

    Maps each pedigree member to the zero-based row index in a
    ``PenetranceTable`` that corresponds to their sex, affected status,
    primary phenotype, and age band.

    For affected members: uses the member's primary affection phenotype
    (raw code, mapped through the phenotype_model) and age_at_diagnosis. If the
    phenotype model maps the affection to several tracked phenotypes ("one of
    these, subtype unknown"), a composite class is appended to the table whose
    penetrances are the column-wise sums of the candidates' affected rows.
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
        :raises ZeroPenetranceError: If *member* is affected and the matched row has
            no penetrance data (all values zero or undefined).
        """
        table: PenetranceTable = penetrance_output
        index = _match_index(member, table, phenotype_model)
        row = table.rows[index]
        if member.is_affected and not row.has_penetrance:
            raise ZeroPenetranceError(
                member.individual_id,
                row.liability_group,
                reason="all penetrance values for this class are zero or undefined",
            )
        return index


def _match_index(member: PedigreeMember, table: PenetranceTable, phenotype_model: Any) -> int:
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

        if canonical is not None and not isinstance(canonical, str):
            phenotypes = list(dict.fromkeys(canonical))  # order kept, duplicates dropped
            if not phenotypes:
                canonical = None
            elif len(phenotypes) == 1:
                canonical = phenotypes[0]
            else:
                age = primary.age_at_diagnosis
                if age is None:
                    age = member.age_last_contact or 0
                return _composite_index(table, sex, phenotypes, age)

        if canonical is None:
            logger.warning(
                "Member %s has affection %r not mapped to a canonical phenotype; "
                "treated as unaffected (liability class and affected status for the FLB).",
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


def composite_phenotype_name(phenotypes: list[str]) -> str:
    """Name of the composite class for an affection that is one of *phenotypes*."""
    return "|".join(sorted(phenotypes))


def _composite_index(table: PenetranceTable, sex: str, phenotypes: list[str], age: int) -> int:
    """Index of the class for an affection that is exactly one of *phenotypes*, subtype unknown.

    The class is the column-wise sum of the affected rows of every candidate phenotype for
    the member's sex and age band (the events are mutually exclusive, so the sum is the
    probability of "one of them"). It is appended to the table on first use and reused
    afterwards, so the zero-based index contract towards the FLB calculator is unchanged.
    """
    parts = [table.rows[_find_affected_index(table, sex, pheno, age)] for pheno in phenotypes]
    name = composite_phenotype_name(phenotypes)
    for i, row in enumerate(table.rows):
        if row.sex == sex and row.phenotype == name and row.age_start <= age <= row.age_end:
            return i
    first = parts[0]
    table.rows.append(
        PenetranceRow(
            age_start=first.age_start,
            age_end=first.age_end,
            sex=first.sex,
            phenotype=name,
            is_affected=True,
            penetrance_nc=sum(r.penetrance_nc for r in parts),
            penetrance_het=sum(r.penetrance_het for r in parts),
            penetrance_hom=sum(r.penetrance_hom for r in parts),
        )
    )
    return len(table.rows) - 1


def _find_unaffected_index(table: PenetranceTable, sex: str, age: int) -> int:
    for i, row in enumerate(table.rows):
        if not row.is_affected and row.sex == sex and row.age_start <= age <= row.age_end:
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
        if (
            abs(row.penetrance_nc - row.penetrance_het) < 1e-15
            and abs(row.penetrance_nc - row.penetrance_hom) < 1e-15
        ):
            return i
    # Fallback: first unaffected row for F
    for i, row in enumerate(table.rows):
        if not row.is_affected and row.sex == "F":
            return i
    return 0
