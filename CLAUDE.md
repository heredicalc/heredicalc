# HerediCalc v4 — Claude Code Conventions

## Project Overview

HerediCalc v4 computes the Full Likelihood Bayes (FLB) factor for Bayesian
cosegregation analysis in hereditary genetics. Given a pedigree with known
phenotypes and partial genotypes, it quantifies whether a genetic entity
co-segregates with disease beyond chance, supporting pathogenicity classification.

## Technology Stack

- Python ≥ 3.12 (tomllib, improved type system, match statement)
- Pydantic v2 for all domain models
- pandas ≥ 2.0 for incidence/penetrance DataFrames
- typer + rich for CLI
- R (≥ 4.2) + segregatr via subprocess for FLB computation

## Package Structure

Source lives in `src/heredicalc/`. Tests in `tests/`. Docs in `docs/`.
Bootstrap data (CI5, RR tables, pedigrees) is in `_bootstrap/` during
development; moved to plugin `data/` directories before first release.

## Code Conventions

- Line length: 100 characters (ruff + black)
- All domain models: Pydantic v2, `from __future__ import annotations`
- All plugin interfaces: `typing.Protocol` (not ABCs)
- Data access in plugins: `importlib.resources` pattern via `_files(__package__)`
- No global singletons — registry passed via dependency injection
- No comments unless the WHY is non-obvious
- No docstrings beyond a single short line where needed

## Plugin System

Ten built-in plugin kinds (plain strings, not enums):
`pedigree_format`, `phenotype_model`, `incidence_source`, `trait_mapper`,
`hazard_model`, `penetrance_model`, `crhf_model`, `rr_model`,
`liability_assigner`, `flb_calculator`

New kinds: `registry.register_kind("new_kind")` — no core code changes needed.

## Key Terminology

- `genetic_entity`: replaces "gene" everywhere (covers gene sub-regions,
  epigenetic phenomena, polygenic risk scores)
- `trait`: raw source-specific phenotype code (e.g. "113" in CI5-IX)
- `phenotype`: canonical internal name (e.g. "BreastCancer")
- `age`: always int (years, 0–99), year granularity is sufficient

## Testing

```bash
pytest tests/ --tb=short
mkdocs build --strict
```

Done criterion for Phase 1: integration tests green — every validation case meets
its own `reference_flb` within its own `tolerance_pct`, as declared per case in
`tests/fixtures/validation_fixtures.json` (correct `victor` model) and
`tests/fixtures/validation_fixtures_cool3.json` (COOL3-compatible `victor_cool3`
model). The primary case `brca1_belman_latvia_ci5ix` is defined in
`validation_fixtures.json`. Read both values from the fixture; do not hardcode them.

## Git Workflow

Conventional Commits. Every `feat(scope):` commit is immediately followed
by a `docs(scope):` commit updating the relevant manual page.

## Bootstrap Teardown (after Phase 1 tests pass)

See plan Section 12. Move data from `_bootstrap/` to plugin `data/` dirs,
run full test suite, then `rm -rf _bootstrap/`.
