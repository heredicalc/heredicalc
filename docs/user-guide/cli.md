# CLI Reference

## R Dependency Setup

HerediCalc requires R ≥ 4.2 with the `segregatr` and `kinship2` packages.

```r
install.packages("kinship2")
install.packages("segregatr")
```

---

## `heredicalc run`

Compute the FLB factor for a single pedigree file.

```
heredicalc run [OPTIONS] PEDIGREE
```

| Argument / Option | Type | Description |
|-------------------|------|-------------|
| `PEDIGREE` | path | Path to the pedigree file (required) |
| `--config`, `-c` | path | YAML configuration file (see [Configuration](config-file.md)) |
| `--genetic-entity` | str | Genetic entity, e.g. `BRCA1` |
| `--allele-freq` | float | Population allele frequency, e.g. `0.0001` |
| `--population` | str | Population name or CI5 registry ID |
| `--incidence-source` | str | Incidence source plugin, e.g. `ci5_ix` |
| `--phenotype-model` | str | Phenotype model plugin, e.g. `hbopc` |
| `--trait-mapper` | str | Trait mapper plugin, e.g. `ci5_ix_hbopc` |
| `--penetrance-model` | str | Penetrance model plugin, e.g. `victor` |
| `--hazard-model` | str | Hazard model plugin, e.g. `annual_rate` |
| `--format` | `text`\|`json` | Output format (default: `text`) |
| `--verbose`, `-v` | flag | Enable INFO-level logging |

CLI options override any values from `--config`. Options not supplied fall back to
config-file values; required values not present in either will raise an error.

**Examples:**

```bash
# Minimal — config file provides everything
heredicalc run pedigree.ped --config heredicalc.yml

# Override population at the command line
heredicalc run pedigree.ped --config heredicalc.yml --population "Finland, Tampere"

# Fully explicit — no config file needed
heredicalc run pedigree.ped \
  --genetic-entity BRCA1 \
  --allele-freq 0.0001 \
  --population "Latvia" \
  --incidence-source ci5_ix \
  --phenotype-model hbopc \
  --trait-mapper ci5_ix_hbopc \
  --penetrance-model victor

# COOL3-compatible — hazard-model is automatically set to annual_rate_cool3
heredicalc run pedigree.ped \
  --genetic-entity BRCA1 \
  --allele-freq 0.0001 \
  --population "Latvia" \
  --incidence-source ci5_ix \
  --phenotype-model hbopc \
  --trait-mapper ci5_ix_hbopc \
  --penetrance-model victor_cool3

# JSON output (suitable for piping)
heredicalc run pedigree.ped --config heredicalc.yml --format json
```

---

## `heredicalc batch`

Compute FLB for all pedigree files in a directory in parallel.

```
heredicalc batch [OPTIONS] DIRECTORY
```

| Argument / Option | Type | Description |
|-------------------|------|-------------|
| `DIRECTORY` | path | Directory containing pedigree files (required) |
| `--config`, `-c` | path | YAML configuration file |
| `--pattern` | str | File glob pattern (default: `*.ped`) |
| `--workers`, `-j` | int | Number of parallel worker processes (default: `4`) |
| `--format` | `text`\|`json` | Output format (default: `json`) |

**Examples:**

```bash
# Process all .ped files in a directory
heredicalc batch ./pedigrees/ --config heredicalc.yml

# Limit parallelism, output as table
heredicalc batch ./pedigrees/ --config heredicalc.yml --workers 2 --format text

# Custom file pattern
heredicalc batch ./pedigrees/ --config heredicalc.yml --pattern "Belman*.ped"
```

JSON output is an array of objects: `{"pedigree": "name.ped", "flb": 19.47, "error": null}`.
Failed pedigrees are included with `flb: null` and the error message.

---

## `heredicalc add config`

Interactively generate a `heredicalc.yml` configuration file.

```
heredicalc add config [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--output`, `-o` | path | Pre-fill the output path prompt (optional) |

Prompts for genetic entity, allele frequency, incidence source, population, and age
bands. The **last prompt** asks for the output file path:

- Default: `heredicalc.yml` (or the value of `--output` if supplied)
- Enter a custom path to write there
- Leave empty to print the YAML to stdout

The trait mapper is automatically derived from the incidence source
(e.g. `ci5_ix` → `ci5_ix_hbopc`). If the output file already exists, a
confirmation prompt is shown before overwriting.

```bash
# Interactive — last prompt asks for filename (default: heredicalc.yml)
heredicalc add config

# Pre-fill the filename prompt via -o
heredicalc add config -o configs/brca1_latvia.yml

# Print to stdout (enter empty string at the filename prompt)
heredicalc add config
# Output file [...]: <Enter>
```

!!! note "Deprecated alias"
    `heredicalc init` still works but prints a deprecation warning.
    Use `heredicalc add config` instead.

---

## `heredicalc add trait`

Add a new user-defined genetic entity (RR table + CRHF value + metadata).

```
heredicalc add trait [OPTIONS] [NAME]
```

| Argument / Option | Type | Description |
|-------------------|------|-------------|
| `NAME` | str | Trait name, e.g. `BRCA2` (prompted if omitted) |
| `--crhf` | float | CRHF value (prompted if omitted) |
| `--kind` | str | Trait kind (default: `gene`; see kinds below) |
| `--rr-file` | path | Import RR CSV directly; omit to generate a template |
| `--meta` | str | Free metadata as `key=value` (repeatable) |

**Trait kinds:** `gene`, `chromosomal_anomaly`, `epigenetic`, `polygenic_score`, `other`

If `--rr-file` is omitted, a template CSV is written to the user data directory and
the command exits with instructions. Fill in the RR values and re-run with `--rr-file`.

User data is stored in:

- **macOS:** `~/Library/Application Support/heredicalc/traits/`
- **Linux:** `~/.local/share/heredicalc/traits/`

```bash
# Step 1: generate template (no --rr-file)
heredicalc add trait BRCA2 --crhf 0.0013

# Step 2: fill in template, then import
heredicalc add trait BRCA2 --crhf 0.0013 --rr-file BRCA2_rr.csv \
  --meta "locus=13q12.3" --meta "omim_nr=600185"
```

---

## `heredicalc clone trait`

Clone an existing trait (built-in or user-defined) as the basis for a new one.

```
heredicalc clone trait [OPTIONS] SOURCE TARGET
```

| Argument / Option | Type | Description |
|-------------------|------|-------------|
| `SOURCE` | str | Source trait name (built-in or user) |
| `TARGET` | str | New trait name |
| `--crhf` | float | Override CRHF value for the new trait |

Built-in data is never modified — the clone always lands in the user data directory.

```bash
# Clone BRCA1 as basis for BRCA2, then edit
heredicalc clone trait BRCA1 BRCA2 --crhf 0.0013
heredicalc edit trait BRCA2 --rr-file BRCA2_rr.csv
```

---

## `heredicalc edit trait`

Edit a user-defined trait.

```
heredicalc edit trait [OPTIONS] NAME
```

| Argument / Option | Type | Description |
|-------------------|------|-------------|
| `NAME` | str | Trait name to edit |
| `--rr-file` | path | Replace the RR table from this file |
| `--meta` | str | Replace metadata key=value (repeatable) |

If `NAME` is a built-in trait, an interactive prompt asks whether to clone it
to the user directory first.

```bash
heredicalc edit trait BRCA2
heredicalc edit trait BRCA2 --rr-file updated_brca2.csv
```

---

## `heredicalc remove trait`

Remove a user-defined trait.

```
heredicalc remove trait [OPTIONS] NAME
```

| Option | Type | Description |
|--------|------|-------------|
| `--yes`, `-y` | flag | Skip confirmation prompt |

Built-in traits cannot be removed. Removes the manifest entry and the user RR CSV.

```bash
heredicalc remove trait BRCA2
heredicalc remove trait BRCA2 --yes
```

---

## `heredicalc plugins list`

List all registered plugins.

```
heredicalc plugins list [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--kind`, `-k` | str | Filter by plugin kind (e.g. `trait_mapper`, `hazard_model`) |
| `--source` | str | Filter by source: `builtin`, `copyin`, `entrypoint` |

**Examples:**

```bash
# All plugins
heredicalc plugins list

# Only trait mappers
heredicalc plugins list --kind trait_mapper

# Only built-in plugins
heredicalc plugins list --source builtin
```

---

## `heredicalc plugins validate`

Validate a plugin's interface compliance and API version compatibility.

```
heredicalc plugins validate NAME
```

Exits with code 0 if the plugin is found and compliant, code 1 otherwise.

```bash
heredicalc plugins validate ci5_ix_hbopc
# ✓ trait_mapper/ci5_ix_hbopc v1.0.0 (source=builtin)
```
