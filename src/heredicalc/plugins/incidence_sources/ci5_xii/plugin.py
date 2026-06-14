"""CI5 Volume XII incidence source plugin."""

from __future__ import annotations

import re
from importlib.resources import files as _files
from pathlib import Path

import pandas as pd

from heredicalc.core.exceptions import DataIntegrityError
from heredicalc.core.models.plugin import PluginMeta, SourceInfo, TraitInfo
from heredicalc.core.pipeline.types import INCIDENCE_SCHEMA, validate_frame
from heredicalc.plugins.incidence_sources.ci5_ix.plugin import _AGE_GROUPS, _split_name_period
from heredicalc.plugins.incidence_sources.ci5_xi.plugin import (
    _REGISTRY_RE,
    _load_detailed_cancer_dict,
)

_DATA = _files(__package__) / "data"

# Ovary aggregate site in CI5-XII; sub-sites 179-189 are excluded.
_OVARY_AGGREGATE_CODE = 178


class CI5XIIIncidenceSource:
    """CI5 Volume XII incidence source (2013-2017).

    Per-source CSVs (9-digit registry ID), same 5-column format.
    Trait codes are plain integers (not zero-padded strings) in the CSVs.
    Only aggregate site 178 (Ovary) is used; sub-sites 179-189 are dropped.
    """

    meta = PluginMeta(
        name="ci5_xii",
        version="1.0.0",
        kind="incidence_source",
        description="Cancer Incidence in Five Continents, Volume XII (2013-2017)",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    _EDITION = "XII"

    def __init__(self) -> None:
        self._sources: dict[str, str] | None = None
        self._trait_dict: dict[str, TraitInfo] | None = None

    def _load_registry(self) -> dict[str, str]:
        if self._sources is None:
            self._sources = {}
            path = Path(str(_DATA / "registry_detailed.txt"))
            with open(path, encoding="latin-1") as f:
                for line in f:
                    line = line.rstrip("\n\r")
                    m = _REGISTRY_RE.match(line)
                    if m:
                        source_id = m.group(1).strip()
                        name = m.group(2).strip()
                        # Strip leading asterisk + spaces from XII names
                        name = re.sub(r"^\*\s*", "", name).strip()
                        self._sources[source_id] = name
        return self._sources

    def list_sources(self) -> list[SourceInfo]:
        """Return all available CI5-XII registries."""
        sources = self._load_registry()
        result = []
        for source_id, name in sources.items():
            clean, period = _split_name_period(name)
            result.append(
                SourceInfo(source_id=source_id, name=clean, study_period=period, edition=self._EDITION)
            )
        return result

    def find_source_id(self, identifier: str) -> str:
        """Resolve a name substring or exact 9-digit ID to canonical source ID."""
        sources = self._load_registry()
        if identifier in sources:
            return identifier
        matches = [sid for sid, name in sources.items() if identifier.lower() in name.lower()]
        if not matches:
            raise ValueError(
                f"No CI5-XII source found for identifier {identifier!r}. "
                f"Available: {sorted(sources)[:5]}..."
            )
        if len(matches) > 1:
            raise ValueError(f"Ambiguous CI5-XII identifier {identifier!r} matches: {matches}")
        return matches[0]

    def load(self, source_id: str) -> pd.DataFrame:
        """Load the incidence table for *source_id*.

        :raises DataIntegrityError: If aggregate ovary site 178 rows are absent.
        """
        csv_path = Path(str(_DATA / f"{source_id}.csv"))
        if not csv_path.exists():
            raise FileNotFoundError(
                f"CI5-XII data file not found: {csv_path}. "
                "Ensure the data directory is populated."
            )
        df = pd.read_csv(
            csv_path,
            header=None,
            names=["sex", "trait_code", "age_group", "cases", "person_years"],
            dtype={"sex": int, "trait_code": int, "age_group": int, "cases": float, "person_years": float},
        )

        # Assert aggregate ovary rows are present (per plan Section 7 integrity check)
        ovary_rows = df[df["trait_code"] == _OVARY_AGGREGATE_CODE]
        if ovary_rows.empty:
            raise DataIntegrityError(
                f"CI5-XII source {source_id!r}: aggregate ovary site "
                f"{_OVARY_AGGREGATE_CODE} rows not found. "
                "The data may contain only morphology sub-sites (179-189)."
            )

        # Drop ovary morphology sub-sites (179-189); keep only aggregate 178
        sub_sites = list(range(_OVARY_AGGREGATE_CODE + 1, _OVARY_AGGREGATE_CODE + 12))
        df = df[~df["trait_code"].isin(sub_sites)].copy()

        return self._normalise(df)

    def _normalise(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df[df["age_group"].isin(_AGE_GROUPS)].copy()
        df["age_start"] = df["age_group"].map(lambda g: _AGE_GROUPS[g][0])
        df["age_end"] = df["age_group"].map(lambda g: _AGE_GROUPS[g][1])
        df["sex"] = df["sex"].map({1: "M", 2: "F"})
        df["trait"] = df["trait_code"].apply(lambda c: f"{int(c):03d}")
        df = df[df["person_years"] > 0].copy()
        df = df[["sex", "trait", "age_start", "age_end", "cases", "person_years"]].copy()
        df["sex"] = df["sex"].astype("category")
        df["age_start"] = df["age_start"].astype("int64")
        df["age_end"] = df["age_end"].astype("int64")
        df["cases"] = df["cases"].astype("float64")
        df["person_years"] = df["person_years"].astype("float64")
        return validate_frame(df, INCIDENCE_SCHEMA, name="CI5-XII")

    def get_trait_info(self, trait_code: str) -> TraitInfo:
        """Return metadata for *trait_code*."""
        if self._trait_dict is None:
            self._trait_dict = _load_detailed_cancer_dict(Path(str(_DATA)))
        zfill = trait_code.zfill(3)
        if zfill not in self._trait_dict:
            raise KeyError(f"Trait code {trait_code!r} not in CI5-XII dictionary")
        return self._trait_dict[zfill]
