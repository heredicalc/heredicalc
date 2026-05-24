"""HBOPC phenotype model plugin — Hereditary Breast/Ovarian/Pancreatic Cancer."""

from __future__ import annotations

from heredicalc.core.models.plugin import PluginMeta


class HBOPCPhenotypeModel:
    """Canonical phenotype model for the HBOPC gene panel.

    Tracks BreastCancer, OvarianCancer, and PancreaticCancer.
    """

    meta = PluginMeta(
        name="hbopc",
        version="1.0.0",
        kind="phenotype_model",
        description="HBOPC phenotype model: Breast, Ovarian, and Pancreatic Cancer",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    _CANONICAL: list[str] = ["BreastCancer", "OvarianCancer", "PancreaticCancer"]

    _RAW_MAP: dict[str, str | None] = {
        "BrCa": "BreastCancer",
        "OvCa": "OvarianCancer",
        "PanCa": "PancreaticCancer",
        "unaff": None,
        ".": None,
    }

    _ICD_MAP: dict[str, str] = {
        "C50": "BreastCancer",
        "C56": "OvarianCancer",
        "C25": "PancreaticCancer",
    }

    def canonical_phenotypes(self) -> list[str]:
        """Return the ordered list of HBOPC canonical phenotype names."""
        return list(self._CANONICAL)

    def map_raw_affection(self, raw: str) -> str | None:
        """Map a COOL3 raw affection code to a canonical HBOPC phenotype.

        :return: Canonical name or ``None`` if unaffected / unrecognised.
        """
        return self._RAW_MAP.get(raw)

    def map_icd(self, icd_code: str) -> str | None:
        """Map an ICD-10 site code to a canonical HBOPC phenotype.

        :return: Canonical name or ``None`` if not tracked.
        """
        return self._ICD_MAP.get(icd_code)
