"""Read/write helpers for the user-local traits.yaml manifest."""

from __future__ import annotations

import yaml

from heredicalc.core.app_dirs import user_traits_dir

VALID_KINDS: frozenset[str] = frozenset(
    {"gene", "chromosomal_anomaly", "epigenetic", "polygenic_score", "other"}
)


def load_manifest() -> list[dict]:
    path = user_traits_dir() / "traits.yaml"
    if not path.exists():
        return []
    return yaml.safe_load(path.read_text(encoding="utf-8")) or []


def save_manifest(entries: list[dict]) -> None:
    path = user_traits_dir() / "traits.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(entries, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )


def get_entry(name: str) -> dict | None:
    return next((e for e in load_manifest() if e["name"] == name), None)


def upsert_entry(entry: dict) -> None:
    entries = [e for e in load_manifest() if e["name"] != entry["name"]]
    entries.append(entry)
    save_manifest(entries)


def remove_entry(name: str) -> bool:
    """Remove the entry for *name*. Returns True if an entry was removed."""
    old = load_manifest()
    new = [e for e in old if e["name"] != name]
    save_manifest(new)
    return len(new) < len(old)
