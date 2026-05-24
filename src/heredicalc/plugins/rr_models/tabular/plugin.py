"""Tabular relative risk model plugin — age-band CSV lookup."""

from __future__ import annotations

from importlib.resources import files as _files
from pathlib import Path
from typing import Literal

import pandas as pd

from heredicalc.core.models.plugin import PluginMeta

_DATA = _files(__package__) / "data"


class TabularRRModel:
    """Tabular RR model.

    Looks up relative risks from a per-gene CSV file with columns:
    gene, gender, age_from, age_to (empty = open-ended), phenotype,
    heterozygous_rr, homozygous_rr.

    Returns 1.0 for any combination not present in the dataset.
    Raises ``KeyError`` at ``get_rr()`` call time for genes with empty CSV files.
    """

    meta = PluginMeta(
        name="tabular",
        version="1.0.0",
        kind="rr_model",
        description="Tabular RR model: age-band lookup from bundled CSV files",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    _SEX_MAP = {"M": "M", "F": "F", "U": "M"}  # U falls back to M for RR lookup

    def __init__(self) -> None:
        self._cache: dict[str, pd.DataFrame | None] = {}

    def _load_gene(self, genetic_entity: str) -> pd.DataFrame | None:
        """Load and cache RR table for *genetic_entity*.

        Returns None if the CSV is empty (stub like BRCA2.csv).
        Raises FileNotFoundError if no CSV exists for the gene.
        """
        if genetic_entity not in self._cache:
            csv_path = Path(str(_DATA / f"{genetic_entity}.csv"))
            if not csv_path.exists():
                raise FileNotFoundError(
                    f"No RR table found for {genetic_entity!r} at {csv_path}. "
                    "Ensure the gene CSV is bundled in the data directory."
                )
            if csv_path.stat().st_size == 0:
                self._cache[genetic_entity] = None
            else:
                df = pd.read_csv(csv_path)
                self._cache[genetic_entity] = df
        return self._cache[genetic_entity]

    def get_rr(
        self,
        genetic_entity: str,
        sex: Literal["M", "F", "U"],
        age: int,
        phenotype: str,
        genotype: Literal["het", "hom"],
    ) -> float:
        """Return the relative risk for the given combination.

        :return: Relative risk ≥ 1.0; returns 1.0 for unknown combinations.
        :raises KeyError: If *genetic_entity* has an empty/stub CSV (no data).
        """
        df = self._load_gene(genetic_entity)
        if df is None:
            raise KeyError(
                f"RR table for {genetic_entity!r} is an empty stub — no data available."
            )

        gender_col = self._SEX_MAP.get(sex, "M")
        col = "heterozygous_rr" if genotype == "het" else "homozygous_rr"

        mask = (df["gene"] == genetic_entity) & (df["gender"] == gender_col) & (df["phenotype"] == phenotype)
        candidates = df[mask]

        for _, row in candidates.iterrows():
            age_from = int(row["age_from"])
            age_to = row["age_to"]
            if pd.isna(age_to) or str(age_to).strip() == "":
                # Open-ended: age_from ≤ age
                if age >= age_from:
                    return float(row[col])
            else:
                if age_from <= age <= int(age_to):
                    return float(row[col])

        return 1.0
