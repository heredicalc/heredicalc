# Configuration File

HerediCalc is configured via a YAML file (default: `heredicalc.yml`). Use
`heredicalc init` to generate a starter file interactively, or write one manually.

---

## Full Schema

```yaml
computation:
  genetic_entity: BRCA1       # required — gene or genetic entity name
  allele_freq: 0.0001          # required — population carrier frequency

plugins:
  incidence_source: ci5_ix     # required — which CI5 edition to use
  phenotype_model: hbopc        # required — canonical disease categories
  trait_mapper: ci5_ix_hbopc   # required — must match incidence_source edition
  hazard_model: annual_rate    # optional — default: annual_rate
  penetrance_model: victor     # optional — default: victor
  liability_assigner: victor_standard   # optional
  flb_calculator: segregatr    # optional
  pedigree_format: cool3_tsv   # optional — auto-detected if omitted

  params:
    population: "Latvia"        # required — population name or CI5 registry ID
    age_bands: [30, 40, 50, 60, 65, 70, 80]   # optional — default shown
    rr_model: tabular           # optional
    crhf_model: lookup          # optional
```

---

## Fields

### `computation`

| Field | Type | Description |
|-------|------|-------------|
| `genetic_entity` | string | Genetic entity name, e.g. `BRCA1`, `BRCA2`, `PALB2` |
| `allele_freq` | float | Population allele frequency (heterozygous carrier rate) |

### `plugins`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `incidence_source` | string | — | CI5 edition: `ci5_viii`, `ci5_ix`, `ci5_x`, `ci5_xi`, `ci5_xii` |
| `phenotype_model` | string | — | `hbopc` (breast, ovarian, pancreatic cancer) |
| `trait_mapper` | string | — | Must match incidence_source: e.g. `ci5_ix_hbopc` for `ci5_ix` |
| `hazard_model` | string | `annual_rate` | `annual_rate` (correct) or `annual_rate_cool3` (COOL3-compatible) |
| `penetrance_model` | string | `victor` | `victor` (correct) or `victor_cool3` (COOL3-compatible) |
| `liability_assigner` | string | `victor_standard` | Maps pedigree members to penetrance liability classes |
| `flb_calculator` | string | `segregatr` | Computes FLB via R subprocess |
| `pedigree_format` | string | auto | `cool3_tsv` — usually auto-detected |

### `plugins.params`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `population` | string | — | Population name substring or exact CI5 registry ID |
| `age_bands` | list[int] | `[30,40,50,60,65,70,80]` | Band boundaries in years; first band starts at 0, last ends at 99 |
| `rr_model` | string | `tabular` | Relative risk model sub-plugin |
| `crhf_model` | string | `lookup` | Cancer-rate-in-heterozygotes frequency sub-plugin |

---

## Minimal Example (BRCA1, Latvia, CI5-IX)

```yaml
computation:
  genetic_entity: BRCA1
  allele_freq: 0.0001

plugins:
  incidence_source: ci5_ix
  phenotype_model: hbopc
  trait_mapper: ci5_ix_hbopc
  params:
    population: "Latvia"
```

---

## COOL3-Compatible Mode

To replicate COOL3 v3 results, switch the hazard and penetrance model:

```yaml
plugins:
  incidence_source: ci5_ix
  phenotype_model: hbopc
  trait_mapper: ci5_ix_hbopc
  hazard_model: annual_rate_cool3
  penetrance_model: victor_cool3
  params:
    population: "Latvia"
```

When `penetrance_model: victor_cool3` is set without an explicit `hazard_model`,
HerediCalc automatically selects `annual_rate_cool3` (plugin-specific default).
Specifying `hazard_model` explicitly always takes precedence.

---

## CLI Overrides

Any `plugins` or `computation` field can be overridden at the command line.
CLI values always take precedence over the config file:

```bash
heredicalc run pedigree.ped --config heredicalc.yml --population "Finland, Tampere"
```

---

## Trait Mapper ↔ Incidence Source Pairing

The trait mapper must be compatible with the chosen incidence source.
Mismatches are caught at startup with a `PluginCompatibilityError`.

| `incidence_source` | `trait_mapper` |
|--------------------|----------------|
| `ci5_viii` | `ci5_viii_hbopc` |
| `ci5_ix` | `ci5_ix_hbopc` |
| `ci5_x` | `ci5_x_hbopc` |
| `ci5_xi` | `ci5_xi_hbopc` |
| `ci5_xii` | `ci5_xii_hbopc` |
