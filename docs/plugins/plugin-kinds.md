# Plugin Kinds

HerediCalc v4 ships ten built-in plugin kinds. Each kind is identified by a
plain string registered at startup. Third-party packages may add new kinds at
runtime by calling `registry.register_kind("new_kind")` — no core-code changes
required.

All plugin interfaces are defined as `typing.Protocol` in
`heredicalc.plugins.protocols`.

---

## Top-level pipeline plugins

### `pedigree_format`

Reads and writes pedigree files. Built-in: **cool3_tsv**.

| Method | Contract |
|--------|---------|
| `load(path)` | Parse file → `Pedigree`; raise `ValueError` on format errors |
| `save(pedigree, path)` | Serialise to file |
| `supports(path)` | Return True if the file can be parsed by this plugin |

### `phenotype_model`

Maps raw affection codes to canonical disease categories. Built-in: **hbopc**.

| Method | Contract |
|--------|---------|
| `canonical_phenotypes()` | Ordered list of tracked canonical phenotype names |
| `map_raw_affection(raw)` | Raw pedigree code → canonical name or None |

The optional `ICDMappablePhenotypeModel` extension adds `map_icd(icd_code)`.

### `incidence_source`

Loads population cancer incidence tables. Built-ins: **ci5_viii**, **ci5_ix**,
**ci5_x**, **ci5_xi**, **ci5_xii**.

| Method | Contract |
|--------|---------|
| `list_sources()` | All available registries as `SourceInfo` list |
| `find_source_id(identifier)` | Resolve name substring or exact ID |
| `load(source_id)` | Return `ValidatedIncidenceFrame` |
| `get_trait_info(trait_code)` | Return `TraitInfo` or raise `KeyError` |

### `trait_mapper`

Maps CI5 trait codes and pedigree affection codes to canonical phenotype names.
Built-in: **ci5_hbopc**.

| Method | Contract |
|--------|---------|
| `map_trait(trait_code)` | CI5 code → canonical name or None (competing risk) |
| `map_affection(raw)` | Pedigree code → canonical name or None |

### `hazard_model`

Converts raw incidence to yearly hazard rates. Built-in: **annual_rate**
(rate = cases / person_years / band_width). Unmapped traits aggregate as
`"OtherTrait"` (RR=1 in VICTOR).

| Method | Contract |
|--------|---------|
| `compute_hazards(incidence, trait_mapper, params)` | Return `ValidatedHazardFrame` |

### `penetrance_model`

Computes MECE penetrance output from hazard rates. Built-in: **victor**.
Declares `requires = {"rr_model": None, "crhf_model": None}`.

| Method | Contract |
|--------|---------|
| `compute(hazards, phenotype_model, params)` | Opaque output; structure defined by plugin pair |

### `liability_assigner`

Maps pedigree members to penetrance-table liability class indices.
Built-in: **victor_standard**.

| Method | Contract |
|--------|---------|
| `assign(member, penetrance_output, phenotype_model, params)` | Zero-based class index |

### `flb_calculator`

Computes the FLB value. Built-in: **segregatr** (R subprocess).

| Method | Contract |
|--------|---------|
| `compute(pedigree, penetrance_output, liability_map, allele_freq, params)` | FLB float |

---

## Sub-plugins (consumed by `penetrance_model`)

### `rr_model`

Provides relative risks per gene/sex/age/phenotype/genotype.
Built-in: **tabular** (age-band CSV lookup). Returns 1.0 for unknown
combinations.

### `crhf_model`

Provides the CRHF value *q* per genetic entity. Built-in: **lookup**
(single value per gene from `genes.csv`).
