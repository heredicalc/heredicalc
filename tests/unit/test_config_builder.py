"""Unit tests for the shared config builder (no R, no Streamlit)."""

from __future__ import annotations

from pathlib import Path

import yaml

from heredicalc.apps.cli.main import _load_config
from heredicalc.core.pipeline.config_builder import build_config_from_dict

# Equivalent CLI YAML: only required + reference fields, rest from PluginConfig defaults.
_REFERENCE_YAML = {
    "computation": {"genetic_entity": "BRCA1", "allele_freq": 0.0001},
    "plugins": {
        "incidence_source": "ci5_ix",
        "phenotype_model": "hbopc",
        "trait_mapper": "ci5_ix_hbopc",
        "penetrance_model": "victor",
        "params": {
            "population": "Latvia",
            "age_bands": [30, 40, 50, 60, 65, 70, 80],
            "rr_model": "tabular",
            "crhf_model": "lookup",
        },
    },
}

# Widget-shaped dict as the web app assembles it (all selections explicit).
_WIDGET_DICT = {
    "computation": {"genetic_entity": "BRCA1", "allele_freq": 0.0001},
    "plugins": {
        "incidence_source": "ci5_ix",
        "phenotype_model": "hbopc",
        "trait_mapper": "ci5_ix_hbopc",
        "hazard_model": "annual_rate",
        "penetrance_model": "victor",
        "liability_assigner": "victor_standard",
        "flb_calculator": "segregatr",
        "pedigree_format": "cool3_tsv",
        "rr_model": "tabular",
        "crhf_model": "lookup",
        "params": {
            "population": "Latvia",
            "age_bands": [30, 40, 50, 60, 65, 70, 80],
            "rr_model": "tabular",
            "crhf_model": "lookup",
        },
    },
}


def test_build_config_from_dict_maps_fields() -> None:
    config = build_config_from_dict(_WIDGET_DICT)
    assert config.computation.genetic_entity == "BRCA1"
    assert config.computation.allele_freq == 0.0001
    assert config.plugins.incidence_source == "ci5_ix"
    assert config.plugins.trait_mapper == "ci5_ix_hbopc"
    assert config.plugins.penetrance_model == "victor"
    assert config.plugins.flb_calculator == "segregatr"
    assert config.plugins.params["population"] == "Latvia"
    assert config.plugins.params["age_bands"] == [30, 40, 50, 60, 65, 70, 80]


def test_web_dict_matches_cli_yaml(tmp_path: Path) -> None:
    yaml_path = tmp_path / "config.yml"
    yaml_path.write_text(yaml.safe_dump(_REFERENCE_YAML), encoding="utf-8")

    cli_config = _load_config(yaml_path, {})
    web_config = build_config_from_dict(_WIDGET_DICT)

    assert web_config == cli_config
    assert web_config.model_dump() == cli_config.model_dump()
