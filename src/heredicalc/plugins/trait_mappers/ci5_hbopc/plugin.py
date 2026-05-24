"""CI5+HBOPC trait mapper plugin — maps all CI5 editions to HBOPC phenotype names."""

from __future__ import annotations

from importlib.resources import files as _files
from pathlib import Path

import yaml

from heredicalc.core.models.plugin import PluginMeta

_DATA = _files(__package__) / "data"


class CI5HBOPCTraitMapper:
    """Maps CI5 trait codes and COOL3 affection codes to HBOPC canonical phenotypes.

    Loads mappings from ``data/mappings.yml`` at construction time.
    Covers all five CI5 editions (VIII–XII) and the HBOPC pedigree format.
    """

    meta = PluginMeta(
        name="ci5_hbopc",
        version="1.0.0",
        kind="trait_mapper",
        description="Maps CI5 editions VIII-XII trait codes to HBOPC canonical phenotypes",
        author="HerediCalc",
        min_api_version="1.0.0",
        compatible_with={
            "incidence_source": ["ci5_viii", "ci5_ix", "ci5_x", "ci5_xi", "ci5_xii"],
            "phenotype_model": ["hbopc"],
        },
    )

    def __init__(self) -> None:
        mappings_path = Path(str(_DATA / "mappings.yml"))
        with open(mappings_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        self._trait_map: dict[str, str | None] = raw.get("trait_mappings", {})
        self._affection_map: dict[str, str | None] = raw.get("affection_mappings", {})

    def map_trait(self, trait_code: str) -> str | None:
        """Map a CI5 trait code to a canonical HBOPC phenotype.

        :param trait_code: 3-digit zero-padded CI5 trait code, e.g. ``"113"``.
        :return: Canonical name, or ``None`` if not a tracked HBOPC phenotype.
        """
        return self._trait_map.get(trait_code)

    def map_affection(self, raw: str) -> str | None:
        """Map a COOL3 pedigree affection code to a canonical HBOPC phenotype.

        :param raw: Raw affection code, e.g. ``"BrCa"``.
        :return: Canonical name, or ``None`` if unaffected / not tracked.
        """
        return self._affection_map.get(raw)
