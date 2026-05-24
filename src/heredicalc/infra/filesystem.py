"""Filesystem-based pedigree repository (Phase 1 implementation)."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from heredicalc.core.registry.registry import PluginRegistry

from heredicalc.core.models.pedigree import Pedigree


class FilesystemPedigreeRepository:
    """PedigreeRepository backed by a directory of pedigree files.

    Each pedigree is stored as a separate file. The pedigree_id corresponds
    to the file stem (filename without extension). The format plugin is used
    for loading and saving.
    """

    def __init__(
        self,
        directory: Path,
        registry: PluginRegistry,
        format_name: str = "cool3_tsv",
    ) -> None:
        self._directory = directory
        self._format = registry.instantiate("pedigree_format", format_name, None)  # type: ignore[arg-type]
        self._extensions = {".ped", ".tsv", ".txt"}

    def _path_for(self, pedigree_id: str) -> Path | None:
        for ext in self._extensions:
            p = self._directory / f"{pedigree_id}{ext}"
            if p.exists():
                return p
        return None

    def get(self, pedigree_id: str) -> Pedigree | None:
        """Return the pedigree for *pedigree_id*, or None if not found."""
        path = self._path_for(pedigree_id)
        if path is None:
            return None
        return self._format.load(path)

    def list_ids(self) -> list[str]:
        """Return sorted list of all pedigree IDs in the directory."""
        ids = []
        for ext in self._extensions:
            for p in self._directory.glob(f"*{ext}"):
                ids.append(p.stem)
        return sorted(set(ids))

    def save(self, pedigree: Pedigree) -> None:
        """Save *pedigree* to the repository directory."""
        path = self._directory / f"{pedigree.pedigree_id}.ped"
        self._format.save(pedigree, path)

    def delete(self, pedigree_id: str) -> bool:
        """Delete the pedigree file for *pedigree_id*.

        :return: True if deleted, False if not found.
        """
        path = self._path_for(pedigree_id)
        if path is None:
            return False
        path.unlink()
        return True
