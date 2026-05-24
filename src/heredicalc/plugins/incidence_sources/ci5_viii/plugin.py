"""CI5 Volume VIII incidence source plugin."""

from __future__ import annotations

import re
from importlib.resources import files as _files
from pathlib import Path

import pandas as pd

from heredicalc.core.models.plugin import PluginMeta, SourceInfo, TraitInfo
from heredicalc.core.pipeline.types import INCIDENCE_SCHEMA, validate_frame
from heredicalc.plugins.incidence_sources.ci5_ix.plugin import _AGE_GROUPS, _extract_period

_DATA = _files(__package__) / "data"

# CI5-VIII uses sequential integer registry IDs — map int → source_id string.
_ID_RE = re.compile(r"^\s+(\d+)\s+\*?(.+)$")
_CANCER_RE = re.compile(r"^\s+(\d+)\s+\S+\s+(.+)$")


class CI5VIIIIncidenceSource:
    """CI5 Volume VIII incidence source.

    Single consolidated CSV ``CI5-VIII.csv`` with columns:
    registry_id (int), sex (int), trait_code (int), age_group (int),
    cases, person_years.
    """

    meta = PluginMeta(
        name="ci5_viii",
        version="1.0.0",
        kind="incidence_source",
        description="Cancer Incidence in Five Continents, Volume VIII (1993-1997)",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    _EDITION = "VIII"

    def __init__(self) -> None:
        self._registry: dict[str, tuple[str, str]] | None = None  # seq_id → (name, period)
        self._trait_dict: dict[str, str] | None = None
        self._raw_df: pd.DataFrame | None = None

    def _ensure_registry(self) -> dict[str, tuple[str, str]]:
        if self._registry is None:
            self._registry = {}
            registry_path = Path(str(_DATA / "registry.txt"))
            with open(registry_path, encoding="latin-1") as f:
                for line in f:
                    line = line.rstrip("\n\r")
                    if line.strip().startswith("Population"):
                        continue
                    m = _ID_RE.match(line)
                    if m:
                        seq_id = m.group(1)
                        name_period = m.group(2).strip()
                        # Strip leading asterisk
                        name_period = name_period.lstrip("*").strip()
                        period = _extract_period(name_period)
                        clean = name_period.split("(")[0].strip().rstrip(",").strip()
                        self._registry[seq_id] = (clean, period)
        return self._registry

    def _ensure_raw_df(self) -> pd.DataFrame:
        if self._raw_df is None:
            csv_path = Path(str(_DATA / "CI5-VIII.csv"))
            if not csv_path.exists():
                raise FileNotFoundError(
                    f"CI5-VIII data file not found: {csv_path}. "
                    "Ensure the data directory is populated."
                )
            self._raw_df = pd.read_csv(
                csv_path,
                header=None,
                names=["registry_id", "sex", "trait_code", "age_group", "cases", "person_years"],
                dtype={
                    "registry_id": int,
                    "sex": int,
                    "trait_code": int,
                    "age_group": int,
                    "cases": float,
                    "person_years": float,
                },
            )
        return self._raw_df

    def list_sources(self) -> list[SourceInfo]:
        """Return all available CI5-VIII registries."""
        registry = self._ensure_registry()
        return [
            SourceInfo(
                source_id=seq_id,
                name=name,
                study_period=period,
                edition=self._EDITION,
            )
            for seq_id, (name, period) in registry.items()
        ]

    def find_source_id(self, identifier: str) -> str:
        """Resolve a sequential integer string or name substring to source ID.

        :raises ValueError: If the identifier matches zero or multiple sources.
        """
        registry = self._ensure_registry()
        if identifier in registry:
            return identifier
        matches = [
            sid for sid, (name, _) in registry.items()
            if identifier.lower() in name.lower()
        ]
        if not matches:
            raise ValueError(
                f"No CI5-VIII source found for identifier {identifier!r}. "
                f"Available IDs: {sorted(registry, key=int)[:10]}... "
                f"(use sequential integer ID or name substring)"
            )
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous CI5-VIII identifier {identifier!r} matches: {matches}"
            )
        return matches[0]

    def load(self, source_id: str) -> pd.DataFrame:
        """Load the incidence table for *source_id* (sequential integer ID)."""
        raw = self._ensure_raw_df()
        df = raw[raw["registry_id"] == int(source_id)].copy()
        if df.empty:
            raise ValueError(f"No CI5-VIII data for registry_id={source_id!r}")
        return self._normalise(df)

    def _normalise(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df[df["age_group"].isin(_AGE_GROUPS)].copy()
        df["age_start"] = df["age_group"].map(lambda g: _AGE_GROUPS[g][0])
        df["age_end"] = df["age_group"].map(lambda g: _AGE_GROUPS[g][1])
        df["sex"] = df["sex"].map({1: "M", 2: "F"})
        df["trait"] = df["trait_code"].apply(lambda c: f"{c:03d}")
        df = df[df["person_years"] > 0].copy()
        df = df[["sex", "trait", "age_start", "age_end", "cases", "person_years"]].copy()
        df["sex"] = df["sex"].astype("category")
        df["age_start"] = df["age_start"].astype("int64")
        df["age_end"] = df["age_end"].astype("int64")
        df["cases"] = df["cases"].astype("float64")
        df["person_years"] = df["person_years"].astype("float64")
        return validate_frame(df, INCIDENCE_SCHEMA, name="CI5-VIII")

    def get_trait_info(self, trait_code: str) -> TraitInfo:
        """Return metadata for *trait_code* (integer string or zero-padded)."""
        if self._trait_dict is None:
            self._trait_dict = self._load_cancer_dict()
        zfill = trait_code.zfill(3)
        if zfill not in self._trait_dict:
            raise KeyError(f"Trait code {trait_code!r} not in CI5-VIII dictionary")
        return TraitInfo(trait_code=zfill, name=self._trait_dict[zfill])

    def _load_cancer_dict(self) -> dict[str, str]:
        result: dict[str, str] = {}
        cancer_path = Path(str(_DATA / "cancer.txt"))
        if not cancer_path.exists():
            return result
        with open(cancer_path, encoding="latin-1") as f:
            for line in f:
                line = line.rstrip("\n\r")
                if "Cancer dictionary" in line or not line.strip():
                    continue
                m = _CANCER_RE.match(line)
                if m:
                    code = m.group(1).zfill(3)
                    name = m.group(2).strip()
                    result[code] = name
        return result
