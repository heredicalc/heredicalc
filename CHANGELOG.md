# Changelog

All notable changes to HerediCalc are documented here.

This file is auto-generated from Conventional Commits via
[git-cliff](https://github.com/orhun/git-cliff).

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
