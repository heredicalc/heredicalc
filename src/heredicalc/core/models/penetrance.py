"""Penetrance table models used by the VICTOR/segregatr plugin pair."""

from __future__ import annotations

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


class PenetranceTable(BaseModel):
    """MECE penetrance table consumed by the segregatr FLBCalculator plugin.

    This is the specific output type of the VICTOR penetrance model.
    Other penetrance models may produce different output types.
    """

    genetic_entity: str
    population: str
    rows: list[PenetranceRow]
