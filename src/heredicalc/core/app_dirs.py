"""User data directory paths for HerediCalc."""

from __future__ import annotations

from pathlib import Path

import platformdirs


def user_data_dir() -> Path:
    return Path(platformdirs.user_data_dir("heredicalc"))


def user_traits_dir() -> Path:
    return user_data_dir() / "traits"
