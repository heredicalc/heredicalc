"""Pipeline configuration models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ComputationConfig(BaseModel):
    """Universal parameters required for any FLB calculation."""

    genetic_entity: str
    allele_freq: float


class PluginConfig(BaseModel):
    """Plugin selection and plugin-specific parameters."""

    incidence_source: str
    phenotype_model: str
    trait_mapper: str
    hazard_model: str = "annual_rate"
    penetrance_model: str = "victor"
    rr_model: str = "tabular"
    crhf_model: str = "lookup"
    liability_assigner: str = "victor_standard"
    flb_calculator: str = "segregatr"
    pedigree_format: str = "cool3_tsv"
    params: dict[str, Any] = {}


class PipelineConfig(BaseModel):
    """Complete configuration for one FLB pipeline run."""

    computation: ComputationConfig
    plugins: PluginConfig
