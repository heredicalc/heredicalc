# Writing Plugins

This page covers writing **built-in plugins** — plugins that ship with
HerediCalc and live in `src/heredicalc/plugins/`. For research-specific plugins
that live outside the repository, see [External Plugins](external-plugins.md).

---

## Structure of a Built-in Plugin

Each plugin lives in its own package directory:

```
src/heredicalc/plugins/<kind>/<name>/
    __init__.py      # empty
    plugin.py        # plugin class
    data/            # optional data files (CSV, YAML, …)
        __init__.py  # empty — required for importlib.resources
        mappings.yml
```

---

## Minimal Plugin

Every plugin is a plain Python class with a class-level `meta: PluginMeta`
attribute and the methods required by its kind's `Protocol`
(see [Plugin Kinds](plugin-kinds.md)).

```python
# src/heredicalc/plugins/trait_mappers/my_mapper/plugin.py
from __future__ import annotations
from heredicalc.core.models.plugin import PluginMeta

class MyTraitMapper:
    meta = PluginMeta(
        name="my_mapper",
        version="1.0.0",
        kind="trait_mapper",
        description="Maps MySource trait codes to HBOPC phenotypes",
        author="HerediCalc",
        min_api_version="1.0.0",
        compatible_with={
            "incidence_source": ["my_source"],
            "phenotype_model": ["hbopc"],
        },
    )

    def map_trait(self, trait_code: str) -> str | None:
        return {"42": "BreastCancer"}.get(trait_code)

    def map_affection(self, raw: str) -> str | None:
        return {"BrCa": "BreastCancer"}.get(raw)
```

---

## Reading Data Files

Use `importlib.resources` to read bundled data files. This works correctly
whether the package is installed from source, as an editable install, or
from a wheel:

```python
from importlib.resources import files as _files

_DATA = _files(__package__) / "data"

# In __init__ or a lazy loader:
import yaml
from pathlib import Path

raw = yaml.safe_load(Path(str(_DATA / "mappings.yml")).read_text(encoding="utf-8"))
```

Never use `__file__`-relative paths — they break with zip imports.

---

## Sub-plugin Dependencies

If your plugin needs another plugin (e.g. an RR model), declare it in
`meta.requires` and accept it as a constructor argument:

```python
from heredicalc.core.models.plugin import PluginMeta
from heredicalc.plugins.protocols import RRModel, CRHFModel

class MyPenetranceModel:
    meta = PluginMeta(
        name="my_penetrance",
        kind="penetrance_model",
        requires={"rr_model": None, "crhf_model": None},
        ...
    )

    def __init__(self, rr_model: RRModel, crhf_model: CRHFModel) -> None:
        self._rr = rr_model
        self._crhf = crhf_model
```

The registry injects the resolved instances automatically.
See [Plugin Dependencies](plugin-dependencies.md) for details.

---

## Registering the Plugin

Add the class to `_BUILTIN_PLUGINS` in `src/heredicalc/plugins/__init__.py`:

```python
from heredicalc.plugins.trait_mappers.my_mapper.plugin import MyTraitMapper

_BUILTIN_PLUGINS = [
    ...
    MyTraitMapper,
]
```

The registry imports this list during `discover_builtins()`.

---

## Registering a New Plugin Kind

If your plugin introduces a kind that does not yet exist, register it before
adding plugins of that kind. No core code changes are required:

```python
# In your plugin's __init__.py or a setup hook:
registry.register_kind("my_new_kind")
```

---

## Compatibility Declaration

Declare which other plugins your plugin is compatible with. The registry checks
these constraints when the pipeline is assembled and raises
`PluginCompatibilityError` on a mismatch:

```python
compatible_with={
    "incidence_source": ["ci5_ix"],   # only works with CI5-IX data
    "phenotype_model": ["hbopc"],     # only works with the HBOPC model
}
```

---

## Checklist

Before submitting a built-in plugin:

- [ ] `__init__.py` exists and is empty in the plugin package and `data/`
- [ ] Data files are read via `importlib.resources`, not `__file__`
- [ ] `meta.kind` is a registered kind
- [ ] `meta.compatible_with` is declared where applicable
- [ ] Sub-plugin dependencies are in `meta.requires` and `__init__` parameters
- [ ] Class is added to `_BUILTIN_PLUGINS`
- [ ] Unit tests in `tests/unit/`
- [ ] No cross-plugin imports (copy shared utilities locally)
