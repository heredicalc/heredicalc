"""Pipeline-internal data types and DataFrame schema validators."""

from __future__ import annotations

from typing import Literal

import pandas as pd
from pydantic import BaseModel

from heredicalc.core.exceptions import DataSchemaError


class HazardArray(BaseModel):
    """Yearly hazard rates for one (sex, phenotype) combination, ages 0–99."""

    sex: Literal["M", "F"]
    phenotype: str
    lambda_pop: list[float]
    lambda_nc: list[float]
    lambda_het: list[float]
    lambda_hom: list[float]


INCIDENCE_SCHEMA: dict[str, str] = {
    "sex": "category",
    "trait": "object",
    "age_start": "int64",
    "age_end": "int64",
    "cases": "float64",
    "person_years": "float64",
}

HAZARD_SCHEMA: dict[str, str] = {
    "sex": "category",
    "phenotype": "object",
    "age": "int64",
    "lambda_pop": "float64",
}


def validate_frame(df: pd.DataFrame, schema: dict[str, str], name: str = "") -> pd.DataFrame:
    """Validate that df has the required columns and dtypes.

    :raises DataSchemaError: if columns are missing or dtypes wrong.
    """
    missing = set(schema) - set(df.columns)
    if missing:
        raise DataSchemaError(
            f"DataFrame{' ' + name if name else ''} missing columns: {sorted(missing)}"
        )
    wrong = {
        col: (str(df[col].dtype), expected)
        for col, expected in schema.items()
        if col in df.columns and not _dtype_matches(df[col].dtype, expected)
    }
    if wrong:
        details = ", ".join(f"{c}: got {a} want {e}" for c, (a, e) in wrong.items())
        raise DataSchemaError(
            f"DataFrame{' ' + name if name else ''} dtype mismatches: {details}"
        )
    return df


def _dtype_matches(dtype: object, expected: str) -> bool:
    dtype_str = str(dtype)
    if expected == "category":
        return dtype_str == "category"
    if expected == "object":
        return dtype_str in ("object", "string", "str")
    if expected == "int64":
        return dtype_str in ("int64", "Int64")
    if expected == "float64":
        return dtype_str in ("float64", "Float64")
    return dtype_str == expected
