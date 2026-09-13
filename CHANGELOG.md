# Changelog

All notable changes to HerediCalc are documented here.

This file is auto-generated from Conventional Commits via
[git-cliff](https://github.com/orhun/git-cliff).

## [4.4.0] — 2026-09-13

### Breaking
- The affected status handed to the FLB engine now follows the assigned liability
  class instead of the raw pedigree flag. A member whose affection the active
  phenotype model does not track (for example a non-TNBC breast cancer under a
  TNBC-only model) is assigned the unaffected class by `victor_standard` and is
  now also passed to `segregatr` as unaffected. Previously the raw flag was
  passed through, so `segregatr` scored such members with the cumulative
  penetrance of the tracked phenotype as if they were cases of it — a directed
  bias (a factor above 1 for every carrier, below 1 for every non-carrier).
  Results of earlier runs with phenotype models that do not track every affection
  present in a pedigree can change; that is the purpose of the fix. Members with
  tracked affections and `.` (affection unknown) members are unaffected by the
  change.

### Fixed
- `segregatr` derives `is_affected` per member from the assigned `PenetranceRow`
  (`pedigree affected AND row.is_affected`); the zero-penetrance guard uses the
  same status, so an untracked affection in an all-zero unaffected class no
  longer raises. The `ZeroPenetranceError` contract of 4.3.0 is otherwise
  unchanged: the two guards do not overlap for tracked affections.

## [4.3.0] — 2026-09-12

### Breaking
- Affected pedigree members without penetrance data now raise instead of silently
  yielding `NaN`. When an affected member falls into a liability class whose
  penetrance is zero or undefined for every genotype (typically a sex or other
  subgroup for which the incidence source or RR model has no rows, e.g. males under a
  female-only model), `victor_standard` and `segregatr` raise
  `heredicalc.core.exceptions.ZeroPenetranceError`. The exception carries the
  member's `individual_id`, the `group` without data (sex, phenotype, age band), a
  `reason`, and, from `segregatr`, the `pedigree_id`. Callers that relied on
  receiving a `NaN` FLB for such pedigrees must now handle the exception (it is a
  `HerediCalcError`). Unaffected members in such classes are assigned exactly as
  before.

### Fixed
- `segregatr` no longer wraps a `ZeroPenetranceError` into a generic `SegregaError`;
  it is re-raised unchanged so callers can handle it specifically.

### Added
- `PenetranceRow.has_penetrance` and `PenetranceRow.liability_group` helpers, shared
  by the two guards.

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
