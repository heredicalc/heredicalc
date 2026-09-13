"""Integration test: an affection the phenotype model does not track counts as unaffected.

Reproduces the study finding behind v4.4.0: a member with an untracked affection used to
be handed to segregatr as affected while sitting in an unaffected liability class, which
biased the FLB. After the fix the member is passed exactly like an ``unaff`` member with
the same age, so both codings must give the same FLB.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from heredicalc.core.pipeline.runner import PipelineRunner
from heredicalc.core.registry.registry import PluginRegistry
from tests._ci5_support import requires_real_ci5_data
from tests.integration.test_manifest_integration import _fixture_to_config, _load_case

_PEDIGREE = Path(__file__).parent.parent / "fixtures" / "pedigrees" / "Belman-3-.-.-9-.-..ped"
_MEMBER = "4"  # male, unaffected, age 41 in the fixture; hbopc does not track PrCa

requires_r = pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not on PATH")


def _variant(tmp_path: Path, affection: str) -> Path:
    lines = _PEDIGREE.read_text(encoding="utf-8").splitlines()
    out = [lines[0]]
    for line in lines[1:]:
        parts = line.split("\t")
        if parts[1] == _MEMBER:
            parts[5] = affection
        out.append("\t".join(parts))
    dest = tmp_path / f"belman_{affection}.ped"
    dest.write_text("\n".join(out) + "\n", encoding="utf-8")
    return dest


@requires_r
@requires_real_ci5_data
def test_untracked_affection_equals_unaffected_coding(tmp_path: Path) -> None:
    case = _load_case()
    assert case is not None
    config = _fixture_to_config(case["config"])
    registry = PluginRegistry()
    registry.discover_all()
    runner = PipelineRunner(registry=registry)
    flb_untracked = runner.run(_variant(tmp_path, "PrCa"), config)
    flb_unaff = runner.run(_variant(tmp_path, "unaff"), config)
    flb_unknown = runner.run(_variant(tmp_path, "."), config)
    assert flb_untracked == pytest.approx(flb_unaff, rel=1e-12)
    assert flb_unknown != pytest.approx(flb_unaff, rel=1e-6)  # '.' stays affection-unknown
