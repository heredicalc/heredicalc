"""CI5 Volume X incidence source plugin.

Identical file format to CI5-IX; differs only in bundled data and meta.name.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from heredicalc.core.models.plugin import PluginMeta, SourceInfo, TraitInfo
from heredicalc.core.pipeline.types import INCIDENCE_SCHEMA, validate_frame
from heredicalc.plugins.incidence_sources._data_dir import ci5_data_dir
from heredicalc.plugins.incidence_sources.ci5_ix.plugin import (
    _AGE_GROUPS,
    _load_ix_cancer_dict,
    _split_name_period,
)


def _data() -> Path:
    return ci5_data_dir(__package__)


class CI5XIncidenceSource:
    """CI5 Volume X incidence source (2003-2007).

    Same 5-column CSV format as CI5-IX.
    """

    meta = PluginMeta(
        name="ci5_x",
        version="1.0.0",
        kind="incidence_source",
        description="Cancer Incidence in Five Continents, Volume X (2003-2007)",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    _EDITION = "X"

    def __init__(self) -> None:
        self._sources: dict[str, str] | None = None
        self._trait_dict: dict[str, str] | None = None

    def _load_registry(self) -> dict[str, str]:
        if self._sources is None:
            self._sources = {}
            registry_path = _data() / "registry.txt"
            with open(registry_path, encoding="latin-1") as f:
                for line in f:
                    line = line.rstrip("\n\r")
                    if "\t" not in line:
                        continue
                    source_id, name = line.split("\t", 1)
                    source_id = source_id.strip()
                    name = name.strip()
                    self._sources[source_id] = name
        return self._sources

    def list_sources(self) -> list[SourceInfo]:
        """Return all available CI5-X registries."""
        sources = self._load_registry()
        result = []
        for source_id, name in sources.items():
            clean_name, period = _split_name_period(name)
            result.append(
                SourceInfo(
                    source_id=source_id,
                    name=clean_name,
                    study_period=period,
                    edition=self._EDITION,
                )
            )
        return result

    def find_source_id(self, identifier: str) -> str:
        """Resolve a name substring or exact ID to a canonical CI5-X source ID."""
        sources = self._load_registry()
        if identifier in sources:
            return identifier
        matches = [sid for sid, name in sources.items() if identifier.lower() in name.lower()]
        if not matches:
            raise ValueError(
                f"No CI5-X source found for identifier {identifier!r}. Available: {sorted(sources)}"
            )
        if len(matches) > 1:
            raise ValueError(f"Ambiguous CI5-X identifier {identifier!r} matches: {matches}")
        return matches[0]

    def load(self, source_id: str) -> pd.DataFrame:
        """Load the incidence table for *source_id*."""
        csv_path = _data() / f"{source_id}.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"CI5-X data file not found: {csv_path}. Ensure the data directory is populated."
            )
        df = pd.read_csv(
            csv_path,
            header=None,
            names=["sex", "trait", "age_group", "cases", "person_years"],
            dtype={
                "sex": int,
                "trait": str,
                "age_group": int,
                "cases": float,
                "person_years": float,
            },
        )
        return self._normalise(df)

    def _normalise(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df[df["age_group"].isin(_AGE_GROUPS)].copy()
        df["age_start"] = df["age_group"].map(lambda g: _AGE_GROUPS[g][0])
        df["age_end"] = df["age_group"].map(lambda g: _AGE_GROUPS[g][1])
        df["sex"] = df["sex"].map({1: "M", 2: "F"})
        df["trait"] = df["trait"].str.strip().str.zfill(3)
        df = df[df["person_years"] > 0].copy()
        df = df[["sex", "trait", "age_start", "age_end", "cases", "person_years"]].copy()
        df["sex"] = df["sex"].astype("category")
        df["age_start"] = df["age_start"].astype("int64")
        df["age_end"] = df["age_end"].astype("int64")
        df["cases"] = df["cases"].astype("float64")
        df["person_years"] = df["person_years"].astype("float64")
        return validate_frame(df, INCIDENCE_SCHEMA, name="CI5-X")

    def get_trait_info(self, trait_code: str) -> TraitInfo:
        """Return metadata for *trait_code*."""
        if self._trait_dict is None:
            self._trait_dict = _load_ix_cancer_dict(_data())
        zfill = trait_code.zfill(3)
        if zfill not in self._trait_dict:
            raise KeyError(f"Trait code {trait_code!r} not found in CI5-X dictionary")
        return TraitInfo(trait_code=zfill, name=self._trait_dict[zfill])
