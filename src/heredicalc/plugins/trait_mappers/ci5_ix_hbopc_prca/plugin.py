"""CI5-IX + HBOPC+PrCa trait mapper."""

from __future__ import annotations

from importlib.resources import files as _files
from pathlib import Path

import yaml

from heredicalc.core.models.plugin import PluginMeta

_DATA = _files(__package__) / "data"


class CI5IXHBOPCPrCaTraitMapper:
    """Maps CI5-IX trait codes and affection codes to HBOPC+PrCa canonical phenotypes."""

    meta = PluginMeta(
        name="ci5_ix_hbopc_prca",
        version="1.0.0",
        kind="trait_mapper",
        description="Maps CI5-IX trait codes to HBOPC+PrCa canonical phenotypes",
        author="HerediCalc",
        min_api_version="1.0.0",
        compatible_with={
            "incidence_source": ["ci5_ix"],
            "phenotype_model": ["hbopc_prca"],
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
