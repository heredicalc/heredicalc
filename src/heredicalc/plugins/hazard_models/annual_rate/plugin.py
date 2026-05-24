"""Annual-rate hazard model plugin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

from heredicalc.core.models.plugin import PluginMeta
from heredicalc.core.pipeline.types import HAZARD_SCHEMA, validate_frame

if TYPE_CHECKING:
    from heredicalc.plugins.protocols import TraitMapper

_OTHER = "OtherTrait"


class AnnualRateHazardModel:
    """Convert raw incidence to per-year hazard rates.

    Rate for each (sex, trait, age band): ``cases / person_years / band_width``.
    Applied uniformly to each year in ``[age_start, age_end]``.
    Traits not mapped to a tracked phenotype are aggregated as ``"OtherTrait"``.
    """

    meta = PluginMeta(
        name="annual_rate",
        version="1.0.0",
        kind="hazard_model",
        description="Annual rate hazard model: cases / person_years / band_width",
        author="HerediCalc",
        min_api_version="1.0.0",
    )

    def compute_hazards(
        self,
        incidence: pd.DataFrame,
        trait_mapper: TraitMapper,
        params: dict[str, Any],
    ) -> pd.DataFrame:
        """Convert a ValidatedIncidenceFrame to a ValidatedHazardFrame.

        :param incidence: ValidatedIncidenceFrame (sex, trait, age_start, age_end,
            cases, person_years).
        :param trait_mapper: Maps CI5 trait codes to canonical phenotype names.
        :param params: Unused by this plugin.
        :return: ValidatedHazardFrame (sex, phenotype, age 0-99, lambda_pop).
        """
        # Map trait codes to canonical phenotype names
        inc = incidence.copy()
        inc["phenotype"] = inc["trait"].map(lambda t: trait_mapper.map_trait(t) or _OTHER)

        # Compute annual rate per (sex, phenotype, age band)
        inc["band_width"] = inc["age_end"] - inc["age_start"] + 1
        inc["lambda_pop"] = np.where(
            inc["person_years"] > 0,
            inc["cases"] / inc["person_years"] / inc["band_width"],
            0.0,
        )

        # Aggregate rows with the same (sex, phenotype, age_start, age_end)
        agg = (
            inc.groupby(["sex", "phenotype", "age_start", "age_end"], observed=True)["lambda_pop"]
            .sum()
            .reset_index()
        )

        # Expand age bands to per-year rows (ages 0-99)
        rows = []
        for _, row in agg.iterrows():
            sex = row["sex"]
            phenotype = row["phenotype"]
            lam = row["lambda_pop"]
            for age in range(int(row["age_start"]), int(row["age_end"]) + 1):
                rows.append({"sex": sex, "phenotype": phenotype, "age": age, "lambda_pop": lam})

        # Ensure all 100 age years (0-99) are covered for every (sex, phenotype)
        hazard_df = pd.DataFrame(rows)
        if hazard_df.empty:
            return validate_frame(_empty_hazard_frame(), HAZARD_SCHEMA, name="annual_rate")

        # Fill missing ages with 0
        phenotypes = hazard_df["phenotype"].unique()
        sexes = list(hazard_df["sex"].unique())
        complete_rows = []
        for sex in sexes:
            for pheno in phenotypes:
                mask = (hazard_df["sex"] == sex) & (hazard_df["phenotype"] == pheno)
                sub = hazard_df[mask].set_index("age")
                for age in range(100):
                    lam = sub.loc[age, "lambda_pop"] if age in sub.index else 0.0
                    complete_rows.append({"sex": sex, "phenotype": pheno, "age": age, "lambda_pop": lam})

        result = pd.DataFrame(complete_rows)
        result["sex"] = result["sex"].astype("category")
        result["age"] = result["age"].astype("int64")
        result["lambda_pop"] = result["lambda_pop"].astype("float64")
        return validate_frame(result, HAZARD_SCHEMA, name="annual_rate")


def _empty_hazard_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["sex", "phenotype", "age", "lambda_pop"],
        dtype=object,
    ).astype({"age": "int64", "lambda_pop": "float64"}).assign(
        sex=pd.Categorical([], categories=["M", "F"])
    )
