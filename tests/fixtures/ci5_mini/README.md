# CI5 mini fixtures (de-minimis)

These are **de-minimis excerpts** of the *Cancer Incidence in Five Continents*
(CI5) dataset, **© IARC**, used only to exercise the structure of the CI5
incidence-source adapters offline. They are not a substitute for the dataset and
must not be used for analysis. See the repository's
[`DATA-NOTICE.md`](../../../DATA-NOTICE.md) for IARC's terms and the full citation
per volume; obtain the complete data via `python scripts/fetch_ci5_data.py`.

The test suite points the plugins here via `HEREDICALC_CI5_DATA_DIR` when the full
packaged data is absent (see `tests/_ci5_support.py`). Each `<band>/` directory
mirrors the layout the plugins expect (`$HEREDICALC_CI5_DATA_DIR/<band>/`).

## What was kept (bytes copied verbatim from the source files)

- **ci5_ix/** — the full `registry.txt` dictionary (so list/lookup tests see all
  300 registries) plus `54280099.csv` (Latvia) trimmed to the breast-cancer rows
  (trait `113`).
- **ci5_viii/** — the full `registry.txt` dictionary (229 registries) plus
  `CI5-VIII.csv` trimmed to registry `1` (Algeria, Algiers), breast trait `116`.
- **ci5_xi/** — `registry_detailed.txt` and `cancer_detailed.txt` trimmed to a
  single registry (`101200199`, Algeria, Sétif) and the breast entry (`111`), plus
  that registry's CSV trimmed to the breast rows.
- **ci5_xii/** — `registry_detailed.txt` trimmed to a single registry (`101200399`,
  Algeria, Batna) plus that registry's CSV trimmed to the ovary aggregate (`178`)
  and one morphology sub-site (`179`, to exercise sub-site exclusion).

`ci5_x` has no adapter test and is therefore not included.
