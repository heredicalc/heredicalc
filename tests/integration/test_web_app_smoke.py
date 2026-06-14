"""Smoke test for the Streamlit web app via AppTest (headless)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

_APP = Path(__file__).parent.parent.parent / "src" / "heredicalc" / "apps" / "web" / "app.py"


def test_app_renders_without_exception() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_APP), default_timeout=60)
    at.run()
    assert not at.exception


def test_dropdowns_are_registry_fed() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_APP), default_timeout=60)
    at.run()
    assert not at.exception

    def options(key: str) -> list[str]:
        return list(at.selectbox(key=key).options)

    # Every dropdown is populated from the discovered registry, not a hardcoded list.
    assert {"ci5_ix", "ci5_viii"} <= set(options("incidence_source"))
    assert "hbopc" in options("phenotype_model")
    assert "ci5_ix_hbopc" in options("trait_mapper")
    assert "tabular" in options("rr_model")
    assert "lookup" in options("crhf_model")
    # Population is fed from the selected incidence source's list_sources()
    # (labels carry the study period via format_func; the value stays the name).
    assert any(o.startswith("Latvia") for o in options("population"))


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not available")
def test_demo_run_yields_reference_flb() -> None:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(_APP), default_timeout=180)
    at.run()
    at.button(key="load_demo").click().run()
    at.button(key="run").click().run()

    assert not at.exception
    results = at.session_state["results"]
    assert results is not None
    assert len(results) == 1
    assert results[0]["status"] == "ok"
    assert results[0]["flb"] == pytest.approx(25.6540503665, rel=0.06)
