# Changelog

All notable changes to HerediCalc are documented here.

This file is auto-generated from Conventional Commits via
[git-cliff](https://github.com/orhun/git-cliff).

## [4.2.0] - 2026-06-17

### Added
- Run-provenance manifest: `PipelineRunner.run_with_manifest()` records the
  HerediCalc, Python, and R versions, the loaded R namespaces, the fully resolved
  configuration, the selected plugins and their versions, the SHA-256 of every input
  pedigree, and the computed FLB — serialisable for reproducible runs.
- Streamlit web frontend over the core pipeline: multi-file pedigree upload,
  registry-fed plugin and population dropdowns, a one-click demo run, and a
  downloadable run-provenance manifest per result (plus a combined ZIP).
- `scripts/fetch_ci5_data.py` (with `scripts/ci5_checksums.txt`) to obtain the CI5
  incidence data from IARC and verify it byte-for-byte, and `DATA-NOTICE.md`
  documenting IARC's terms of use and the per-volume citations.
- `HEREDICALC_CI5_DATA_DIR` environment variable to point the incidence-source
  plugins at a CI5 data directory outside the installed package.

### Changed
- CI now runs a fast lane against de-minimis fixtures on every push/PR (no data
  download) and a separate full-validation lane (on `v*` tags and manual dispatch)
  that fetches the CI5 data and runs the complete FLB validation suite.
- The release workflow publishes from the canonical repository itself using the
  built-in `GITHUB_TOKEN`: it builds the sdist + wheel, creates the GitHub Release
  with notes drawn from this changelog and the artifacts attached, and deploys the
  documentation to GitHub Pages.

### Removed
- The CI5 incidence data is no longer distributed with the repository. The code stays
  MIT-licensed; the data is © IARC and must be obtained separately under IARC's terms
  via `scripts/fetch_ci5_data.py` (see `DATA-NOTICE.md`).
- The release pipeline's circular self force-push and its non-functional PyPI
  publishing step were removed; PyPI publishing is deferred.

## [4.1.0] — 2026-05-25

### Features
- `heredicalc add/edit/clone/remove trait` — CRUD für nutzerdefinierte Traits
  mit `traits.yaml`-Manifest, `kind`-Vokabular und freien Metadatenfeldern
- `heredicalc add config` — ersetzt `heredicalc init` (bleibt als deprecated alias)
- `hbopc_prca` phenotype model + 5 CI5-Mapper mit ProstateCancer (C61)
  (CI5-VIII: 154, CI5-IX/X: 151, CI5-XI: 147, CI5-XII: 197)
- `tabular` RR-Modell und `lookup` CRHF-Modell prüfen User-Datenverzeichnis
  vor bundled Daten

### Internal
- `src/heredicalc/core/app_dirs.py` — User-Datenpfade
- `src/heredicalc/core/trait_manifest.py` — traits.yaml Lese/Schreib-Helfer

<!-- releases will be inserted here -->
