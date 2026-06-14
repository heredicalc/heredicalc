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
| Genetic entity | `BRCA1` | Free text |
| Allele frequency | `0.0001` | Hardy-Weinberg prior |
| Age bands | `30,40,50,60,65,70,80` | Comma-separated integers |
| Incidence source | `ci5_ix` | Dropdown of **registered** incidence sources |
| Phenotype model | `hbopc` | Dropdown of **registered** phenotype models |
| Population | `Latvia` | Dropdown from the chosen source's `list_sources()` |
| Trait mapper | `ci5_ix_hbopc` | Dropdown of mappers **compatible** with the source + phenotype model |
| RR model | `tabular` | Dropdown of registered RR models compatible with the selection |
| CRHF model | `lookup` | Dropdown of registered CRHF models compatible with the selection |

Every dropdown is populated from the registry discovered by `build_registry()` /
`discover_all()` — never from a hardcoded list — so externally installed plugins
appear automatically (see [External plugins in the dropdowns](#external-plugins-in-the-dropdowns)).

The model backbone (`hazard_model`, `penetrance_model=victor`,
`liability_assigner`, `flb_calculator=segregatr`, `pedigree_format=cool3_tsv`) is
fixed to the reference defaults and shown in the *Fixed model & plugins* panel.

### Population dropdown

The population is a dropdown filled from the selected incidence source's
`list_sources()` (each label shows the source name and study period). The chosen
name is passed as `params["population"]`; the runner resolves it via
`find_source_id`. Changing the incidence source refreshes the list; a source that
exposes no populations shows a clear error.

### Dependent plugin coupling

The trait-mapper, RR-model, and CRHF-model dropdowns are derived from the current
selections using the plugins' declared `compatible_with`/`requires` metadata — the
same mechanism the registry uses for compatibility validation, so no plugin names
are hardcoded:

- **Trait mapper** declares `compatible_with = {incidence_source, phenotype_model}`,
  so its list is restricted to mappers compatible with *both* the chosen incidence
  source and phenotype model.
- **RR model / CRHF model** are present because the fixed `penetrance_model`
  (`victor`) declares `requires = {rr_model, crhf_model}`; the app derives which
  sub-plugin kinds to offer from that `requires`. The built-in `tabular`/`lookup`
  declare no `compatible_with`, so they are universally compatible; a study-specific
  RR/CRHF plugin that declares `compatible_with = {phenotype_model: [...]}` is
  filtered to the matching phenotype models by the same rule.

When you change the incidence source or phenotype model, the dependent dropdowns
update automatically. If no compatible plugin exists for a kind, the app shows a
clear error instead of running.

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

## External plugins in the dropdowns

Because every dropdown is fed from the discovered registry, study-specific plugins
loaded via `HEREDICALC_PLUGIN_PATH` appear automatically alongside the built-ins —
no code change to the app. Point HerediCalc at your plugin directory before
launching:

```bash
export HEREDICALC_PLUGIN_PATH=~/my_project/plugins
streamlit run src/heredicalc/apps/web/app.py
```

A new `phenotype_model` shows up in the phenotype dropdown; a new
`incidence_source` adds its populations; and a `trait_mapper`/`rr_model`/`crhf_model`
that declares the appropriate `compatible_with` is offered automatically whenever
its declared selection is active. See
[External Plugins](../plugins/external-plugins.md) for the plugin file layout and
discovery rules.

## Error handling

Parsing and validation are delegated to the `pedigree_format` plugin. Invalid or
empty pedigrees, parse errors, a missing `Rscript`, or R-side failures are caught
and shown as a friendly `st.error` message — never a stack trace. In a batch, one
failing pedigree does not abort the others: its row is marked `error` with a short
reason while the rest complete. A genetic entity with no RR/CRHF data surfaces the
same way — a clear error row, not a crash.
