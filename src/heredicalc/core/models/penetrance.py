"""Penetrance table models used by the VICTOR/segregatr plugin pair."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel


class PenetranceRow(BaseModel):
    """One liability class row in a MECE penetrance table."""

    age_start: int
    age_end: int
    sex: Literal["M", "F", "U"]
    phenotype: str
    is_affected: bool
    penetrance_nc: float
    penetrance_het: float
    penetrance_hom: float

    @property
    def has_penetrance(self) -> bool:
        """True when at least one genotype gives this class a defined, non-zero probability."""
        values = (self.penetrance_nc, self.penetrance_het, self.penetrance_hom)
        return not any(math.isnan(v) for v in values) and any(v > 0 for v in values)

    @property
    def liability_group(self) -> dict[str, str]:
        """Identifying fields of this liability class, for diagnostics."""
        return {
            "sex": self.sex,
            "phenotype": self.phenotype,
            "age_band": f"{self.age_start}-{self.age_end}",
        }


class PenetranceTable(BaseModel):
    """MECE penetrance table consumed by the segregatr FLBCalculator plugin.

    This is the specific output type of the VICTOR penetrance model.
    Other penetrance models may produce different output types.
    """

    genetic_entity: str
    population: str
    rows: list[PenetranceRow]
