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

## `heredicalc init`

Interactively generate a `heredicalc.yml` configuration file.

```
heredicalc init [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--output`, `-o` | path | Output file path (default: `heredicalc.yml`) |

Prompts for genetic entity, allele frequency, incidence source, population, and age
bands, then writes the config file. The trait mapper is automatically derived from
the chosen incidence source (e.g. `ci5_ix` → `ci5_ix_hbopc`). If the output file
already exists, a confirmation prompt is shown before overwriting.

```bash
# Write to default heredicalc.yml
heredicalc init

# Write to a custom path
heredicalc init --output configs/brca1_latvia.yml
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
