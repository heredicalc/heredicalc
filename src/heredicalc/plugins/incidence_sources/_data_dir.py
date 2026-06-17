"""Resolve a CI5 band's data directory, overridable via ``HEREDICALC_CI5_DATA_DIR``.

When the variable is set, ``$HEREDICALC_CI5_DATA_DIR/<band>/`` is used (e.g. test
fixtures or a fetched-data cache); otherwise the packaged ``data/`` directory. With
the variable unset and the data present, the result is identical to the former
hard-coded ``_files(__package__) / "data"`` path.
"""

from __future__ import annotations

import os
from importlib.resources import files as _files
from pathlib import Path

ENV_VAR = "HEREDICALC_CI5_DATA_DIR"


def ci5_data_dir(package: str) -> Path:
    override = os.environ.get(ENV_VAR)
    if override:
        band = package.rsplit(".", 1)[-1]
        return Path(override) / band
    return Path(str(_files(package) / "data"))
