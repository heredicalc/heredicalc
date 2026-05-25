"""CI5-XII + HBOPC trait mapper."""

from __future__ import annotations

from importlib.resources import files as _files
from pathlib import Path

import yaml

from heredicalc.core.models.plugin import PluginMeta

_DATA = _files(__package__) / "data"


class CI5XIIHBOPCTraitMapper:
    """Maps CI5-XII trait codes and affection codes to HBOPC canonical phenotypes."""

    meta = PluginMeta(
        name="ci5_xii_hbopc",
        version="1.0.0",
        kind="trait_mapper",
        description="Maps CI5-XII trait codes to HBOPC canonical phenotypes",
        author="HerediCalc",
        min_api_version="1.0.0",
        compatible_with={
            "incidence_source": ["ci5_xii"],
            "phenotype_model": ["hbopc"],
        },
    )

    def __init__(self) -> None:
        raw = yaml.safe_load(Path(str(_DATA / "mappings.yml")).read_text(encoding="utf-8"))
        self._trait_map: dict[str, str | None] = raw["trait_mappings"]
        self._affection_map: dict[str, str | None] = raw["affection_mappings"]

    def map_trait(self, trait_code: str) -> str | None:
        return self._trait_map.get(trait_code)

    def map_affection(self, raw: str) -> str | None:
        return self._affection_map.get(raw)
