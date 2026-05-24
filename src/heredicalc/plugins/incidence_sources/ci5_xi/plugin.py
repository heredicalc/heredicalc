"""CI5 Volume XI incidence source plugin."""

from __future__ import annotations

import re
from importlib.resources import files as _files
from pathlib import Path

import pandas as pd

from heredicalc.core.models.plugin import PluginMeta, SourceInfo, TraitInfo
from heredicalc.core.pipeline.types import INCIDENCE_SCHEMA, validate_frame
from heredicalc.plugins.incidence_sources.ci5_ix.plugin import _AGE_GROUPS, _extract_period

_DATA = _files(__package__) / "data"

# registry_detailed.txt: "{9-digit-id}\t{spaces}*?{Name} ({years})"
_REGISTRY_RE = re.compile(r"^(\d+)\t\s*\*?\s*(.+)$")
# cancer_detailed.txt: "{3-digit-code} {Name} ({ICD})"
_CANCER_RE = re.compile(r"^(\d{3})\s+(.+?)\s+\(([^)]+)\)\s*$")


class CI5XIIncidenceSource:
    """CI5 Volume XI incidence source (2008-2012).

    Per-source CSVs (9-digit registry ID), same 5-column format as IX/X.
    Lookup via registry_detailed.txt and cancer_detailed.txt.
    """

    meta = PluginMeta(
        name="ci5_xi",
        version="1.0.0",
        kind="incidence_source",
        description="Cancer Incidence in Five Continents, Volume XI (2008-2012)",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    _EDITION = "XI"

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
                        self._sources[source_id] = name
        return self._sources

    def list_sources(self) -> list[SourceInfo]:
        """Return all available CI5-XI registries."""
        sources = self._load_registry()
        result = []
        for source_id, name in sources.items():
            period = _extract_period(name)
            clean = name.split("(")[0].strip().rstrip(",").strip()
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
                f"No CI5-XI source found for identifier {identifier!r}. "
                f"Available: {sorted(sources)[:5]}..."
            )
        if len(matches) > 1:
            raise ValueError(f"Ambiguous CI5-XI identifier {identifier!r} matches: {matches}")
        return matches[0]

    def load(self, source_id: str) -> pd.DataFrame:
        """Load the incidence table for *source_id*."""
        csv_path = Path(str(_DATA / f"{source_id}.csv"))
        if not csv_path.exists():
            raise FileNotFoundError(
                f"CI5-XI data file not found: {csv_path}. "
                "Ensure the data directory is populated."
            )
        df = pd.read_csv(
            csv_path,
            header=None,
            names=["sex", "trait", "age_group", "cases", "person_years"],
            dtype={"sex": int, "trait": str, "age_group": int, "cases": float, "person_years": float},
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
        return validate_frame(df, INCIDENCE_SCHEMA, name="CI5-XI")

    def get_trait_info(self, trait_code: str) -> TraitInfo:
        """Return metadata for *trait_code*."""
        if self._trait_dict is None:
            self._trait_dict = _load_detailed_cancer_dict(Path(str(_DATA)))
        zfill = trait_code.zfill(3)
        if zfill not in self._trait_dict:
            raise KeyError(f"Trait code {trait_code!r} not in CI5-XI dictionary")
        return self._trait_dict[zfill]


def _load_detailed_cancer_dict(data_dir: Path) -> dict[str, TraitInfo]:
    """Parse cancer_detailed.txt — format: '001 Name (ICD)'."""
    result: dict[str, TraitInfo] = {}
    path = data_dir / "cancer_detailed.txt"
    if not path.exists():
        return result
    with open(path, encoding="latin-1") as f:
        for line in f:
            m = _CANCER_RE.match(line.rstrip("\n\r"))
            if m:
                code = m.group(1)
                name = m.group(2).strip()
                icd = m.group(3).strip()
                result[code] = TraitInfo(trait_code=code, name=name, icd_code=icd)
    return result
