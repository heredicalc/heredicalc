 HerediCalc v4 — Greenfield Architecture Planning Session

 Your Role

 You are in Plan Mode in a fresh project directory. This directory contains a
 _bootstrap/ staging folder with data files (see below). Your task is to produce a
 comprehensive architecture and implementation plan for HerediCalc v4. Do NOT write
 any implementation code. Do NOT create any files other than your plan document.

 This plan is the primary reference document for the entire implementation.
 Favour completeness over brevity — a section that is too detailed is better than
 one that leaves implementation decisions open or ambiguous. Every interface,
 every data model, every algorithm, and every deployment detail should be specified
 precisely enough that a developer can implement it without revisiting you for
 clarification.

 ---
 Project Purpose

 HerediCalc computes the Full Likelihood Bayes (FLB) factor for Bayesian
 cosegregation analysis in hereditary cancer genetics. Given a family pedigree
 with known phenotypes and (partially) known genotypes, it asks: does this variant
 co-segregate with disease beyond chance?

 FLB = Π_i  P(observations_i | heterozygous carrier)
           / P(observations_i | non-carrier)
 A high FLB (e.g., > 10) supports pathogenicity classification of a genetic variant.

 The computation requires:
 1. Population cancer incidence data (CI5 registries, editions VIII–XII)
 2. Gene-specific relative risk (RR) tables by age, sex, phenotype
 3. Carrier allele frequencies (Cumulative Risk Haplotype Frequency, CRHF) per gene
 4. A pedigree file with family members, phenotypes, and age information
 5. A penetrance model that converts incidence + RR + CRHF into a MECE penetrance table
 6. The R package segregatr for the final FLB calculation

 ---
 Bootstrap Data in This Directory

 A _bootstrap/ directory is present with the following structure. It is a
 temporary staging area — gitignored and deleted after setup. Read all files
 in it to understand their formats before designing any interfaces. The formats
 differ significantly between CI5 editions and must inform the per-edition plugin designs.

 _bootstrap/
     ci5/
         edition_viii/      # CI5 Volume VIII — infer format from actual files
         edition_ix/        # CI5 Volume IX  — infer format from actual files
         edition_x/         # CI5 Volume X   — infer format from actual files
         edition_xi/        # CI5 Volume XI  — infer format from actual files
         edition_xii/       # CI5 Volume XII — infer format from actual files
     rr/
         BRCA1.csv          # Relative risk table, gene/sex/age/phenotype
         BRCA2.csv
     crhf/
         genes.csv          # CRHF values per gene
     pedigrees/
         Belman.ped         # Validation pedigree: Belman et al. 2020, Fig. 1 (BRCA1)
         *.ped              # Permutations with varied phenotype distributions
     validation_fixtures.json   # COOL3 reference FLB values — see format below

 The validation_fixtures.json file contains machine-readable COOL3 reference values
 for each pedigree. Claude Code must read this file and generate parametrized pytest
 integration tests from it — one test case per entry, no hardcoded FLB values in
 test code. When new pedigrees are added later, only this JSON file is updated.

 Required format:
 {
   "validation_cases": [
     {
       "id": "brca1_belman_latvia_ci5ix",
       "pedigree": "Belman.ped",
       "description": "Belman et al. 2020, Fig. 1 — primary COOL3 validation",
       "config": {
         "gene": "BRCA1",
         "population": "54280099",
         "incidence_source": "ci5_ix",
         "phenotype_model": "hbopc",
         "penetrance_model": "victor",
         "rr_model": "tabular",
         "crhf_model": "lookup",
         "allele_freq": 0.00075,
         "age_bands": [30, 40, 50, 60, 65, 70, 80]
       },
       "reference_flb": 19.47,
       "tolerance_pct": 6.0,
       "reference_source": "COOL3 v3 server, Latvia registry 54280099, 1998-2002",
       "computed_date": "2026-05-20"
     }
   ]
 }

 Long-Term Data Placement

 Once plugins are implemented, their associated data moves out of _bootstrap/
 and into the plugin package directory, accessed via importlib.resources:

 src/heredicalc/plugins/incidence_sources/ci5_viii/data/*.csv
 src/heredicalc/plugins/incidence_sources/ci5_ix/data/*.csv
 ...
 src/heredicalc/plugins/rr_models/tabular/data/*.csv
 src/heredicalc/plugins/crhf_models/lookup/data/*.csv

 The plan must specify how importlib.resources.files(__package__) / "data" is used
 to locate bundled data files at runtime. After the plugins are implemented and the
 data is in the correct plugin directories, _bootstrap/ is removed.

 ---
 Core Algorithm — VICTOR Competing-Risk Penetrance Model

 This algorithm has been validated against COOL3/VICTOR server output and must be
 implemented exactly as specified. Any deviation produces incorrect FLB values.

 Step 1: Carrier-Corrected Hazard Rates (Hardy-Weinberg derivation)

 For each disease j and age a, given population incidence λ_pop(j, a)
 and CRHF value q:

 D(j, a)     = 1 + 2·q·(RR_het(j, a) − 1)        # VICTOR correction denominator
 λ_nc(j, a)  = λ_pop(j, a) / D(j, a)              # non-carrier hazard
 λ_het(j, a) = RR_het(j, a) · λ_nc(j, a)          # heterozygous carrier hazard
 λ_hom(j, a) = RR_hom(j, a) · λ_nc(j, a)          # homozygous carrier hazard
 This guarantees λ_het / λ_nc = RR_het exactly.

 ⚠️  CRITICAL: Never use λ_het = RR · λ_pop · (1 − q). It is algebraically wrong.

 Step 2: All-Cause Survival Curve (per genotype g ∈ {nc, het, hom})

 λ_g_all(a) = Σ_j λ_g(j, a)
 S_g(a)     = exp(−Σ_{i=0}^{a} λ_g_all(i))
 S_g_prev   = [1, S_g(0), ..., S_g(98)]     # S_g(a−1) shifted, S_g(−1) = 1
 Step 3: Cause-Specific Cumulative Incidence Function (CIF)

 F_j_g(a) = Σ_{i=0}^{a} S_g_prev[i] · (1 − exp(−λ_g(j, i)))
 Step 4: MECE Penetrance Table

 One row per (sex, phenotype, age/band) — Mutually Exclusive, Collectively
 Exhaustive (MECE) liability classes consumed by segregatr.

 - Affected member, diagnosed in age band [a₀, a₁], disease j:
   penetrance_g = F_j_g(a₁) − F_j_g(a₀ − 1)         # BAND-SPECIFIC increment
 - Unaffected member, last observed at age a₁:
   penetrance_g = 1 − S_g(a₁)                         # cumulative all-cause

 ⚠️  CRITICAL: Disease rows must be band-specific CIF increments, NOT cumulative
    F_j_g(a₁). Cumulative values inflate het/nc ratios by up to 3× for older age
    bands, producing FLB errors of 40%+.

 Step 5: FLB via R/segregatr

 Penetrance matrix and pedigree structure passed to the R package segregatr via
 subprocess. R and segregatr must be installed on the system.

 ---
 Plugin Architecture Requirements

 Design Principle: Open, Extensible Registry

 The set of plugin kinds is not fixed. The registry must support registering new
 plugin kinds at runtime without modifying any core framework code. Plugin kinds are
 identified by a plain string registered at startup — not a closed Literal or Enum.
 Built-in kinds are registered by the framework itself; third-party packages and
 future milestones register additional kinds via entry points or explicit calls.

 Current Built-in Plugin Kinds

 The following eight kinds ship with v4. They are the starting point, not the
 complete set. New kinds will be added in future milestones.

 ┌────────────────────┬──────────────────────────────────────────────────────────────┐
 │        Kind        │                        Responsibility                        │
 ├────────────────────┼──────────────────────────────────────────────────────────────┤
 │ pedigree_format    │ Load/save pedigree files (COOL3 TSV, HerediCare CSV, ...)    │
 ├────────────────────┼──────────────────────────────────────────────────────────────┤
 │ phenotype_model    │ Map raw phenotype codes to canonical disease categories      │
 ├────────────────────┼──────────────────────────────────────────────────────────────┤
 │ incidence_source   │ Load population incidence tables (CI5 VIII–XII, Munich, ...) │
 ├────────────────────┼──────────────────────────────────────────────────────────────┤
 │ hazard_model       │ Convert raw incidence to yearly λ_pop(j, a) arrays           │
 ├────────────────────┼──────────────────────────────────────────────────────────────┤
 │ penetrance_model   │ Compute MECE penetrance table (VICTOR, spline, normal, ...)  │
 ├────────────────────┼──────────────────────────────────────────────────────────────┤
 │ crhf_model         │ Provide CRHF value q per gene/sex/age                        │
 ├────────────────────┼──────────────────────────────────────────────────────────────┤
 │ rr_model           │ Provide relative risks RR(j, a, sex, genotype) per gene      │
 ├────────────────────┼──────────────────────────────────────────────────────────────┤
 │ liability_assigner │ Map pedigree members to penetrance table row indices         │
 └────────────────────┴──────────────────────────────────────────────────────────────┘

 CI5 Incidence Sources — Per-Edition Plugins

 CI5 editions VIII through XII have significantly different file formats (column
 layouts, age group encodings, registry ID schemes, delimiter conventions). Do NOT
 attempt to unify them in a single adapter. Each edition is its own concrete plugin:

 - ci5_viii — implements incidence_source, reads CI5 VIII format
 - ci5_ix   — implements incidence_source, reads CI5 IX format
 - ci5_x    — implements incidence_source, reads CI5 X format
 - ci5_xi   — implements incidence_source, reads CI5 XI format
 - ci5_xii  — implements incidence_source, reads CI5 XII format

 All five share the same IncidenceSource Protocol and return identical output
 DataFrames. The format differences are entirely internal to each plugin. Each
 plugin's bundled data files live in its own data/ subdirectory.

 Before designing the IncidenceSource interface, read the actual files in
 _bootstrap/ci5/ to understand what columns are common across all editions.

 Plugin Dependency Declaration (Sub-Plugin Composition)

 Different penetrance models have different computational requirements:
 - VICTOR penetrance model needs rr_model + crhf_model
 - A spline-interpolation model may need neither
 - A normal-distribution model may need only population statistics

 Each plugin declares its sub-plugin dependencies in its metadata:

 class VictorPenetranceModel:
     meta = PluginMeta(
         name="victor",
         kind="penetrance_model",
         requires={
             "rr_model": None,     # None = accept any registered rr_model
             "crhf_model": None,   # None = accept any registered crhf_model
         },
     )

 The pipeline runner reads meta.requires, resolves sub-plugins from the registry
 using the active configuration, and injects them into the constructor. Penetrance
 models that do not declare requires receive no sub-plugins. This makes rr_model
 and crhf_model optional plugin kinds — present in the pipeline only when
 a penetrance model requests them.

 Registry/runner rules:
 - requires value of None → accept any registered plugin of that kind
 - requires value of "tabular" → require the specific plugin named "tabular"
 - Circular sub-plugin dependencies → detected at startup, hard error
 - Missing required sub-plugin → clear error before any computation begins

 Plugin Metadata

 Each plugin must declare:
 - name: str — unique within its kind
 - version: str — semantic version ("1.2.0")
 - kind: str — the registered kind name (plain string, not enum)
 - description: str
 - author: str
 - min_api_version: str — minimum framework API version required
 - max_api_version: str | None — upper bound (None = no upper bound)
 - requires: dict[str, str | None] — sub-plugin dependencies (kind → name or None)

 Plugin Interface Pattern

 - Python typing.Protocol for type-safe interface contracts (not ABC)
 - Constructor injection for sub-plugin dependencies declared in requires
 - Plugins stateless after construction (safe for concurrent batch processing)
 - Every public method: full type annotations + Sphinx RST docstring

 Plugin Discovery Sources

 Discovery runs in this priority order (later sources can override earlier ones
 for the same name+kind, subject to version resolution):

 1. Built-in — bundled in the framework package; always available, read-only
 2. pip-installed — third-party packages via importlib.metadata entry_points
 3. Copy-in directory — user drops plugin files/packages into a watched directory;
 auto-discovered on startup without any installation step
 4. Data-driven — PluginSpec records from database or YAML (Extension Point EP-2)

 Copy-In Directory

 The copy-in directory is the primary mechanism for users to extend HerediCalc
 without modifying the framework or running pip. It is:
 - Configurable (default: ~/.heredicalc/plugins/ on all platforms via platformdirs)
 - Scanned recursively on every startup
 - Each valid plugin module/package found there is registered automatically

 A plugin is valid if it contains a PluginMeta-bearing class at module level.
 Invalid files in the directory are logged as warnings and skipped.

 Plugin management CLI subcommands operate on this directory:
 - heredicalc plugins install <path-or-url> — copy into the copy-in directory
 - heredicalc plugins remove <name> [--kind <kind>] — remove from directory
 - heredicalc plugins update <name> <path-or-url> — replace in directory
 - heredicalc plugins list [--kind <kind>] [--source builtin|copyin|entrypoint]
 - heredicalc plugins validate <name> — check interface compliance + API compat

 Version Constraints in Config Files

 Run config files may pin or constrain plugin versions using pip-compatible syntax:

 penetrance_model: "victor>=1.0.0,<2.0.0"
 rr_model: "tabular~=1.2"          # compatible release: >=1.2, <2.0
 crhf_model: "lookup"               # no constraint: newest compatible
 incidence_source: "ci5_ix==1.0.0"  # exact pin

 The runner resolves each constraint against the registry at startup and raises
 PluginResolutionError with a clear message if no compatible version is found.

 ---
 Three Deployment Modes

 A single shared core library powers all three modes. No business logic in
 CLI, GUI, or web layers.

 Mode 1: CLI (implement first)

 - Framework: typer
 - Configuration: YAML or TOML config files; CLI flags override config values
 - Subcommands:
   - heredicalc run <pedigree> [options] — single pedigree FLB
   - heredicalc batch <directory> [options] — all pedigrees in directory
   - heredicalc plugins list [--kind <kind>] — list registered plugins
   - heredicalc plugins validate <name> — validate plugin compatibility
 - Batch: concurrent.futures.ProcessPoolExecutor, configurable --workers N
 - Progress: rich progress bar; --json-log for structured logging output
 - Output: JSON (default), CSV, TSV; one result row per pedigree in batch
 - Example config file:
 gene: BRCA1
 population: "54280099"        # Latvia 1998-2002
 incidence_source: ci5_ix
 phenotype_model: hbopc
 penetrance_model: victor
 rr_model: tabular
 crhf_model: lookup
 allele_freq: 0.00075
 age_bands: [30, 40, 50, 60, 65, 70, 80]

 Mode 2: Desktop GUI (implement second)

 - Framework: PyQt6; standalone packaging via PyInstaller
 - The GUI is a thin shell over core — zero business logic in the GUI layer
 - Two functional areas with tab-based layout from day one:
   a. Computation tab: pedigree file selector, parameter panel, run button,
 results display, export
   b. Management tab (placeholder in Phase 2, implemented in Phase 4):
       - Pedigree library: browse, open, tag, persist to local SQLite database
     - Model editor: guided forms to create/edit phenotype models, RR tables,
 CRHF values, incidence source configurations
     - Plugin manager: install (file picker → copy-in), remove, update, list with
 version info and source (builtin / copy-in / pip), view dependency graphs
 - Install as: pip install heredicalc[gui]

 Mode 3: Web Application (implement third)

 - Backend: FastAPI with async endpoints
 - API endpoints:
   - POST /api/flb — single pedigree, returns FLB synchronously
   - POST /api/batch — returns job ID
   - GET /api/batch/{job_id} — status + results
 - Background jobs: FastAPI.BackgroundTasks for v1; document Celery as upgrade path
 - Frontend: Streamlit for rapid v1 deployment (replaceable without API changes)
 - Two functional areas:
   a. Computation interface: web equivalent of CLI run/batch
   b. Management routes (HTTP 501 placeholder in Phase 3, implemented in Phase 4):
       - /manage/pedigrees — upload, browse, tag, search (PostgreSQL backend)
     - /manage/models — create/share phenotype models, RR datasets, CRHF tables
     - /manage/plugins — upload to copy-in dir, remove, update, list with
 version/source info, view dependency graphs, check API compatibility
 - Route namespace /manage/ reserved from the start
 - Install as: pip install heredicalc[web]

 ---
 Management Layer — Architecture Prerequisites

 The management layer is NOT part of Phases 1–3. However, the following structural
 decisions must be made now so it can be added in Phase 4 without breaking changes.

 Persistence Abstraction (Repository Pattern)

 Define abstract repository interfaces in core/repositories/ from day one:

 - PedigreeRepository — CRUD for pedigree records
 - ModelSpecRepository — CRUD for user-defined model specifications
 - PluginSpecRepository — CRUD for data-driven plugin specifications

 Phase 1 concrete implementations: FilesystemPedigreeRepository (file I/O, no DB).
 Phase 2: SQLitePedigreeRepository.
 Phase 3: PostgresPedigreeRepository.
 All three implement the same abstract interface — no consumer code changes when
 swapping implementations.

 Data-Driven Plugin Specifications

 Users will eventually create plugins (custom RR tables, phenotype models, CRHF
 values, incidence configurations) through guided UI forms, not by writing Python code.
 This means plugin specifications must be representable as structured data:

 - Define serializable PluginSpec Pydantic models for each plugin kind that is
 likely to be user-created: RRModelSpec, CRHFModelSpec, PhenotypeModelSpec,
 IncidenceSourceSpec
 - The plugin registry must be able to instantiate a plugin from a PluginSpec
 record (retrieved from DB or YAML) in addition to importable Python modules
 - Document this as: Extension Point EP-2: Data-Driven Plugin Instantiation

 Serializable Domain Models

 All core domain objects must be Pydantic models from the start:
 Pedigree, PedigreeMember, PenetranceTable, PipelineConfig, PluginMeta,
 PluginSpec. Required for repository storage and future client-server transmission.

 UI Layer Structure

 - GUI: QTabWidget or QStackedWidget from Phase 2, with a management tab slot
 visible but disabled (or labelled "Coming soon") until Phase 4
 - Web: /manage/ route namespace returns HTTP 501 from Phase 3 onwards

 ---
 Future Extension Points (document — do NOT implement)

 List all of these in the architecture docs. For each, describe where the hook
 lives and what would NOT change when it is implemented.

 - EP-1: Additional Plugin Kinds — new kinds registered at runtime, no core changes
 - EP-2: Data-Driven Plugin Instantiation — plugins from DB records or YAML specs
 - EP-3: Async Core — mark where async def / await would be introduced
 - EP-4: Distributed Batch — batch abstraction with pluggable Dask/Ray backends
 - EP-5: Client-Server — REST API backend + thin remote client
 - EP-6: Cluster Computing — HPC job submission (SLURM) as a batch backend
 - EP-7: Multi-User Web — authentication + per-user pedigree/model namespaces

 ---
 Development Standards

 Language

 All code, comments, docstrings, commit messages, and documentation: English only.
 No German in any source file.

 Type Annotations

 - from __future__ import annotations in every module
 - Full annotations on all public functions and class attributes
 - py.typed marker file to declare the package as typed

 Docstring Format — Sphinx RST

 All public classes, methods, and functions require Sphinx RST docstrings:

 def compute_penetrance(
     self,
     hazards: pd.DataFrame,
     phenotype_model: PhenotypeModel,
 ) -> pd.DataFrame:
     """Compute the MECE penetrance table from yearly hazard rates.

     Implements the VICTOR competing-risk algorithm. Output rows are
     Mutually Exclusive and Collectively Exhaustive (MECE) liability classes
     for use with the segregatr R package.

     :param hazards: DataFrame with columns sex, phenotype, age, hazard.
         One row per (sex, phenotype, age), ages 0..99.
     :type hazards: pd.DataFrame
     :param phenotype_model: Active phenotype model; determines which
         canonical phenotype labels appear in the output.
     :type phenotype_model: PhenotypeModel
     :return: MECE penetrance table with columns age_start, age_end, sex,
         phenotype, penetrance_nc, penetrance_het, penetrance_hom.
     :rtype: pd.DataFrame
     :raises ValueError: If hazards is missing required columns.
     """

 Private methods (_name) may omit docstrings unless the logic is non-obvious.

 Code Quality

 - ruff check src/ — enforced, no exceptions
 - black src/ — 100-char line length
 - No comments explaining WHAT the code does; only WHY when non-obvious
 - No unused imports, dead code, or feature flags

 Testing

 - pytest + pytest-cov; directories tests/unit/ and tests/integration/
 - Mandatory integration test: parametrized from _bootstrap/validation_fixtures.json.
 Each entry in validation_cases becomes one test. Do NOT hardcode FLB values in
 test code. The Belman case (Latvia 54280099, BRCA1, CI5-IX) must pass within
 ±6% of its reference_flb.
 - Mandatory unit test: VICTOR formula invariant — for any (RR, q, λ_pop),
 verify λ_het / λ_nc == RR_het to floating-point precision
 - Mandatory unit test: plugin registry raises on circular sub-plugin dependencies
 - Target coverage: ≥80% line coverage on core/ and plugins/
 - Test fixtures (pedigrees, reference values) live in tests/fixtures/
 - mkdocs build --strict must pass as part of the standard test run (add as
 a pytest fixture or a separate tox/make target that CI always executes)

 Documentation

 Documentation is developed in parallel with the code, not after the fact.
 This is a hard requirement with the same status as passing tests:

 - Every feat(scope): commit must be immediately followed by a docs(scope):
 commit updating the relevant manual page. No feature is complete until its
 documentation is written.
 - mkdocs build --strict (zero warnings, zero broken links) must pass at all
 times — treat it identically to a failing test. The CI check list in Phase 1
 must include this.
 - New plugin kind added → docs/plugins/plugin-kinds.md updated in same session.
 - New CLI subcommand added → docs/user-guide/cli.md updated immediately.
 - New config key added → docs/user-guide/config-file.md updated immediately.
 - New extension point documented → docs/plugins/writing-plugins.md updated.

 Tool: Material for MkDocs (mkdocs-material + mkdocstrings[python])
 - mkdocs.yml configured and mkdocs serve succeeds from the very first commit
 - API reference auto-generated from Sphinx RST docstrings via mkdocstrings
 - Docs structure:
 docs/
   index.md                      # overview + quick-start
   user-guide/
     cli.md                      # full CLI reference (auto-updated)
     config-file.md              # all config keys with types and defaults
     gui.md                      # placeholder Phase 2
     web.md                      # placeholder Phase 3
   algorithms/
     competing-risk-model.md     # VICTOR mathematics
     flb-computation.md          # segregatr integration
   plugins/
     writing-plugins.md          # how to create a plugin
     plugin-kinds.md             # interface spec per kind
     plugin-dependencies.md      # requires declaration + injection
     copy-in-system.md           # how copy-in discovery works
     version-constraints.md      # constraint syntax in config files
   management/
     pedigree-library.md         # placeholder Phase 4
     model-editor.md             # placeholder Phase 4
   api/                          # auto-generated from docstrings

 Git Workflow

 - git init is the absolute first action in the project directory
 - .gitignore created immediately after — must include _bootstrap/
 - Conventional Commits strictly: feat, fix, refactor, docs, test,
 chore with scope in parentheses
 - Commit after each logical unit of work; docs() commits follow feat() commits
 immediately, not at end of session
 - Subject line: imperative mood, ≤72 characters, readable in git log --oneline
 - Branch strategy: main (always passing), feature/<component>

 ---
 What Your Plan Must Cover

 1. Technology Stack Decisions

 Table of every major library with version constraint and one-sentence justification.
 Include: Python version, data library (pandas vs polars), CLI, GUI, web framework,
 ORM/DB, importlib.resources usage, doc tool, test runner, linter, formatter.

 2. Directory and Package Structure

 Full directory tree from project root. Show:
 - src/heredicalc/core/, src/heredicalc/plugins/ with all plugin subdirectories
 - Each CI5 edition plugin directory with its data/ subdirectory
 - src/heredicalc/apps/cli/, apps/gui/, apps/web/
 - tests/unit/, tests/integration/, tests/fixtures/
 - docs/, mkdocs.yml, pyproject.toml, CLAUDE.md, py.typed
 - _bootstrap/ (gitignored, temporary)

 3. Core Domain Models

 Pydantic class stubs (field names + types, no method implementations) for:
 Pedigree, PedigreeMember, PenetranceTable, PipelineConfig,
 PluginMeta, PluginSpec, HazardArray (or equivalent).

 4. Repository Interface Specifications

 Abstract Protocol stubs for PedigreeRepository, ModelSpecRepository,
 PluginSpecRepository. List method signatures. Note which concrete
 implementation ships in each phase.

 5. Plugin Registry Design

 - Internal data structures (what is stored per registered plugin)
 - Kind registration mechanism (how a new kind string is added at runtime)
 - Version resolution algorithm including pip-compatible constraint syntax (pseudocode)
 - Sub-plugin dependency injection algorithm (pseudocode)
 - Circular dependency detection algorithm
 - Discovery sequence: builtin → entry_points → copy-in directory → data-driven
 - Copy-in directory: default path via platformdirs, scan algorithm, error handling
 for invalid files, how plugins install/remove/update CLI commands interact with it
 - PluginResolutionError specification: what information it carries, when it is raised

 6. Plugin Interface Specifications

 For each of the 8 built-in plugin kinds: Protocol method signatures with parameter
 types, return types, and one-sentence docstring contract. Mark which kinds are
 sub-plugins (consumed by other plugins) vs. top-level pipeline components.

 7. CI5 Edition Adapter Design

 For each edition VIII–XII (after reading the actual files in _bootstrap/ci5/):
 describe the file format, identify common vs. edition-specific columns, specify
 how the adapter normalizes to the common IncidenceSource output schema.
 Highlight any format quirks that require special handling.

 8. Pipeline Data Flow

 Ordered step-by-step from (pedigree_file, config) → float FLB. Name the plugin
 at each step, its inputs, its outputs, and where sub-plugins are injected. Show
 that all three deployment modes call the same pipeline function identically.

 9. Development Phases and Milestones

 Phase 1 — Core + CLI:
 Plugin registry (extensible kinds, sub-plugin injection), all 8 plugin Protocols,
 VICTOR penetrance model, CI5 adapters for all five editions, segregatr integration,
 CLI with run/batch/plugins subcommands, filesystem repository stubs,
 mkdocs skeleton, integration test passing, CLAUDE.md.

 Phase 2 — Desktop GUI:
 PyQt6 computation view, QTabWidget with placeholder management tab,
 PyInstaller packaging, SQLite repository implementations.

 Phase 3 — Web Application:
 FastAPI backend, Streamlit frontend, Docker image, PostgreSQL repository
 implementations, /manage/ namespace reserved (HTTP 501).

 Phase 4 — Management Layer (future milestone, not planned in detail):
 Pedigree library UI, model editor with guided forms, data-driven plugin
 instantiation from DB-stored PluginSpec records.

 For Phases 1–3: list features, tests, and docs pages per phase.

 10. Git Bootstrap Sequence

 First 18–20 commits in order with exact commit messages and one-sentence
 description of what each commit contains. This is the intended initial history —
 make it clean, logical, and representative.

 11. Extension Points Documentation

 For each of EP-1 through EP-7: the file/class where the hook lives, what the
 interface boundary looks like, and what would NOT need to change when implemented.

 12. Bootstrap Teardown Instructions

 After all plugins are implemented and data is moved to plugin data/ directories,
 what exactly must be done to remove _bootstrap/? Specify the steps and any
 verification commands (e.g., ruff, pytest) to confirm nothing broke.

 13. Open Questions and Assumptions

 Tag with [ASSUMPTION] or [NEEDS INPUT]. Flag any format ambiguity found when
 reading the _bootstrap/ files.

 ---
 Constraints

 - No auth system, no cloud storage, no telemetry unless explicitly asked
 - No abstract base classes where a Protocol suffices
 - No error handling for scenarios that cannot happen (trust internal APIs)
 - Validate only at system boundaries: file parsing, config loading, network I/O
 - GUI and web layers: zero domain logic
 - Management layer: design the seams now; implement only in Phase 4
 - _bootstrap/ is temporary; the plan must explicitly describe how to remove it
