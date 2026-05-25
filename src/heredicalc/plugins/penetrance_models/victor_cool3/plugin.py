"""VICTOR competing-risk penetrance model — COOL3-compatible variant.

Replicates the methodology used by COOL3 v3, including two known deviations
from mathematically correct competing-risk theory:

1. **Tracked-only survival**: OtherTrait is excluded from lambda_all when
   computing survival curves S_g(a). Only tracked phenotypes (BrCa, OvCa,
   PanCa) contribute to the all-cause hazard.

2. **Band-midpoint evaluation for unaffected rows**: The survival probability
   for unaffected members is evaluated at the band midpoint ``(a0+a1)//2``
   rather than the band end ``a1``.

These deviations make COOL3 internally inconsistent (affected rows cover the
full band; unaffected rows cover only the first half), but are replicated here
to produce COOL3-identical FLB values for validation and comparison purposes.

See ``docs/algorithms/victor-model.md`` for a full mathematical analysis.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from heredicalc.core.models.penetrance import PenetranceRow, PenetranceTable
from heredicalc.core.models.plugin import PluginMeta

if TYPE_CHECKING:
    from heredicalc.plugins.protocols import CRHFModel, PhenotypeModel, RRModel

_OTHER = "OtherTrait"


class VictorCool3PenetranceModel:
    """VICTOR penetrance model — COOL3-compatible (midpoint + tracked-only survival).

    Produces penetrance tables identical to COOL3 v3 for use in validation and
    cross-tool comparison. For scientifically correct results, use ``VictorPenetranceModel``.
    """

    meta = PluginMeta(
        name="victor_cool3",
        version="1.0.0",
        kind="penetrance_model",
        description="COOL3-compatible VICTOR model: midpoint unaff evaluation, tracked-only survival",
        author="HerediCalc",
        min_api_version="1.0.0",
        requires={"rr_model": None, "crhf_model": None},
        compatible_with={
            "flb_calculator": ["segregatr"],
            "liability_assigner": ["victor_standard"],
        },
    )

    def __init__(self, rr_model: RRModel, crhf_model: CRHFModel) -> None:
        self.rr_model = rr_model
        self.crhf_model = crhf_model

    def compute(
        self,
        hazards: pd.DataFrame,
        phenotype_model: PhenotypeModel,
        params: dict[str, Any],
    ) -> PenetranceTable:
        """Compute a MECE PenetranceTable using the COOL3-compatible VICTOR algorithm."""
        genetic_entity: str = params["genetic_entity"]
        age_bands: list[int] = params.get("age_bands", [30, 40, 50, 60, 65, 70, 80])
        tracked: list[str] = phenotype_model.canonical_phenotypes()

        q = self.crhf_model.get_crhf(genetic_entity)

        bands = _build_bands(age_bands)
        sexes = ["F", "M"]
        rows: list[PenetranceRow] = []

        for sex in sexes:
            sub_all = hazards[hazards["sex"] == sex].copy()
            sub = (
                sub_all.groupby(["phenotype", "age"], observed=True)["lambda_pop"]
                .sum()
                .reset_index()
            )
            phenotype_names = list(sub["phenotype"].unique())

            lambda_nc = np.zeros((100, len(phenotype_names)))
            lambda_het = np.zeros((100, len(phenotype_names)))
            lambda_hom = np.zeros((100, len(phenotype_names)))

            for j, pheno in enumerate(phenotype_names):
                age_series = sub[sub["phenotype"] == pheno].set_index("age")["lambda_pop"]
                for a in range(100):
                    val = age_series.get(a, 0.0)
                    lp = float(val) if not hasattr(val, "__len__") else float(val.iloc[0])

                    if pheno == _OTHER:
                        rr_het = 1.0
                        rr_hom = 1.0
                    else:
                        rr_het = self.rr_model.get_rr(genetic_entity, sex, a, pheno, "het")
                        rr_hom = self.rr_model.get_rr(genetic_entity, sex, a, pheno, "hom")

                    D = 1.0 + 2.0 * q * (rr_het - 1.0)
                    lnc = lp / D if D > 0 else lp
                    lambda_nc[a, j] = lnc
                    lambda_het[a, j] = rr_het * lnc
                    lambda_hom[a, j] = rr_hom * lnc

            # COOL3 deviation 1: tracked-only survival (OtherTrait excluded)
            tracked_cols = [j for j, p in enumerate(phenotype_names) if p != _OTHER]
            if tracked_cols:
                lambda_all_nc = lambda_nc[:, tracked_cols].sum(axis=1)
                lambda_all_het = lambda_het[:, tracked_cols].sum(axis=1)
                lambda_all_hom = lambda_hom[:, tracked_cols].sum(axis=1)
            else:
                lambda_all_nc = lambda_nc.sum(axis=1)
                lambda_all_het = lambda_het.sum(axis=1)
                lambda_all_hom = lambda_hom.sum(axis=1)

            S_nc = np.exp(-np.cumsum(lambda_all_nc))
            S_het = np.exp(-np.cumsum(lambda_all_het))
            S_hom = np.exp(-np.cumsum(lambda_all_hom))

            S_nc_prev = np.concatenate([[1.0], S_nc[:-1]])
            S_het_prev = np.concatenate([[1.0], S_het[:-1]])
            S_hom_prev = np.concatenate([[1.0], S_hom[:-1]])

            n_pheno = len(phenotype_names)
            F_nc = np.zeros((100, n_pheno))
            F_het = np.zeros((100, n_pheno))
            F_hom = np.zeros((100, n_pheno))

            for j in range(n_pheno):
                inc_nc = S_nc_prev * (1.0 - np.exp(-lambda_nc[:, j]))
                inc_het = S_het_prev * (1.0 - np.exp(-lambda_het[:, j]))
                inc_hom = S_hom_prev * (1.0 - np.exp(-lambda_hom[:, j]))
                F_nc[:, j] = np.cumsum(inc_nc)
                F_het[:, j] = np.cumsum(inc_het)
                F_hom[:, j] = np.cumsum(inc_hom)

            pheno_idx = {p: i for i, p in enumerate(phenotype_names)}

            for a0, a1 in bands:
                f_prev_a0 = a0 - 1

                for pheno in tracked:
                    if pheno not in pheno_idx:
                        pen_nc = pen_het = pen_hom = 0.0
                    else:
                        j = pheno_idx[pheno]
                        f_a1_nc = F_nc[a1, j]
                        f_a1_het = F_het[a1, j]
                        f_a1_hom = F_hom[a1, j]
                        if f_prev_a0 >= 0:
                            f_a0m1_nc = F_nc[f_prev_a0, j]
                            f_a0m1_het = F_het[f_prev_a0, j]
                            f_a0m1_hom = F_hom[f_prev_a0, j]
                        else:
                            f_a0m1_nc = f_a0m1_het = f_a0m1_hom = 0.0

                        pen_nc = max(0.0, f_a1_nc - f_a0m1_nc)
                        pen_het = max(0.0, f_a1_het - f_a0m1_het)
                        pen_hom = max(0.0, f_a1_hom - f_a0m1_hom)

                    rows.append(
                        PenetranceRow(
                            age_start=a0,
                            age_end=a1,
                            sex=sex,  # type: ignore[arg-type]
                            phenotype=pheno,
                            is_affected=True,
                            penetrance_nc=pen_nc,
                            penetrance_het=pen_het,
                            penetrance_hom=pen_hom,
                        )
                    )

                # COOL3 deviation 2: evaluate survival at band midpoint, not band end
                mid = (a0 + a1) // 2
                rows.append(
                    PenetranceRow(
                        age_start=a0,
                        age_end=a1,
                        sex=sex,  # type: ignore[arg-type]
                        phenotype="unaffected",
                        is_affected=False,
                        penetrance_nc=1.0 - float(S_nc[mid]),
                        penetrance_het=1.0 - float(S_het[mid]),
                        penetrance_hom=1.0 - float(S_hom[mid]),
                    )
                )

        return PenetranceTable(
            genetic_entity=genetic_entity,
            population=str(params.get("population", "")),
            rows=rows,
        )


def _build_bands(age_bands: list[int]) -> list[tuple[int, int]]:
    """Build (age_start, age_end) pairs from a list of band-start ages.

    The first band starts at 0; the last band ends at 99.
    Example: [30, 40, 50] → [(0,29), (30,39), (40,49), (50,99)]
    """
    starts = [0] + sorted(age_bands)
    bands = []
    for i, a0 in enumerate(starts):
        a1 = starts[i + 1] - 1 if i + 1 < len(starts) else 99
        bands.append((a0, a1))
    return bands
