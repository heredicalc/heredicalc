"""Pipeline runner — orchestrates the full FLB computation."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from heredicalc.core.pipeline.config import PipelineConfig

if TYPE_CHECKING:
    from heredicalc.core.registry.registry import PluginRegistry

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Orchestrate the full FLB pipeline from pedigree file to FLB value.

    All three deployment modes (CLI, GUI, web) call ``run()`` identically.
    The runner holds a registry reference but no mutable state between calls.
    """

    def __init__(self, registry: PluginRegistry) -> None:
        self._registry = registry

    def run(self, pedigree_path: Path, config: PipelineConfig) -> float:
        """Execute the full FLB pipeline.

        :param pedigree_path: Path to the pedigree file.
        :param config: Complete pipeline configuration.
        :return: FLB value (> 1 supports pathogenicity).
        """
        reg = self._registry
        pc = config.plugins
        cc = config.computation

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

        logger.info("FLB = %g", flb)
        return flb
