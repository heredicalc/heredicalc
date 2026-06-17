"""Shared helpers for CI5 data-dependent tests.

The full CI5 incidence data is not committed. When it is absent from the package,
tests run against the de-minimis mini fixtures under ``tests/fixtures/ci5_mini`` via
``HEREDICALC_CI5_DATA_DIR``. The real-FLB validation tests are skipped unless the full
data is installed (e.g. via ``python scripts/fetch_ci5_data.py``).
"""

from __future__ import annotations

import os
from importlib.resources import files as _files
from pathlib import Path

import pytest

from heredicalc.plugins.incidence_sources._data_dir import ENV_VAR

MINI_FIXTURES = Path(__file__).parent / "fixtures" / "ci5_mini"


def real_ci5_data_present() -> bool:
    """True when the full packaged CI5 data is installed (not just mini fixtures)."""
    latvia = _files("heredicalc.plugins.incidence_sources.ci5_ix") / "data" / "54280099.csv"
    return Path(str(latvia)).is_file()


def ensure_ci5_data_env() -> None:
    """Point plugins at the mini fixtures when the full data is not installed."""
    if not real_ci5_data_present():
        os.environ.setdefault(ENV_VAR, str(MINI_FIXTURES))


requires_real_ci5_data = pytest.mark.skipif(
    not real_ci5_data_present(),
    reason="full CI5 incidence data not installed (run scripts/fetch_ci5_data.py)",
)
