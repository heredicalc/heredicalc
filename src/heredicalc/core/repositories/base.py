"""Abstract repository interfaces (Protocols)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from heredicalc.core.models.pedigree import Pedigree


@runtime_checkable
class PedigreeRepository(Protocol):
    """Abstract persistence interface for pedigree records."""

    def get(self, pedigree_id: str) -> Pedigree | None: ...

    def list_ids(self) -> list[str]: ...

    def save(self, pedigree: Pedigree) -> None: ...

    def delete(self, pedigree_id: str) -> bool: ...
