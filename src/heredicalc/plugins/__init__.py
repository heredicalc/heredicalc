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
from heredicalc.plugins.phenotype_models.hbopc.plugin import HBOPCPhenotypeModel
from heredicalc.plugins.rr_models.tabular.plugin import TabularRRModel
from heredicalc.plugins.trait_mappers.ci5_hbopc.plugin import CI5HBOPCTraitMapper

_BUILTIN_PLUGINS = [
    Cool3TsvPedigreeFormat,
    HBOPCPhenotypeModel,
    CI5VIIIIncidenceSource,
    CI5IXIncidenceSource,
    CI5XIncidenceSource,
    CI5XIIncidenceSource,
    CI5XIIIncidenceSource,
    CI5HBOPCTraitMapper,
    AnnualRateHazardModel,
    VictorPenetranceModel,
    LookupCRHFModel,
    TabularRRModel,
    VictorStandardLiabilityAssigner,
    SegregatrFLBCalculator,
]
