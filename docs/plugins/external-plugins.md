# External Plugins

HerediCalc's plugin system is designed so that researchers can add their own
phenotype models, trait mappers, incidence sources, and other plugin types
**without modifying the HerediCalc package itself**.  Research-specific plugins
live entirely outside the HerediCalc repository and are never pushed to it.

---

## Why External Plugins?

Built-in plugins (bundled in `src/heredicalc/plugins/`) are general-purpose and
suitable for publication in the main repository.  Study-specific plugins — for
example, a phenotype model for triple-negative breast cancer or an incidence
source from a regional cancer registry — are research artefacts that belong in
the analysis project, not in the tool.

---

## Discovery Mechanism

`PluginRegistry.discover_all()` searches for external plugins in two places:

1. **User plugin directory** (always checked):
   - macOS: `~/Library/Application Support/heredicalc/plugins/`
   - Linux: `~/.local/share/heredicalc/plugins/`

2. **`HEREDICALC_PLUGIN_PATH` environment variable** (optional):
   Any number of additional directories, colon-separated (POSIX) or
   semicolon-separated (Windows):
   ```bash
   export HEREDICALC_PLUGIN_PATH=~/my_project/plugins
   # or multiple paths:
   export HEREDICALC_PLUGIN_PATH=~/project_a/plugins:~/project_b/plugins
   ```

Within each directory, HerediCalc recursively searches for files named
**`plugin.py`** and imports them.

---

## Writing an External Plugin File

A `plugin.py` file must expose one of:

| Attribute | Type | When to use |
|-----------|------|-------------|
| `plugin_class` | a class | one plugin per file |
| `plugin_classes` | list of classes | multiple plugins per file |

Each class must have a class-level `meta: PluginMeta` attribute and implement
the appropriate Protocol for its kind (see [Plugin Kinds](plugin-kinds.md)).

### Minimal example — single-phenotype model

```python
# ~/my_project/plugins/phenotype_models/bc_only/plugin.py
from heredicalc.core.models.plugin import PluginMeta

class BCOnlyPhenotypeModel:
    meta = PluginMeta(
        name="bc_only",
        version="1.0.0",
        kind="phenotype_model",
        description="Tracks BreastCancer only (TNBC counted as BrCa subtype)",
        author="My Research Group",
        min_api_version="1.0.0",
    )

    def canonical_phenotypes(self) -> list[str]:
        return ["BreastCancer"]

    def map_raw_affection(self, raw: str) -> str | None:
        return {"BrCa": "BreastCancer", "TNBC": "BreastCancer"}.get(raw)

    def map_icd(self, icd: str) -> str | None:
        return "BreastCancer" if icd == "C50" else None

plugin_class = BCOnlyPhenotypeModel
```

### Example — multiple plugins in one file

```python
# plugin.py
plugin_classes = [BCOnlyPhenotypeModel, BCTNBCPhenotypeModel]
```

---

## Recommended Directory Layout

```
my_project/
└── plugins/
    ├── phenotype_models/
    │   ├── bc_only/
    │   │   └── plugin.py
    │   └── bc_tnbc/
    │       └── plugin.py
    ├── trait_mappers/
    │   ├── my_registry_bc_only/
    │   │   └── plugin.py
    │   └── my_registry_bc_tnbc/
    │       └── plugin.py
    └── incidence_sources/
        └── my_registry/
            └── plugin.py
```

Point HerediCalc at the root of the `plugins/` directory:

```bash
export HEREDICALC_PLUGIN_PATH=~/my_project/plugins
```

---

## Verifying Discovery

```bash
heredicalc plugins list --kind phenotype_model
```

External plugins appear alongside built-ins.  The `Source` column shows the
file path so you can confirm the correct file was loaded.

---

## Load Order and Overrides

Plugins are discovered in this order:

1. Built-ins (`src/heredicalc/plugins/`)
2. Entry-point plugins (installed packages that declare `heredicalc.plugins`)
3. User plugin directory
4. `HEREDICALC_PLUGIN_PATH` directories (left to right)

A later plugin with the **same name and version** as an earlier one silently
replaces it.  This lets you override a built-in plugin for a specific project
without touching the package.

---

## Data Files in External Plugins

If your plugin needs data files (CSV tables, YAML mappings), place them next to
`plugin.py` and read them with `pathlib.Path(__file__).parent`:

```python
import yaml
from pathlib import Path

_DATA = yaml.safe_load((Path(__file__).parent / "mappings.yml").read_text())
```

---

## Compatibility with `heredicalc add trait`

External plugins coexist with user-defined traits registered via
`heredicalc add trait`.  Traits (RR tables + CRHF values) are stored in
`~/.local/share/heredicalc/traits/` and loaded independently of the plugin
system.  You can use both mechanisms together.
