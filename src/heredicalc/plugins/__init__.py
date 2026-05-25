"""Built-in plugin registration.

Imported by ``PluginRegistry.discover_builtins()`` to register all
built-in plugin classes with the active registry instance.
The registry is passed via the module-level ``_registry`` attribute,
set by ``discover_builtins()`` before importing this module.
"""

from __future__ import annotations

# NOTE: This module is imported by discover_builtins() which sets
# _registry on this module before the import completes. Each plugin
# self-registers via the register() calls below.

# All imports are deferred to avoid import-time side effects when the
# module is imported outside of a discover_builtins() call context.

from heredicalc.plugins.crhf_models.lookup.plugin import LookupCRHFModel
from heredicalc.plugins.flb_calculators.segregatr.plugin import SegregatrFLBCalculator
from heredicalc.plugins.hazard_models.annual_rate.plugin import AnnualRateHazardModel
from heredicalc.plugins.hazard_models.annual_rate_cool3.plugin import AnnualRateCool3HazardModel
from heredicalc.plugins.incidence_sources.ci5_viii.plugin import CI5VIIIIncidenceSource
from heredicalc.plugins.incidence_sources.ci5_ix.plugin import CI5IXIncidenceSource
from heredicalc.plugins.incidence_sources.ci5_x.plugin import CI5XIncidenceSource
from heredicalc.plugins.incidence_sources.ci5_xi.plugin import CI5XIIncidenceSource
from heredicalc.plugins.incidence_sources.ci5_xii.plugin import CI5XIIIncidenceSource
from heredicalc.plugins.liability_assigners.victor_standard.plugin import (
    VictorStandardLiabilityAssigner,
)
from heredicalc.plugins.pedigree_formats.cool3_tsv.plugin import Cool3TsvPedigreeFormat
from heredicalc.plugins.penetrance_models.victor.plugin import VictorPenetranceModel
from heredicalc.plugins.penetrance_models.victor_cool3.plugin import VictorCool3PenetranceModel
from heredicalc.plugins.phenotype_models.hbopc.plugin import HBOPCPhenotypeModel
from heredicalc.plugins.phenotype_models.hbopc_prca.plugin import HBOPCPrCaPhenotypeModel
from heredicalc.plugins.rr_models.tabular.plugin import TabularRRModel
from heredicalc.plugins.trait_mappers.ci5_viii_hbopc.plugin import CI5VIIIHBOPCTraitMapper
from heredicalc.plugins.trait_mappers.ci5_ix_hbopc.plugin import CI5IXHBOPCTraitMapper
from heredicalc.plugins.trait_mappers.ci5_x_hbopc.plugin import CI5XHBOPCTraitMapper
from heredicalc.plugins.trait_mappers.ci5_xi_hbopc.plugin import CI5XIHBOPCTraitMapper
from heredicalc.plugins.trait_mappers.ci5_xii_hbopc.plugin import CI5XIIHBOPCTraitMapper
from heredicalc.plugins.trait_mappers.ci5_viii_hbopc_prca.plugin import CI5VIIIHBOPCPrCaTraitMapper
from heredicalc.plugins.trait_mappers.ci5_ix_hbopc_prca.plugin import CI5IXHBOPCPrCaTraitMapper
from heredicalc.plugins.trait_mappers.ci5_x_hbopc_prca.plugin import CI5XHBOPCPrCaTraitMapper
from heredicalc.plugins.trait_mappers.ci5_xi_hbopc_prca.plugin import CI5XIHBOPCPrCaTraitMapper
from heredicalc.plugins.trait_mappers.ci5_xii_hbopc_prca.plugin import CI5XIIHBOPCPrCaTraitMapper

_BUILTIN_PLUGINS = [
    Cool3TsvPedigreeFormat,
    HBOPCPhenotypeModel,
    HBOPCPrCaPhenotypeModel,
    CI5VIIIIncidenceSource,
    CI5IXIncidenceSource,
    CI5XIncidenceSource,
    CI5XIIncidenceSource,
    CI5XIIIncidenceSource,
    CI5VIIIHBOPCTraitMapper,
    CI5IXHBOPCTraitMapper,
    CI5XHBOPCTraitMapper,
    CI5XIHBOPCTraitMapper,
    CI5XIIHBOPCTraitMapper,
    CI5VIIIHBOPCPrCaTraitMapper,
    CI5IXHBOPCPrCaTraitMapper,
    CI5XHBOPCPrCaTraitMapper,
    CI5XIHBOPCPrCaTraitMapper,
    CI5XIIHBOPCPrCaTraitMapper,
    AnnualRateHazardModel,
    AnnualRateCool3HazardModel,
    VictorPenetranceModel,
    VictorCool3PenetranceModel,
    LookupCRHFModel,
    TabularRRModel,
    VictorStandardLiabilityAssigner,
    SegregatrFLBCalculator,
]
