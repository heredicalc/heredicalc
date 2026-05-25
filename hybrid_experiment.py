"""Hybrid FLB experiment: COOL3 unaff rows + our aff rows → segregatr FLB.

Uses Latvia/BRCA1/CI5-IX config (shared by all 226 test cases).
COOL3 unaff values hardcoded from:
  https://fenglab-r9.chpc.utah.edu/results/coseg/2a94852b-950f-4489-97bf-707c0eb4d921/index.html
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from heredicalc.core.models.penetrance import PenetranceRow, PenetranceTable
from heredicalc.core.pipeline.config import ComputationConfig, PipelineConfig, PluginConfig
from heredicalc.core.pipeline.runner import PipelineRunner
from heredicalc.core.registry.registry import PluginRegistry
from heredicalc.plugins.flb_calculators.segregatr.plugin import SegregatrFLBCalculator
from heredicalc.plugins.liability_assigners.victor_standard.plugin import (
    VictorStandardLiabilityAssigner,
)
from heredicalc.plugins.pedigree_formats.cool3_tsv.plugin import Cool3TsvPedigreeFormat

# ---------------------------------------------------------------------------
# COOL3 unaff penetrance values (cumulative 1-S_g per band-end age)
# Fetched from primary result page (Latvia, BRCA1, CI5-IX):
#   https://fenglab-r9.chpc.utah.edu/results/coseg/2a94852b-950f-4489-97bf-707c0eb4d921/index.html
# Row format: (sex, age_start, age_end): (nc, het, hom)
# ---------------------------------------------------------------------------
COOL3_UNAFF = {
    # male
    ("M", 0, 29):  (0.000023574, 0.000121557, 0.000121557),
    ("M", 30, 39): (0.000164800, 0.000832388, 0.000832388),
    ("M", 40, 49): (0.000803197, 0.003897042, 0.003897042),
    ("M", 50, 59): (0.002809724, 0.008897523, 0.008897523),
    ("M", 60, 64): (0.005490758, 0.013189215, 0.013189215),
    ("M", 65, 69): (0.008365794, 0.017629794, 0.017629794),
    ("M", 70, 79): (0.014077759, 0.026669561, 0.026669561),
    ("M", 80, 99): (0.021471507, 0.036345807, 0.036345807),
    # female
    ("F", 0, 29):  (0.000273821, 0.007719602, 0.007719602),
    ("F", 30, 39): (0.002033155, 0.076603545, 0.076603545),
    ("F", 40, 49): (0.009737713, 0.251749669, 0.251749669),
    ("F", 50, 59): (0.024689585, 0.453028188, 0.453028188),
    ("F", 60, 64): (0.038428823, 0.577670612, 0.577670612),
    ("F", 65, 69): (0.049229472, 0.652804549, 0.652804549),
    ("F", 70, 79): (0.067118422, 0.711415031, 0.711415031),
    ("F", 80, 99): (0.087460822, 0.734635673, 0.734635673),
}


def make_config() -> PipelineConfig:
    params = {
        "population": "Latvia",
        "age_bands": [30, 40, 50, 60, 65, 70, 80],
        "rr_model": "tabular",
        "crhf_model": "lookup",
    }
    return PipelineConfig(
        computation=ComputationConfig(genetic_entity="BRCA1", allele_freq=0.0001),
        plugins=PluginConfig(
            incidence_source="ci5_ix",
            phenotype_model="hbopc",
            trait_mapper="ci5_hbopc",
            penetrance_model="victor",
            params=params,
        ),
    )


def patch_unaff_rows(table: PenetranceTable) -> PenetranceTable:
    """Replace unaff rows with COOL3 values; keep all aff rows unchanged."""
    new_rows: list[PenetranceRow] = []
    for row in table.rows:
        if not row.is_affected:
            key = (row.sex, row.age_start, row.age_end)
            if key in COOL3_UNAFF:
                nc, het, hom = COOL3_UNAFF[key]
                new_rows.append(
                    PenetranceRow(
                        age_start=row.age_start,
                        age_end=row.age_end,
                        sex=row.sex,
                        phenotype=row.phenotype,
                        is_affected=False,
                        penetrance_nc=nc,
                        penetrance_het=het,
                        penetrance_hom=hom,
                    )
                )
            else:
                new_rows.append(row)
        else:
            new_rows.append(row)
    return PenetranceTable(
        genetic_entity=table.genetic_entity,
        population=table.population,
        rows=new_rows,
    )


def main() -> None:
    fixtures_path = Path(__file__).parent / "tests/fixtures/validation_fixtures.json"
    pedigrees_dir = Path(__file__).parent / "tests/fixtures/pedigrees"

    with open(fixtures_path) as f:
        data = json.load(f)
    cases = data["validation_cases"]

    reg = PluginRegistry()
    reg.discover_all()

    config = make_config()
    params = dict(config.plugins.params)
    params.setdefault("genetic_entity", config.computation.genetic_entity)

    # Compute our penetrance table once (config identical for all 226 cases)
    print("Computing our penetrance table...", flush=True)
    incidence_plugin = reg.instantiate("incidence_source", "ci5_ix", config)
    phenotype_plugin = reg.instantiate("phenotype_model", "hbopc", config)
    trait_mapper = reg.instantiate("trait_mapper", "ci5_hbopc", config)
    hazard_plugin = reg.instantiate("hazard_model", "annual_rate", config)
    penetrance_plugin = reg.instantiate("penetrance_model", "victor", config)

    source_id = incidence_plugin.find_source_id("Latvia")
    raw_incidence = incidence_plugin.load(source_id)
    hazard_df = hazard_plugin.compute_hazards(raw_incidence, trait_mapper, params)
    our_table = penetrance_plugin.compute(hazard_df, phenotype_plugin, params)

    hybrid_table = patch_unaff_rows(our_table)

    pedigree_plugin = reg.instantiate("pedigree_format", "cool3_tsv", config)
    liability_plugin = reg.instantiate("liability_assigner", "victor_standard", config)
    flb_plugin = reg.instantiate("flb_calculator", "segregatr", config)

    hdr = f"{'Case ID':<58} {'Ref FLB':>10} {'Hybrid FLB':>12} {'Ours FLB':>10} {'Δ% Hybrid':>10} {'Δ% Ours':>10}"
    sep = "-" * len(hdr)
    print(f"\n{hdr}")
    print(sep)

    results = []
    for case in cases:
        ped_file = pedigrees_dir / case["pedigree"]
        ref_flb = case["reference_flb"]
        allele_freq = case["config"].get("allele_freq", 0.0001)

        try:
            pedigree = pedigree_plugin.load(ped_file)

            liability_map_hybrid = {
                m.individual_id: liability_plugin.assign(m, hybrid_table, phenotype_plugin, params)
                for m in pedigree.members
            }
            hybrid_flb = flb_plugin.compute(
                pedigree, hybrid_table, liability_map_hybrid, allele_freq, params
            )

            liability_map_ours = {
                m.individual_id: liability_plugin.assign(m, our_table, phenotype_plugin, params)
                for m in pedigree.members
            }
            our_flb = flb_plugin.compute(
                pedigree, our_table, liability_map_ours, allele_freq, params
            )

            delta_hybrid = (hybrid_flb - ref_flb) / ref_flb * 100
            delta_ours = (our_flb - ref_flb) / ref_flb * 100

            results.append((case["id"], ref_flb, hybrid_flb, our_flb, delta_hybrid, delta_ours))
            print(
                f"{case['id']:<58} {ref_flb:>10.4f} {hybrid_flb:>12.4f} {our_flb:>10.4f} "
                f"{delta_hybrid:>+9.1f}% {delta_ours:>+9.1f}%"
            )

        except Exception as e:
            print(f"{case['id']:<58} ERROR: {e}")
            results.append((case["id"], ref_flb, None, None, None, None))

    # Summary
    valid = [(r[4], r[5]) for r in results if r[4] is not None]
    deltas_hybrid = [abs(r[0]) for r in valid]
    deltas_ours = [abs(r[1]) for r in valid]
    within6_hybrid = sum(1 for d in deltas_hybrid if d <= 6.0)
    within6_ours = sum(1 for d in deltas_ours if d <= 6.0)
    print(sep)
    print(f"\nWithin ±6%:  Hybrid={within6_hybrid}/{len(valid)},  Ours={within6_ours}/{len(valid)}")
    print(f"Mean |Δ%|:   Hybrid={sum(deltas_hybrid)/len(deltas_hybrid):.1f}%,  "
          f"Ours={sum(deltas_ours)/len(deltas_ours):.1f}%")
    print(f"Max  |Δ%|:   Hybrid={max(deltas_hybrid):.1f}%,  Ours={max(deltas_ours):.1f}%")


if __name__ == "__main__":
    main()
