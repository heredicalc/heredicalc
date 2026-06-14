# Reproducibility & Provenance

Every FLB run can emit a **run-provenance manifest**: a single machine-readable
JSON document that records everything needed to reproduce the result — the
resolved configuration, the exact plugin versions that ran, the Python and R
environments, and a content hash of each input pedigree.

The manifest is produced by the core `PipelineRunner`, so the CLI and the
Streamlit frontend share one implementation and emit byte-for-byte identical
manifests for the same run.

## When is a manifest written?

Manifests are **on by default** for both `run` and `batch`. Each run writes a
sidecar file named `<pedigree-stem>.manifest.json` next to the pedigree:

```bash
# Writes Belman.manifest.json next to Belman.ped
heredicalc run Belman.ped -c config.yml

# All sidecars collected in one directory
heredicalc run Belman.ped -c config.yml --manifest-dir ./manifests

# Disable manifest generation entirely
heredicalc run Belman.ped -c config.yml --no-manifest

# batch behaves identically, one manifest per pedigree
heredicalc batch ./pedigrees -c config.yml --manifest-dir ./manifests
```

The manifest is **always a separate file** — it is never part of `stdout`. The
existing `stdout` contract is unchanged, including `--format json`, which still
prints only `{"pedigree": ..., "flb": ...}`. The path of each written manifest is
reported on `stderr`.

## Schema

| Field | Type | Description |
|-------|------|-------------|
| `heredicalc_version` | `str` | Installed HerediCalc version (`importlib.metadata`). |
| `python_version` | `str` | Running CPython version, e.g. `3.12.5`. |
| `python_packages` | `dict[str, str]` | Versions of the declared runtime dependencies plus `heredicalc`. |
| `r_session` | `object \| null` | R version, platform, and all namespaces loaded after the `FLB()` call (`null` if the calculator exposes no session info). |
| `resolved_config` | `object` | The `PipelineConfig` **after** the penetrance-model defaults cascade — the effective parameters, not the raw input. |
| `inputs` | `list` | One entry per pedigree file: `filename` and the SHA-256 over its raw bytes. |
| `plugins` | `list` | `kind`, `name`, and `version` for **all ten** plugin selections, including the injected `rr_model` and `crhf_model` sub-plugins. |
| `timestamp_utc` | `str` | Run time as an ISO 8601 UTC timestamp. |
| `flb` | `float` | The computed FLB factor (identical to the `run` output). |

Notes:

- **`resolved_config`** is captured after the cascade, so plugin-specific defaults
  (e.g. `victor_cool3` selecting `annual_rate_cool3` as its `hazard_model`) are
  recorded as the values that actually ran.
- **`inputs[].sha256`** is computed over the raw file bytes, so it is stable and
  reproducible across machines for an unchanged pedigree.
- **`plugins`** is derived from `resolved_config` via the registry, capturing the
  resolved version of every selected plugin — including sub-plugins that are
  injected into other plugins and never instantiated directly by the runner.
- **`r_session`** comes from the `segregatr` R subprocess, which reports its
  version, platform, and `loadedNamespaces()` in the same JSON object as the FLB.

## Example manifest

Produced by the primary validation case `brca1_belman_latvia_ci5ix`
(`penetrance_model: victor`). The `loaded_namespaces` map is abbreviated here:

```json
{
  "heredicalc_version": "4.1.0",
  "python_version": "3.12.5",
  "python_packages": {
    "pandas": "2.3.2",
    "numpy": "2.3.2",
    "pydantic": "2.13.4",
    "packaging": "25.0",
    "platformdirs": "4.4.0",
    "PyYAML": "6.0.3",
    "typer": "0.25.1",
    "rich": "15.0.0",
    "heredicalc": "4.1.0"
  },
  "r_session": {
    "r_version": "R version 4.4.1 (2024-06-14)",
    "platform": "aarch64-apple-darwin20",
    "loaded_namespaces": {
      "base": "4.4.1",
      "pedtools": "2.7.0",
      "segregatr": "0.5.0",
      "stats": "4.4.1",
      "utils": "4.4.1"
    }
  },
  "resolved_config": {
    "computation": {
      "genetic_entity": "BRCA1",
      "allele_freq": 0.0001
    },
    "plugins": {
      "incidence_source": "ci5_ix",
      "phenotype_model": "hbopc",
      "trait_mapper": "ci5_ix_hbopc",
      "hazard_model": "annual_rate",
      "penetrance_model": "victor",
      "rr_model": "tabular",
      "crhf_model": "lookup",
      "liability_assigner": "victor_standard",
      "flb_calculator": "segregatr",
      "pedigree_format": "cool3_tsv",
      "params": {
        "population": "Latvia",
        "age_bands": [30, 40, 50, 60, 65, 70, 80],
        "rr_model": "tabular",
        "crhf_model": "lookup"
      }
    }
  },
  "inputs": [
    {
      "filename": "Belman.ped",
      "sha256": "57d5eca9fa68803e21a997ab79cbf203415bea49760e0a47fd2cef4b9904d52e"
    }
  ],
  "plugins": [
    { "kind": "pedigree_format", "name": "cool3_tsv", "version": "1.0.0" },
    { "kind": "phenotype_model", "name": "hbopc", "version": "1.0.0" },
    { "kind": "incidence_source", "name": "ci5_ix", "version": "1.0.0" },
    { "kind": "trait_mapper", "name": "ci5_ix_hbopc", "version": "1.0.0" },
    { "kind": "hazard_model", "name": "annual_rate", "version": "1.0.0" },
    { "kind": "penetrance_model", "name": "victor", "version": "1.0.0" },
    { "kind": "liability_assigner", "name": "victor_standard", "version": "1.0.0" },
    { "kind": "flb_calculator", "name": "segregatr", "version": "1.0.0" },
    { "kind": "rr_model", "name": "tabular", "version": "1.0.0" },
    { "kind": "crhf_model", "name": "lookup", "version": "1.0.0" }
  ],
  "timestamp_utc": "2026-06-14T10:56:01.381292+00:00",
  "flb": 25.6540503665
}
```

## Programmatic access

The manifest is a Pydantic model, so any frontend can obtain it directly instead
of parsing the sidecar:

```python
from pathlib import Path

from heredicalc.core.pipeline.runner import PipelineRunner

manifest = PipelineRunner(registry=registry).run_with_manifest(
    Path("Belman.ped"), config
)
print(manifest.flb)
print(manifest.model_dump_json(indent=2))
```

`run()` remains unchanged and returns the bare FLB `float`; `run_with_manifest()`
runs the same pipeline and additionally assembles the manifest.
