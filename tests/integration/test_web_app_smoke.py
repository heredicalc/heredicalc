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
