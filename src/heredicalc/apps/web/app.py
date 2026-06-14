"""HerediCalc Streamlit frontend — minimal researcher UI over the core pipeline."""

from __future__ import annotations

import io
import json
import shutil
import tempfile
import zipfile
from importlib.resources import files as _files
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from heredicalc.core.pipeline.config_builder import build_config_from_dict
from heredicalc.core.pipeline.runner import PipelineRunner
from heredicalc.core.registry.registry import build_registry

# Belman reference case (brca1_belman_latvia_ci5ix, victor) widget pre-fill.
_REFERENCE: dict[str, Any] = {
    "genetic_entity": "BRCA1",
    "allele_freq": 0.0001,
    "population": "Latvia",
    "age_bands": "30,40,50,60,65,70,80",
    "incidence_source": "ci5_ix",
    "trait_mapper": "ci5_ix_hbopc",
}

# Fixed reference plugin selections (not exposed as widgets in this MVP).
_PHENOTYPE_MODEL = "hbopc"
_FIXED_PLUGINS = {
    "hazard_model": "annual_rate",
    "penetrance_model": "victor",
    "liability_assigner": "victor_standard",
    "flb_calculator": "segregatr",
    "pedigree_format": "cool3_tsv",
    "rr_model": "tabular",
    "crhf_model": "lookup",
}

_DEMO_PED = _files("heredicalc.apps.web") / "data" / "Belman.ped"


@st.cache_resource
def _registry():
    return build_registry()


def _compatible_trait_mappers(reg, incidence_source: str, phenotype_model: str) -> list[str]:
    names: list[str] = []
    for entry in reg.list_plugins("trait_mapper"):
        compatible = entry.meta.compatible_with
        inc_ok = incidence_source in compatible.get("incidence_source", [])
        phen_allowed = compatible.get("phenotype_model")
        phen_ok = phen_allowed is None or phenotype_model in phen_allowed
        if inc_ok and phen_ok:
            names.append(entry.meta.name)
    return sorted(set(names))


def _build_raw_config(
    genetic_entity: str,
    allele_freq: float,
    population: str,
    age_bands: list[int],
    incidence_source: str,
    trait_mapper: str,
) -> dict[str, Any]:
    return {
        "computation": {"genetic_entity": genetic_entity, "allele_freq": allele_freq},
        "plugins": {
            "incidence_source": incidence_source,
            "phenotype_model": _PHENOTYPE_MODEL,
            "trait_mapper": trait_mapper,
            **_FIXED_PLUGINS,
            "params": {
                "population": population,
                "age_bands": age_bands,
                "rr_model": _FIXED_PLUGINS["rr_model"],
                "crhf_model": _FIXED_PLUGINS["crhf_model"],
            },
        },
    }


def _short_error(exc: Exception) -> str:
    msg = str(exc).strip().splitlines()
    text = msg[0] if msg else exc.__class__.__name__
    return text if len(text) <= 300 else text[:297] + "..."


def _gather_inputs(uploads, pasted: str, use_demo: bool) -> list[tuple[str, bytes]]:
    if uploads:
        return [(f.name, f.getvalue()) for f in uploads]
    if pasted.strip():
        return [("pasted.ped", pasted.encode("utf-8"))]
    if use_demo:
        return [("Belman.ped", _DEMO_PED.read_bytes())]
    return []


def _run_all(reg, config, pedigrees: list[tuple[str, bytes]]) -> list[dict[str, Any]]:
    runner = PipelineRunner(registry=reg)
    results: list[dict[str, Any]] = []
    tmpdir = Path(tempfile.mkdtemp(prefix="heredicalc_web_"))
    try:
        for name, data in pedigrees:
            path = tmpdir / name
            try:
                path.write_bytes(data)
                manifest = runner.run_with_manifest(path, config)
                results.append(
                    {
                        "name": name,
                        "flb": manifest.flb,
                        "status": "ok",
                        "manifest": manifest.model_dump_json(indent=2),
                        "error": None,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                results.append(
                    {
                        "name": name,
                        "flb": None,
                        "status": "error",
                        "manifest": None,
                        "error": _short_error(exc),
                    }
                )
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return results


def _zip_manifests(ok_results: list[dict[str, Any]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in ok_results:
            zf.writestr(f"{Path(r['name']).stem}.manifest.json", r["manifest"])
    return buf.getvalue()


def _load_demo() -> None:
    for key, value in _REFERENCE.items():
        st.session_state[key] = value
    st.session_state["use_demo"] = True


def main() -> None:
    st.set_page_config(page_title="HerediCalc", page_icon="🧬", layout="wide")
    st.title("HerediCalc — Full Likelihood Bayes cosegregation analysis")
    st.caption(
        "Compute the FLB factor over the same core pipeline as the CLI. "
        "Each run produces a downloadable run-provenance manifest."
    )

    reg = _registry()

    for key, value in _REFERENCE.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("use_demo", False)
    st.session_state.setdefault("results", None)

    st.subheader("Parameters")
    col1, col2 = st.columns(2)
    with col1:
        genetic_entity = st.text_input("Genetic entity", key="genetic_entity")
        allele_freq = st.number_input(
            "Allele frequency",
            min_value=0.0,
            max_value=1.0,
            step=0.0001,
            format="%.5f",
            key="allele_freq",
        )
        population = st.text_input("Population", key="population")
    with col2:
        age_bands_str = st.text_input("Age bands (comma-separated)", key="age_bands")
        inc_options = sorted(e.meta.name for e in reg.list_plugins("incidence_source"))
        incidence_source = st.selectbox("Incidence source", inc_options, key="incidence_source")
        tm_options = _compatible_trait_mappers(reg, incidence_source, _PHENOTYPE_MODEL)
        if not tm_options:
            st.error(
                f"No trait_mapper is compatible with incidence source {incidence_source!r}. "
                "Pick a different source."
            )
            trait_mapper = None
        else:
            if st.session_state.get("trait_mapper") not in tm_options:
                st.session_state["trait_mapper"] = (
                    "ci5_ix_hbopc" if "ci5_ix_hbopc" in tm_options else tm_options[0]
                )
            trait_mapper = st.selectbox("Trait mapper", tm_options, key="trait_mapper")

    with st.expander("Fixed model & plugins"):
        st.write({"phenotype_model": _PHENOTYPE_MODEL, **_FIXED_PLUGINS})

    st.subheader("Pedigrees")
    uploads = st.file_uploader(
        "Upload COOL3 TSV pedigrees (.ped)", type=["ped"], accept_multiple_files=True, key="uploads"
    )
    pasted = st.text_area("…or paste a single pedigree (COOL3 TSV)", key="pasted", height=160)

    c1, c2 = st.columns(2)
    c1.button("Load demo", key="load_demo", on_click=_load_demo)
    run_clicked = c2.button("Run FLB", key="run", type="primary")

    if run_clicked:
        if trait_mapper is None:
            st.stop()
        try:
            age_bands = [int(x.strip()) for x in age_bands_str.split(",") if x.strip()]
        except ValueError:
            st.error("Age bands must be comma-separated integers, e.g. 30,40,50,60,65,70,80.")
            st.stop()
        pedigrees = _gather_inputs(uploads, pasted, st.session_state["use_demo"])
        if not pedigrees:
            st.warning("Provide a pedigree: upload files, paste one, or click “Load demo”.")
        else:
            try:
                config = build_config_from_dict(
                    _build_raw_config(
                        genetic_entity,
                        allele_freq,
                        population,
                        age_bands,
                        incidence_source,
                        trait_mapper,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Invalid configuration: {_short_error(exc)}")
                st.stop()
            with st.spinner(f"Computing FLB for {len(pedigrees)} pedigree(s)…"):
                st.session_state["results"] = _run_all(reg, config, pedigrees)

    _render_results(st.session_state.get("results"))


def _render_results(results: list[dict[str, Any]] | None) -> None:
    if not results:
        return

    st.subheader("Results")
    ok = [r for r in results if r["status"] == "ok"]

    if len(results) == 1 and ok:
        st.metric(label=f"FLB — {results[0]['name']}", value=f"{results[0]['flb']:.4f}")

    table = pd.DataFrame(
        [
            {
                "Pedigree": r["name"],
                "FLB": f"{r['flb']:.4f}" if r["flb"] is not None else "—",
                "Status": r["status"],
            }
            for r in results
        ]
    )
    st.dataframe(table, hide_index=True, use_container_width=True)

    for r in results:
        if r["status"] == "error":
            st.error(f"{r['name']}: {r['error']}")

    for i, r in enumerate(ok):
        st.download_button(
            f"Download {Path(r['name']).stem}.manifest.json",
            data=r["manifest"],
            file_name=f"{Path(r['name']).stem}.manifest.json",
            mime="application/json",
            key=f"dl_{i}",
        )

    if len(ok) > 1:
        st.download_button(
            "Download all manifests (ZIP)",
            data=_zip_manifests(ok),
            file_name="manifests.zip",
            mime="application/zip",
            key="dl_zip",
        )

    for r in ok:
        manifest = json.loads(r["manifest"])
        with st.expander(f"Provenance — {r['name']}"):
            st.json(
                {
                    "resolved_config": manifest["resolved_config"],
                    "r_session": manifest["r_session"],
                }
            )


main()
