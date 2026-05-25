"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def pedigrees_dir() -> Path:
    return FIXTURES_DIR / "pedigrees"


@pytest.fixture
def validation_fixtures() -> list[dict]:
    path = FIXTURES_DIR / "validation_fixtures.json"
    if not path.exists():
        pytest.skip("validation_fixtures.json not yet copied from _bootstrap/")
    with open(path) as f:
        return json.load(f)
