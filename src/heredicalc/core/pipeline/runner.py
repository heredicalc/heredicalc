"""Pipeline runner — orchestrates the full FLB computation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from heredicalc.core.pipeline.config import PipelineConfig
from heredicalc.core.pipeline.manifest import (
    InputFile,
    PluginRef,
    RunManifest,
    collect_python_packages,
    current_timestamp_utc,
    file_sha256,
    heredicalc_version,
    python_version,
)

if TYPE_CHECKING:
    from heredicalc.core.registry.registry import PluginRegistry

logger = logging.getLogger(__name__)

# Plugin kinds the runner instantiates directly (constraint = config field).
_DIRECT_KINDS = (
    "pedigree_format",
    "phenotype_model",
    "incidence_source",
    "trait_mapper",
    "hazard_model",
    "penetrance_model",
    "liability_assigner",
    "flb_calculator",
)
# Sub-plugin kinds injected into other plugins (constraint = params, then field).
_DEP_KINDS = ("rr_model", "crhf_model")


@dataclass(frozen=True)
class _RunOutcome:
    flb: float
    resolved_config: PipelineConfig
    r_session: dict[str, Any] | None


class PipelineRunner:
    """Orchestrate the full FLB pipeline from pedigree file to FLB value.

    All three deployment modes (CLI, GUI, web) call ``run()`` / ``run_with_manifest()``
    identically. The runner holds a registry reference but no mutable state between calls.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def run(self, pedigree_path: Path, config: PipelineConfig) -> float:
        """Execute the full FLB pipeline.

        :param pedigree_path: Path to the pedigree file.
        :param config: Complete pipeline configuration.
        :return: FLB value (> 1 supports pathogenicity).
        """
        return self._execute(pedigree_path, config).flb

    def run_with_manifest(self, pedigree_path: Path, config: PipelineConfig) -> RunManifest:
        """Execute the pipeline and assemble a full run-provenance manifest."""
        outcome = self._execute(pedigree_path, config)
        return RunManifest(
            heredicalc_version=heredicalc_version(),
            python_version=python_version(),
            python_packages=collect_python_packages(),
            r_session=outcome.r_session,
            resolved_config=outcome.resolved_config,
            inputs=[
                InputFile(
                    filename=pedigree_path.name,
                    sha256=file_sha256(pedigree_path),
                )
            ],
            plugins=self._collect_plugins(outcome.resolved_config),
            timestamp_utc=current_timestamp_utc(),
            flb=outcome.flb,
        )

    def _resolve_config(self, config: PipelineConfig) -> PipelineConfig:
        """Apply the penetrance-model defaults cascade, returning the effective config."""
        reg = self._registry
        pc = config.plugins
        pen_defaults = reg.resolve(
            "penetrance_model", pc.penetrance_model
        ).plugin_class.meta.defaults
        if pen_defaults:
            overrides = {k: v for k, v in pen_defaults.items() if k not in pc.model_fields_set}
            if overrides:
                pc = pc.model_copy(update=overrides)
                return PipelineConfig(computation=config.computation, plugins=pc)
        return config

    def _collect_plugins(self, config: PipelineConfig) -> list[PluginRef]:
        """Resolve name/version for every plugin selection in *config* (all ten kinds)."""
        reg = self._registry
        pc = config.plugins
        refs: list[PluginRef] = []
        for kind in _DIRECT_KINDS:
            constraint = getattr(pc, kind)
            entry = reg.resolve(kind, str(constraint))
            refs.append(PluginRef(kind=kind, name=entry.meta.name, version=entry.meta.version))
        for kind in _DEP_KINDS:
            constraint = pc.params.get(kind) or getattr(pc, kind)
            entry = reg.resolve(kind, str(constraint))
            refs.append(PluginRef(kind=kind, name=entry.meta.name, version=entry.meta.version))
        return refs

    def _execute(self, pedigree_path: Path, config: PipelineConfig) -> _RunOutcome:
        """Run the pipeline, returning the FLB plus raw provenance building blocks."""
        reg = self._registry

        # Cascade: apply penetrance_model plugin-specific defaults for fields not
        # explicitly set in config (detected via Pydantic model_fields_set).
        config = self._resolve_config(config)
        cc = config.computation
        pc = config.plugins

        # Build params dict with genetic_entity for sub-plugin calls
        params = dict(pc.params)
        params.setdefault("genetic_entity", cc.genetic_entity)

        logger.info("Resolving plugins for %s", pedigree_path.name)

        # Step 1: Resolve and instantiate all plugins
        pedigree_plugin = reg.instantiate("pedigree_format", pc.pedigree_format, config)
        phenotype_plugin = reg.instantiate("phenotype_model", pc.phenotype_model, config)
        incidence_plugin = reg.instantiate("incidence_source", pc.incidence_source, config)
        trait_mapper = reg.instantiate("trait_mapper", pc.trait_mapper, config)
        hazard_plugin = reg.instantiate("hazard_model", pc.hazard_model, config)
        penetrance_plugin = reg.instantiate("penetrance_model", pc.penetrance_model, config)
        liability_plugin = reg.instantiate("liability_assigner", pc.liability_assigner, config)
        flb_plugin = reg.instantiate("flb_calculator", pc.flb_calculator, config)

        reg.validate_compatibility(
            {
                "pedigree_format": pedigree_plugin,
                "phenotype_model": phenotype_plugin,
                "incidence_source": incidence_plugin,
                "trait_mapper": trait_mapper,
                "hazard_model": hazard_plugin,
                "penetrance_model": penetrance_plugin,
                "liability_assigner": liability_plugin,
                "flb_calculator": flb_plugin,
            }
        )

        # Step 2: Load pedigree
        logger.info("Loading pedigree from %s", pedigree_path)
        pedigree = pedigree_plugin.load(pedigree_path)

        # Step 3: Load incidence
        population = params.get("population", "")
        logger.info("Loading incidence for population %r", population)
        source_id = incidence_plugin.find_source_id(population)
        raw_incidence = incidence_plugin.load(source_id)

        # Step 4: Compute hazards
        logger.info("Computing hazards")
        hazard_df = hazard_plugin.compute_hazards(raw_incidence, trait_mapper, params)

        # Step 5: Compute penetrance
        logger.info("Computing VICTOR penetrance")
        penetrance_output = penetrance_plugin.compute(hazard_df, phenotype_plugin, params)

        # Step 6: Assign liabilities
        logger.info("Assigning liability classes")
        liability_map = {
            member.individual_id: liability_plugin.assign(
                member, penetrance_output, phenotype_plugin, params
            )
            for member in pedigree.members
        }

        # Step 7: Compute FLB
        logger.info("Computing FLB via segregatr")
        flb = flb_plugin.compute(
            pedigree,
            penetrance_output,
            liability_map,
            cc.allele_freq,
            params,
        )

        session_accessor = getattr(flb_plugin, "session_info", None)
        r_session = session_accessor() if callable(session_accessor) else None

        logger.info("FLB = %g", flb)
        return _RunOutcome(flb=flb, resolved_config=config, r_session=r_session)
