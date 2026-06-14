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
    "phenotype_model": "hbopc",
    "trait_mapper": "ci5_ix_hbopc",
    "rr_model": "tabular",
    "crhf_model": "lookup",
}

# Fixed model backbone (display-only; not exposed as selectable widgets).
_PENETRANCE_MODEL = "victor"
_FIXED_PLUGINS = {
    "hazard_model": "annual_rate",
    "penetrance_model": _PENETRANCE_MODEL,
    "liability_assigner": "victor_standard",
    "flb_calculator": "segregatr",
    "pedigree_format": "cool3_tsv",
}

_LABELS = {"trait_mapper": "Trait mapper", "rr_model": "RR model", "crhf_model": "CRHF model"}

_DEMO_PED = _files("heredicalc.apps.web") / "data" / "Belman.ped"


@st.cache_resource
def _registry():
    return build_registry()


@st.cache_data(show_spinner=False)
def _population_sources(incidence_source: str) -> list[tuple[str, str, str]]:
    reg = _registry()
    plugin = reg.resolve("incidence_source", incidence_source).plugin_class()
    sources = [(s.source_id, s.name, s.study_period) for s in plugin.list_sources()]
    return sorted(sources, key=lambda t: (t[1], t[0]))


def _compatible_names(reg, kind: str, selections: dict[str, str]) -> list[str]:
    """Names of registered *kind* plugins compatible with the current selections.

    A candidate is rejected only if it explicitly declares a ``compatible_with``
    entry for a selected kind that excludes the selected plugin. Plugins that
    declare nothing for a kind are treated as universally compatible.
    """
    names: list[str] = []
    for entry in reg.list_plugins(kind):
        compatible = entry.meta.compatible_with
        ok = True
        for sel_kind, sel_name in selections.items():
            allowed = compatible.get(sel_kind)
            if allowed is not None and sel_name not in allowed:
                ok = False
                break
        if ok:
            names.append(entry.meta.name)
    return sorted(set(names))


def _dependent_selectbox(reg, kind: str, label: str, selections: dict[str, str], default: str):
    options = _compatible_names(reg, kind, selections)
    if not options:
        st.error(f"No {kind} is compatible with the current selection.")
        return None
    if st.session_state.get(kind) not in options:
        st.session_state[kind] = default if default in options else options[0]
    return st.selectbox(label, options, key=kind)


def _build_raw_config(
    genetic_entity: str,
    allele_freq: float,
    population: str,
    age_bands: list[int],
    incidence_source: str,
    phenotype_model: str,
    trait_mapper: str,
    rr_model: str,
    crhf_model: str,
) -> dict[str, Any]:
    return {
        "computation": {"genetic_entity": genetic_entity, "allele_freq": allele_freq},
        "plugins": {
            "incidence_source": incidence_source,
            "phenotype_model": phenotype_model,
            "trait_mapper": trait_mapper,
            "rr_model": rr_model,
            "crhf_model": crhf_model,
            **_FIXED_PLUGINS,
            "params": {
                "population": population,
                "age_bands": age_bands,
                "rr_model": rr_model,
                "crhf_model": crhf_model,
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
        age_bands_str = st.text_input("Age bands (comma-separated)", key="age_bands")
    with col2:
        inc_options = sorted(e.meta.name for e in reg.list_plugins("incidence_source"))
        incidence_source = st.selectbox("Incidence source", inc_options, key="incidence_source")

        phen_options = sorted(e.meta.name for e in reg.list_plugins("phenotype_model"))
        if st.session_state.get("phenotype_model") not in phen_options:
            st.session_state["phenotype_model"] = (
                "hbopc" if "hbopc" in phen_options else phen_options[0]
            )
        phenotype_model = st.selectbox("Phenotype model", phen_options, key="phenotype_model")

        population = _population_selectbox(incidence_source)

    trait_mapper, rr_model, crhf_model = _data_plugin_selectboxes(
        reg, incidence_source, phenotype_model
    )

    with st.expander("Fixed model & plugins"):
        st.write(_FIXED_PLUGINS)

    st.subheader("Pedigrees")
    uploads = st.file_uploader(
        "Upload COOL3 TSV pedigrees (.ped)", type=["ped"], accept_multiple_files=True, key="uploads"
    )
    pasted = st.text_area("…or paste a single pedigree (COOL3 TSV)", key="pasted", height=160)

    c1, c2 = st.columns(2)
    c1.button("Load demo", key="load_demo", on_click=_load_demo)
    run_clicked = c2.button("Run FLB", key="run", type="primary")

    if run_clicked:
        selections = {
            "population": population,
            "trait_mapper": trait_mapper,
            "rr_model": rr_model,
            "crhf_model": crhf_model,
        }
        missing = [k for k, v in selections.items() if v is None]
        if missing:
            st.error("Cannot run — no compatible selection for: " + ", ".join(missing) + ".")
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
                        phenotype_model,
                        trait_mapper,
                        rr_model,
                        crhf_model,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Invalid configuration: {_short_error(exc)}")
                st.stop()
            with st.spinner(f"Computing FLB for {len(pedigrees)} pedigree(s)…"):
                st.session_state["results"] = _run_all(reg, config, pedigrees)

    _render_results(st.session_state.get("results"))


def _default_population_id(sources: list[tuple[str, str, str]]) -> str:
    # Resolve the reference population name (used by "Load demo") to its source_id.
    for source_id, name, _ in sources:
        if name == _REFERENCE["population"]:
            return source_id
    return sources[0][0]


def _population_selectbox(incidence_source: str) -> str | None:
    try:
        sources = _population_sources(incidence_source)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not load populations for {incidence_source!r}: {_short_error(exc)}")
        return None
    if not sources:
        st.error(f"Incidence source {incidence_source!r} exposes no populations.")
        return None
    ids = [source_id for source_id, _, _ in sources]
    label_by_id = {
        source_id: f"{name} ({period})" if period else name for source_id, name, period in sources
    }
    # The selection VALUE is the unambiguous source_id; the label stays readable.
    if st.session_state.get("population") not in ids:
        st.session_state["population"] = _default_population_id(sources)
    return st.selectbox(
        "Population", ids, key="population", format_func=lambda sid: label_by_id[sid]
    )


def _data_plugin_selectboxes(reg, incidence_source: str, phenotype_model: str):
    st.caption("Data plugins (restricted to selections compatible with the parameters above)")
    pen_entry = reg.resolve("penetrance_model", _PENETRANCE_MODEL)
    dep_kinds = list(pen_entry.meta.requires.keys())

    cols = st.columns(1 + len(dep_kinds))
    with cols[0]:
        trait_mapper = _dependent_selectbox(
            reg,
            "trait_mapper",
            _LABELS["trait_mapper"],
            {"incidence_source": incidence_source, "phenotype_model": phenotype_model},
            _REFERENCE["trait_mapper"],
        )

    sub_selections = {
        "incidence_source": incidence_source,
        "phenotype_model": phenotype_model,
        "penetrance_model": _PENETRANCE_MODEL,
    }
    dep_values: dict[str, str | None] = {}
    for i, dep_kind in enumerate(dep_kinds, start=1):
        with cols[i]:
            dep_values[dep_kind] = _dependent_selectbox(
                reg,
                dep_kind,
                _LABELS.get(dep_kind, dep_kind.replace("_", " ").title()),
                sub_selections,
                _REFERENCE.get(dep_kind, ""),
            )
    return trait_mapper, dep_values.get("rr_model"), dep_values.get("crhf_model")


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
