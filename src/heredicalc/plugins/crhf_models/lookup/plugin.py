"""Lookup CRHF model plugin — single q value per gene."""

from __future__ import annotations

from importlib.resources import files as _files
from pathlib import Path
from typing import Literal

import pandas as pd

from heredicalc.core.models.plugin import PluginMeta
from heredicalc.core.trait_manifest import load_manifest

_DATA = _files(__package__) / "data"


class LookupCRHFModel:
    """CRHF lookup model.

    Reads a single *q* value per gene from ``genes.csv``
    (columns: gene, crhf_value). Sex and age are ignored.
    """

    meta = PluginMeta(
        name="lookup",
        version="1.0.0",
        kind="crhf_model",
        description="Lookup CRHF model: single q value per gene from genes.csv",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    def __init__(self) -> None:
        self._table: dict[str, float] | None = None

    def _load(self) -> dict[str, float]:
        if self._table is None:
            csv_path = Path(str(_DATA / "genes.csv"))
            df = pd.read_csv(csv_path)
            self._table = dict(zip(df["gene"], df["crhf_value"].astype(float)))
            for entry in load_manifest():
                self._table[entry["name"]] = float(entry["crhf_value"])
        return self._table

    def get_crhf(
        self,
        genetic_entity: str,
        sex: Literal["M", "F", "U"] | None = None,
        age: int | None = None,
    ) -> float:
        """Return the CRHF value *q* for *genetic_entity*.

        :raises KeyError: If *genetic_entity* is not in ``genes.csv``.
        """
        table = self._load()
        if genetic_entity not in table:
            raise KeyError(
                f"CRHF not found for {genetic_entity!r}. "
                f"Available: {sorted(table)}"
            )
        return table[genetic_entity]
