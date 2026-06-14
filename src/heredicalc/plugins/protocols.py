"""Protocol interfaces for all ten built-in plugin kinds."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

import pandas as pd

from heredicalc.core.models.pedigree import Pedigree, PedigreeMember
from heredicalc.core.models.plugin import PluginMeta, SourceInfo, TraitInfo


@runtime_checkable
class PedigreeFormat(Protocol):
    """Load and save pedigree files in a specific format."""

    meta: PluginMeta

    def load(self, path: Path) -> Pedigree:
        """Load a pedigree from *path*.

        :raises ValueError: If the file format is invalid.
        :raises FileNotFoundError: If path does not exist.
        """
        ...

    def save(self, pedigree: Pedigree, path: Path) -> None:
        """Serialise *pedigree* to *path*."""
        ...

    def supports(self, path: Path) -> bool:
        """Return True if this plugin can parse *path*.

        Used for automatic format detection in GUI/web file pickers.
        """
        ...


@runtime_checkable
class PhenotypeModel(Protocol):
    """Map raw phenotype codes to canonical disease categories."""

    meta: PluginMeta

    def canonical_phenotypes(self) -> list[str]:
        """Return the ordered list of all tracked canonical phenotype names.

        :return: e.g. ``["BreastCancer", "OvarianCancer", "PancreaticCancer"]``
        """
        ...

    def map_raw_affection(self, raw: str) -> str | None:
        """Map a raw affection code from a pedigree file to a canonical phenotype.

        :param raw: Raw code as stored in the pedigree file, e.g. ``"BrCa"``.
        :return: Canonical phenotype name, or ``None`` if unaffected / not tracked.
        """
        ...


@runtime_checkable
class ICDMappablePhenotypeModel(PhenotypeModel, Protocol):
    """Extended protocol for phenotype models that understand ICD-10 codes."""

    def map_icd(self, icd_code: str) -> str | None:
        """Map an ICD-10 code to a canonical phenotype name.

        :param icd_code: ICD-10 code, e.g. ``"C50"``.
        :return: Canonical phenotype name, or ``None`` if not tracked.
        """
        ...


@runtime_checkable
class IncidenceSource(Protocol):
    """Load population cancer incidence tables from one CI5 edition or similar source."""

    meta: PluginMeta

    def list_sources(self) -> list[SourceInfo]:
        """Return all available registry sources for this edition."""
        ...

    def find_source_id(self, identifier: str) -> str:
        """Resolve a source name or numeric ID to the canonical source ID.

        Accepts an exact ID string or a case-insensitive name substring.

        :raises ValueError: If the identifier is ambiguous or not found.
        """
        ...

    def load(self, source_id: str) -> pd.DataFrame:
        """Load the full incidence table for *source_id*.

        :return: ValidatedIncidenceFrame with columns
            ``sex`` (category, "M"/"F"), ``trait`` (str, raw source code),
            ``age_start`` (int64), ``age_end`` (int64),
            ``cases`` (float64), ``person_years`` (float64).
            Rows with ``person_years == 0`` are excluded.
        """
        ...

    def get_trait_info(self, trait_code: str) -> TraitInfo:
        """Return metadata for one trait code.

        :raises KeyError: If *trait_code* is not in this source's dictionary.
        """
        ...


@runtime_checkable
class TraitMapper(Protocol):
    """Map raw CI5 trait codes and pedigree affection codes to canonical phenotype names."""

    meta: PluginMeta

    def map_trait(self, trait_code: str) -> str | None:
        """Map a raw source trait code to a canonical phenotype name.

        :return: Canonical phenotype name, or ``None`` if not tracked (competing risk).
        """
        ...

    def map_affection(self, raw: str) -> str | None:
        """Map a raw pedigree affection code to a canonical phenotype name.

        :return: Canonical phenotype name, or ``None`` if unaffected / not tracked.
        """
        ...


@runtime_checkable
class HazardModel(Protocol):
    """Convert raw incidence tables to yearly per-phenotype hazard rates."""

    meta: PluginMeta

    def compute_hazards(
        self,
        incidence: pd.DataFrame,
        trait_mapper: TraitMapper,
        params: dict[str, Any],
    ) -> pd.DataFrame:
        """Convert a ValidatedIncidenceFrame to a ValidatedHazardFrame.

        Maps trait codes to canonical phenotype names via *trait_mapper*.
        Traits not mapped to a tracked phenotype are aggregated as
        ``"OtherTrait"`` (competing risk, RR=1 in VICTOR).

        :return: ValidatedHazardFrame with columns
            ``sex`` (category), ``phenotype`` (str), ``age`` (int64, 0–99),
            ``lambda_pop`` (float64).
        """
        ...


@runtime_checkable
class CRHFModel(Protocol):
    """Provide cumulative risk haplotype frequency (CRHF) values per genetic entity."""

    meta: PluginMeta

    def get_crhf(
        self,
        genetic_entity: str,
        sex: Literal["M", "F", "U"] | None = None,
        age: int | None = None,
    ) -> float:
        """Return the CRHF value *q* for *genetic_entity*.

        :param genetic_entity: Gene or variant identifier, e.g. ``"BRCA1"``.
        :param sex: Optional sex filter; ignored by the lookup plugin.
        :param age: Optional age filter; ignored by the lookup plugin.
        :raises KeyError: If *genetic_entity* is not in the dataset.
        """
        ...


@runtime_checkable
class RRModel(Protocol):
    """Provide relative risk values per genetic entity, sex, age, phenotype, and genotype."""

    meta: PluginMeta

    def get_rr(
        self,
        genetic_entity: str,
        sex: Literal["M", "F", "U"],
        age: int,
        phenotype: str,
        genotype: Literal["het", "hom"],
    ) -> float:
        """Return the relative risk for the given combination.

        :param age: Age in years (0–99).
        :param phenotype: Canonical phenotype name, e.g. ``"BreastCancer"``.
        :return: Relative risk ≥ 1.0; returns 1.0 for unknown combinations.
        """
        ...


@runtime_checkable
class PenetranceModel(Protocol):
    """Compute a MECE penetrance output from yearly population hazard rates."""

    meta: PluginMeta

    def compute(
        self,
        hazards: pd.DataFrame,
        phenotype_model: PhenotypeModel,
        params: dict[str, Any],
    ) -> Any:
        """Compute penetrance output from a ValidatedHazardFrame.

        The return type is opaque to the core pipeline; only the compatible
        ``flb_calculator`` and ``liability_assigner`` plugins consume it.
        For VICTOR: returns a ``PenetranceTable``.
        """
        ...


@runtime_checkable
class LiabilityAssigner(Protocol):
    """Map pedigree members to penetrance-table liability class indices."""

    meta: PluginMeta

    def assign(
        self,
        member: PedigreeMember,
        penetrance_output: Any,
        phenotype_model: PhenotypeModel,
        params: dict[str, Any],
    ) -> int:
        """Return the zero-based liability class index for *member*.

        For affected members: matches the disease row for the member's
        primary canonical phenotype and age-at-diagnosis band.
        For unaffected members: matches the unaffected row for sex and
        age-last-contact band.
        For sex="U" members: returns the uninformative slot index; logs warning.

        :raises ValueError: If no matching row is found.
        """
        ...


@runtime_checkable
class FLBCalculator(Protocol):
    """Compute the Full Likelihood Bayes factor for a pedigree."""

    meta: PluginMeta

    def compute(
        self,
        pedigree: Pedigree,
        penetrance_output: Any,
        liability_map: dict[int, int],
        allele_freq: float,
        params: dict[str, Any],
    ) -> float:
        """Compute the FLB value for *pedigree*.

        :param liability_map: Mapping from ``individual_id`` to zero-based
            liability class index.
        :param allele_freq: Variant-specific allele frequency for the
            Hardy-Weinberg prior in segregatr.
        :return: FLB as float; values > 1 support pathogenicity.
        :raises SegregaError: If the external FLB computation fails.
        """
        ...

    def session_info(self) -> dict[str, Any] | None:
        """Optional: external session/runtime provenance from the last ``compute``."""
        return None
