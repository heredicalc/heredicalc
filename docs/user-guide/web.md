# Web Application

The Streamlit frontend is a minimal researcher UI over the **same core pipeline**
as the CLI. It computes the FLB factor for one or more pedigrees and produces a
downloadable run-provenance manifest for every run — identical to what the CLI
emits, because both call `PipelineRunner.run_with_manifest` through the shared
`build_config_from_dict` helper.

## Launch

Install the web extra and start the app:

```bash
pip install -e ".[web]"
streamlit run src/heredicalc/apps/web/app.py
```

The app opens in your browser (default <http://localhost:8501>).

## Parameters

The form is pre-filled with the primary Belman reference case
(`brca1_belman_latvia_ci5ix`, `victor`):

| Widget | Default | Notes |
|--------|---------|-------|
| Genetic entity | `BRCA1` | |
| Allele frequency | `0.0001` | Hardy-Weinberg prior |
| Population | `Latvia` | Resolved by the incidence source |
| Age bands | `30,40,50,60,65,70,80` | Comma-separated integers |
| Incidence source | `ci5_ix` | Dropdown of registered incidence sources |
| Trait mapper | `ci5_ix_hbopc` | Dropdown of mappers **compatible** with the chosen source |

The remaining plugin selections (`phenotype_model`, `hazard_model`,
`penetrance_model`, `liability_assigner`, `flb_calculator`, `pedigree_format`,
`rr_model`, `crhf_model`) are fixed to the reference defaults and shown in the
*Fixed model & plugins* panel.

### Coupling of incidence source and trait mapper

The trait-mapper dropdown is derived from the selected incidence source using the
plugins' declared `compatible_with` metadata — the same mechanism the registry
uses for compatibility validation, so no plugin names are hardcoded. When you
change the incidence source, the trait-mapper list updates automatically. If no
compatible trait mapper exists for a source, the app shows a clear error instead
of running.

## Providing pedigrees

Three ways, in precedence order:

1. **Upload** one or more COOL3 TSV `.ped` files (`Upload COOL3 TSV pedigrees`).
2. **Paste** a single pedigree into the text area.
3. **Load demo** — loads the bundled Belman pedigree and resets the parameters to
   the reference values. Clicking **Run FLB** then yields FLB ≈ 25.65.

Uploaded files are written to temporary files (the runner takes a path) and
cleaned up after the run.

## Results and manifests

- A single pedigree shows its FLB prominently; multiple pedigrees produce a
  results table (pedigree, FLB, status).
- Each successful run offers a **`<pedigree>.manifest.json`** download
  (`RunManifest.model_dump_json`); with several pedigrees you can also download
  **all manifests as a ZIP**.
- An expandable **Provenance** panel per run shows the manifest's
  `resolved_config` and `r_session`.

## Error handling

Parsing and validation are delegated to the `pedigree_format` plugin. Invalid or
empty pedigrees, parse errors, a missing `Rscript`, or R-side failures are caught
and shown as a friendly `st.error` message — never a stack trace. In a batch, one
failing pedigree does not abort the others: its row is marked `error` with a short
reason while the rest complete.
