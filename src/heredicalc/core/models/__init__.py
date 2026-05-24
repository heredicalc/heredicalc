"""Core domain models."""

from heredicalc.core.models.pedigree import Affection, Pedigree, PedigreeMember
from heredicalc.core.models.penetrance import PenetranceRow, PenetranceTable
from heredicalc.core.models.plugin import PluginMeta, PluginSpec, SourceInfo, TraitInfo

__all__ = [
    "Affection",
    "Pedigree",
    "PedigreeMember",
    "PenetranceRow",
    "PenetranceTable",
    "PluginMeta",
    "PluginSpec",
    "SourceInfo",
    "TraitInfo",
]
