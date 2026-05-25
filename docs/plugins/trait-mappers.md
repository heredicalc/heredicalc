# Trait Mappers

A trait mapper translates between two different code systems:

1. **`map_trait(code)`** — raw CI5 cancer registry codes (e.g. `"113"`) → canonical
   phenotype names (e.g. `"BreastCancer"`) or `None` for untracked traits
2. **`map_affection(status)`** — pedigree affection status strings (e.g. `"BrCa"`) →
   canonical phenotype names or `None` for unaffected/unknown

Each CI5 edition uses different numeric codes for the same cancer sites. HerediCalc
therefore provides **one standalone mapper per edition × phenotype model combination**.
There is no shared cross-edition mapper.

---

## Built-In Mappers (HBOPC)

All five built-in mappers cover the HBOPC phenotype model
(Hereditary Breast, Ovarian, and Pancreatic Cancer).

### ICD Code Mapping

| Plugin | Incidence source | Breast Cancer | Ovarian Cancer | Pancreatic Cancer |
|--------|-----------------|:-------------:|:--------------:|:-----------------:|
| `ci5_viii_hbopc` | `ci5_viii` | `"116"` | `"136"` | `"071"` |
| `ci5_ix_hbopc` | `ci5_ix` | `"113"` | `"133"` | `"070"` |
| `ci5_x_hbopc` | `ci5_x` | `"113"` | `"133"` | `"070"` |
| `ci5_xi_hbopc` | `ci5_xi` | `"111"` | `"130"` | `"065"` |
| `ci5_xii_hbopc` | `ci5_xii` | `"159"` | `"178"` | `"080"` |

All other CI5 codes map to `None` — they are treated as competing-risk events
(`OtherTrait`) by the hazard and penetrance models.

### Affection Code Mapping (all editions identical)

| Pedigree code | Canonical phenotype |
|---------------|-------------------|
| `BrCa` | `BreastCancer` |
| `OvCa` | `OvarianCancer` |
| `PanCa` | `PancreaticCancer` |
| `unaff` | `None` (unaffected) |
| `.` | `None` (unknown / not assessed) |

---

## Compatibility Enforcement

Each mapper declares `compatible_with` in its metadata:

```python
compatible_with={
    "incidence_source": ["ci5_ix"],
    "phenotype_model": ["hbopc"],
}
```

The registry raises a `PluginCompatibilityError` at startup if the configured
`trait_mapper` does not match the active `incidence_source`. For example,
using `ci5_ix_hbopc` with `incidence_source: ci5_x` is caught immediately.

The `heredicalc init` command automatically derives the correct mapper name from
the chosen incidence source: `{incidence_source}_hbopc`.

---

## Configuration

```yaml
plugins:
  incidence_source: ci5_ix
  trait_mapper: ci5_ix_hbopc   # must match incidence_source edition
```

| `incidence_source` | `trait_mapper` |
|--------------------|----------------|
| `ci5_viii` | `ci5_viii_hbopc` |
| `ci5_ix` | `ci5_ix_hbopc` |
| `ci5_x` | `ci5_x_hbopc` |
| `ci5_xi` | `ci5_xi_hbopc` |
| `ci5_xii` | `ci5_xii_hbopc` |

---

## Adding a New Mapper

When a new CI5 edition (e.g. CI5-XIII) becomes available, create a new standalone
plugin directory — no existing code needs to be modified.

**1. Create the directory structure:**

```
src/heredicalc/plugins/trait_mappers/ci5_xiii_hbopc/
    __init__.py
    plugin.py
    data/
        mappings.yml
```

**2. Write `plugin.py`** (copy from an existing mapper, update name and `compatible_with`):

```python
class CI5XIIIHBOPCTraitMapper:
    meta = PluginMeta(
        name="ci5_xiii_hbopc",
        version="1.0.0",
        kind="trait_mapper",
        description="Maps CI5-XIII trait codes to HBOPC canonical phenotypes",
        author="HerediCalc",
        min_api_version="1.0.0",
        compatible_with={
            "incidence_source": ["ci5_xiii"],
            "phenotype_model": ["hbopc"],
        },
    )
    # ... (identical __init__, map_trait, map_affection implementation)
```

**3. Write `data/mappings.yml`** with the correct CI5-XIII codes:

```yaml
trait_mappings:
  "<breast_code>": "BreastCancer"
  "<ovarian_code>": "OvarianCancer"
  "<pancreatic_code>": "PancreaticCancer"

affection_mappings:
  "BrCa":  "BreastCancer"
  "OvCa":  "OvarianCancer"
  "PanCa": "PancreaticCancer"
  "unaff": null
  ".":     null
```

**4. Register in `src/heredicalc/plugins/__init__.py`:**

```python
from heredicalc.plugins.trait_mappers.ci5_xiii_hbopc.plugin import CI5XIIIHBOPCTraitMapper
# add CI5XIIIHBOPCTraitMapper to _BUILTIN_PLUGINS list
```
