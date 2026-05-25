"""CI5 Volume IX incidence source plugin."""

from __future__ import annotations

from importlib.resources import files as _files
from pathlib import Path

import pandas as pd

from heredicalc.core.models.plugin import PluginMeta, SourceInfo, TraitInfo
from heredicalc.core.pipeline.types import INCIDENCE_SCHEMA, validate_frame

_DATA = _files(__package__) / "data"

# Age group → (age_start, age_end). Group 18 extended to 99; group 19 excluded.
# CI5-IX aggregate summary codes that must be excluded to avoid double-counting.
# Code 001 = "All sites combined"; code 002 = "All sites excl. non-melanoma skin".
_AGGREGATE_TRAITS: frozenset[str] = frozenset(["001", "002"])

_AGE_GROUPS: dict[int, tuple[int, int]] = {
    1: (0, 4),
    2: (5, 9),
    3: (10, 14),
    4: (15, 19),
    5: (20, 24),
    6: (25, 29),
    7: (30, 34),
    8: (35, 39),
    9: (40, 44),
    10: (45, 49),
    11: (50, 54),
    12: (55, 59),
    13: (60, 64),
    14: (65, 69),
    15: (70, 74),
    16: (75, 79),
    17: (80, 84),
    18: (85, 99),
}


class CI5IXIncidenceSource:
    """CI5 Volume IX incidence source.

    Per-source CSVs named ``{8-digit-id}.csv``, no header.
    Columns: sex (int), trait (3-digit str), age_group (int), cases, person_years.
    """

    meta = PluginMeta(
        name="ci5_ix",
        version="1.0.0",
        kind="incidence_source",
        description="Cancer Incidence in Five Continents, Volume IX (1998-2002)",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    _EDITION = "IX"

    def __init__(self) -> None:
        self._sources: dict[str, str] | None = None  # source_id → name
        self._trait_dict: dict[str, str] | None = None  # trait_code → name

    def _load_registry(self) -> dict[str, str]:
        if self._sources is None:
            self._sources = {}
            registry_path = Path(str(_DATA / "registry.txt"))
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
        """Return all available CI5-IX registries."""
        sources = self._load_registry()
        result = []
        for source_id, name in sources.items():
            period = _extract_period(name)
            clean_name = name.split("(")[0].strip().rstrip(",").strip()
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
        """Resolve a name substring or exact ID to a canonical CI5-IX source ID.

        :raises ValueError: If the identifier matches zero or multiple sources.
        """
        sources = self._load_registry()
        if identifier in sources:
            return identifier
        matches = [sid for sid, name in sources.items() if identifier.lower() in name.lower()]
        if not matches:
            raise ValueError(
                f"No CI5-IX source found for identifier {identifier!r}. "
                f"Available: {sorted(sources)}"
            )
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous CI5-IX identifier {identifier!r} matches: {matches}"
            )
        return matches[0]

    def load(self, source_id: str) -> pd.DataFrame:
        """Load the incidence table for *source_id*.

        :return: ValidatedIncidenceFrame.
        :raises FileNotFoundError: If the CSV for *source_id* is not bundled.
        """
        csv_path = Path(str(_DATA / f"{source_id}.csv"))
        if not csv_path.exists():
            raise FileNotFoundError(
                f"CI5-IX data file not found: {csv_path}. "
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
        df = df[~df["trait"].isin(_AGGREGATE_TRAITS)].copy()
        df = df[["sex", "trait", "age_start", "age_end", "cases", "person_years"]].copy()
        df["sex"] = df["sex"].astype("category")
        df["age_start"] = df["age_start"].astype("int64")
        df["age_end"] = df["age_end"].astype("int64")
        df["cases"] = df["cases"].astype("float64")
        df["person_years"] = df["person_years"].astype("float64")
        return validate_frame(df, INCIDENCE_SCHEMA, name="CI5-IX")

    def get_trait_info(self, trait_code: str) -> TraitInfo:
        """Return metadata for *trait_code*.

        :raises KeyError: If *trait_code* is not in the CI5-IX cancer dictionary.
        """
        if self._trait_dict is None:
            self._trait_dict = _load_ix_cancer_dict(Path(str(_DATA)))
        zfill = trait_code.zfill(3)
        if zfill not in self._trait_dict:
            raise KeyError(f"Trait code {trait_code!r} not found in CI5-IX dictionary")
        return TraitInfo(trait_code=zfill, name=self._trait_dict[zfill])


def _extract_period(name: str) -> str:
    """Extract the study period from a registry name like 'Latvia (1998-2002)'."""
    if "(" in name and ")" in name:
        return name[name.index("(") + 1 : name.index(")")]
    return ""


def _load_ix_cancer_dict(data_dir: Path) -> dict[str, str]:
    """Load trait code → name mapping from CI5-IX data directory."""
    cancer_path = data_dir / "cancer.txt"
    result: dict[str, str] = {}
    if not cancer_path.exists():
        return result
    with open(cancer_path, encoding="latin-1") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(None, 2)
            if len(parts) >= 2:
                try:
                    code = parts[0].zfill(3)
                    name = parts[-1] if len(parts) == 3 else parts[1]
                    result[code] = name.strip()
                except (ValueError, IndexError):
                    continue
    return result
