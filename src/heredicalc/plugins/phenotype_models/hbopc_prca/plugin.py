"""HBOPC+PrCa phenotype model plugin — Hereditary Breast/Ovarian/Pancreatic/Prostate Cancer."""

from __future__ import annotations

from heredicalc.core.models.plugin import PluginMeta


class HBOPCPrCaPhenotypeModel:
    """Phenotype model extending HBOPC with ProstateCancer.

    Tracks BreastCancer, OvarianCancer, PancreaticCancer, and ProstateCancer.
    Suitable for BRCA2 and other genes with prostate cancer association.
    """

    meta = PluginMeta(
        name="hbopc_prca",
        version="1.0.0",
        kind="phenotype_model",
        description="HBOPC+PrCa phenotype model: Breast, Ovarian, Pancreatic, and Prostate Cancer",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    _CANONICAL: list[str] = ["BreastCancer", "OvarianCancer", "PancreaticCancer", "ProstateCancer"]

    _RAW_MAP: dict[str, str | None] = {
        "BrCa": "BreastCancer",
        "OvCa": "OvarianCancer",
        "PanCa": "PancreaticCancer",
        "PrCa": "ProstateCancer",
        "unaff": None,
        ".": None,
    }

    _ICD_MAP: dict[str, str] = {
        "C50": "BreastCancer",
        "C56": "OvarianCancer",
        "C25": "PancreaticCancer",
        "C61": "ProstateCancer",
    }

    def canonical_phenotypes(self) -> list[str]:
        return list(self._CANONICAL)

    def map_raw_affection(self, raw: str) -> str | None:
        return self._RAW_MAP.get(raw)

    def map_icd(self, icd_code: str) -> str | None:
        return self._ICD_MAP.get(icd_code)
