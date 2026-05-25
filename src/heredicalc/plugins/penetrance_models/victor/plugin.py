"""VICTOR competing-risk penetrance model plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from heredicalc.core.models.penetrance import PenetranceRow, PenetranceTable
from heredicalc.core.models.plugin import PluginMeta

if TYPE_CHECKING:
    from heredicalc.plugins.protocols import CRHFModel, PhenotypeModel, RRModel

_OTHER = "OtherTrait"


class VictorPenetranceModel:
    """VICTOR competing-risk penetrance model.

    Computes carrier-corrected hazards via Hardy-Weinberg correction, derives
    all-cause survival curves and cause-specific CIFs, then builds a MECE
    ``PenetranceTable`` for use with the segregatr FLB calculator.

    Requires ``rr_model`` and ``crhf_model`` sub-plugins injected at construction.
    """

    meta = PluginMeta(
        name="victor",
        version="1.0.0",
        kind="penetrance_model",
        description="VICTOR competing-risk penetrance model with Hardy-Weinberg correction",
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
        """Compute a MECE PenetranceTable using the VICTOR algorithm.

        :param hazards: ValidatedHazardFrame (sex, phenotype, age 0-99, lambda_pop).
        :param phenotype_model: Active phenotype model (provides canonical names).
        :param params: Must include ``genetic_entity`` (str) and
            ``age_bands`` (list[int]). ``age_bands`` values are the start
            ages of each band; the last band extends to age 99.
        :return: ``PenetranceTable`` with MECE rows (sex, phenotype, age band,
            is_affected, penetrance_nc/het/hom).
        """
        genetic_entity: str = params["genetic_entity"]
        age_bands: list[int] = params.get("age_bands", [30, 40, 50, 60, 65, 70, 80])
        tracked: list[str] = phenotype_model.canonical_phenotypes()

        q = self.crhf_model.get_crhf(genetic_entity)

        bands = _build_bands(age_bands)
        sexes = ["F", "M"]
        rows: list[PenetranceRow] = []

        for sex in sexes:
            # Aggregate by (phenotype, age) in case of duplicate rows
            sub_all = hazards[hazards["sex"] == sex].copy()
            sub = (
                sub_all.groupby(["phenotype", "age"], observed=True)["lambda_pop"]
                .sum()
                .reset_index()
            )
            phenotype_names = list(sub["phenotype"].unique())

            # Build lambda arrays: age × phenotype → {nc, het, hom}
            lambda_nc = np.zeros((100, len(phenotype_names)))
            lambda_het = np.zeros((100, len(phenotype_names)))
            lambda_hom = np.zeros((100, len(phenotype_names)))
            lambda_pop_arr = np.zeros((100, len(phenotype_names)))

            for j, pheno in enumerate(phenotype_names):
                age_series = sub[sub["phenotype"] == pheno].set_index("age")["lambda_pop"]
                for a in range(100):
                    val = age_series.get(a, 0.0)
                    lp = float(val) if not hasattr(val, "__len__") else float(val.iloc[0])
                    lambda_pop_arr[a, j] = lp

                    if pheno == _OTHER:
                        rr_het = 1.0
                        rr_hom = 1.0
                    else:
                        rr_het = self.rr_model.get_rr(genetic_entity, sex, a, pheno, "het")
                        rr_hom = self.rr_model.get_rr(genetic_entity, sex, a, pheno, "hom")

                    # VICTOR Hardy-Weinberg correction
                    # D = 1 + 2*q*(RR_het - 1)
                    D = 1.0 + 2.0 * q * (rr_het - 1.0)
                    lnc = lp / D if D > 0 else lp
                    lambda_nc[a, j] = lnc
                    lambda_het[a, j] = rr_het * lnc
                    lambda_hom[a, j] = rr_hom * lnc

            # Step 2: all-cause hazard
            lambda_all_nc = lambda_nc.sum(axis=1)
            lambda_all_het = lambda_het.sum(axis=1)
            lambda_all_hom = lambda_hom.sum(axis=1)

            # Step 3: all-cause survival S_g(a) = exp(-sum_{i=0}^{a} lambda_all_g(i))
            S_nc = np.exp(-np.cumsum(lambda_all_nc))
            S_het = np.exp(-np.cumsum(lambda_all_het))
            S_hom = np.exp(-np.cumsum(lambda_all_hom))

            # S_prev[a] = S(a-1), with S(-1)=1
            S_nc_prev = np.concatenate([[1.0], S_nc[:-1]])
            S_het_prev = np.concatenate([[1.0], S_het[:-1]])
            S_hom_prev = np.concatenate([[1.0], S_hom[:-1]])

            # Step 4: cause-specific CIF for each phenotype
            # F_j_g(a) = sum_{i=0}^{a} S_g_prev[i] * (1 - exp(-lambda_g(j, i)))
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

            # Index map: phenotype name → column index in lambda/F arrays
            pheno_idx = {p: i for i, p in enumerate(phenotype_names)}

            # Step 5: build MECE rows from age bands
            for a0, a1 in bands:
                # F(a0-1) = 0 if a0=0, else F at last age of previous band
                f_prev_a0 = a0 - 1  # age index for "previous" age (may be -1)

                for pheno in tracked:
                    if pheno not in pheno_idx:
                        pen_nc = pen_het = pen_hom = 0.0
                    else:
                        j = pheno_idx[pheno]
                        # Band-specific CIF increment
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

                # Unaffected row: segregatr uses (1 - penetrance) for unaffected members,
                # so store 1 - S_g(a1) = CIF(a1). segregatr then computes
                # 1 - (1 - S_g(a1)) = S_g(a1) = P(cancer-free through band end | genotype).
                rows.append(
                    PenetranceRow(
                        age_start=a0,
                        age_end=a1,
                        sex=sex,  # type: ignore[arg-type]
                        phenotype="unaffected",
                        is_affected=False,
                        penetrance_nc=1.0 - float(S_nc[a1]),
                        penetrance_het=1.0 - float(S_het[a1]),
                        penetrance_hom=1.0 - float(S_hom[a1]),
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
