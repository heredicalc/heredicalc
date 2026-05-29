# Plugin Dependencies

Some plugins require other plugins to function. HerediCalc resolves these
dependencies automatically through the registry's dependency injection (DI)
mechanism — you only need to declare them in `PluginMeta`.

---

## Declaring Dependencies

A plugin declares its required sub-plugins via the `requires` field in `PluginMeta`:

```python
meta = PluginMeta(
    name="victor",
    kind="penetrance_model",
    requires={
        "rr_model": None,    # any rr_model plugin
        "crhf_model": None,  # any crhf_model plugin
    },
    ...
)
```

Each key is a plugin kind; the value is either:

| Value | Meaning |
|-------|---------|
| `None` | Accept any registered plugin of this kind |
| `"name"` | Require a specific plugin by name |

---

## Automatic Injection

When the registry instantiates a plugin via `registry.instantiate()`, it:

1. Reads `meta.requires`
2. Resolves each required kind to a concrete plugin (using `params` overrides
   or the kind's default)
3. Passes the resolved instances as constructor arguments

The plugin class must accept these as keyword arguments in `__init__`:

```python
class VictorPenetranceModel:
    meta = PluginMeta(
        name="victor",
        kind="penetrance_model",
        requires={"rr_model": None, "crhf_model": None},
        ...
    )

    def __init__(self, rr_model: RRModel, crhf_model: CRHFModel) -> None:
        self._rr = rr_model
        self._crhf = crhf_model
```

---

## Overriding Sub-plugins

Sub-plugin selection can be overridden in the pipeline `params` dict:

```yaml
plugins:
  penetrance_model: victor
  params:
    rr_model: tabular      # explicit — same as default
    crhf_model: lookup     # explicit — same as default
```

If `rr_model` or `crhf_model` are omitted from `params`, the registry uses
the first registered plugin of that kind.

---

## Default Sub-plugins via `defaults`

A plugin can declare preferred sub-plugins using the `defaults` field:

```python
meta = PluginMeta(
    name="victor_cool3",
    kind="penetrance_model",
    requires={"rr_model": None, "crhf_model": None},
    defaults={"hazard_model": "annual_rate_cool3"},
    ...
)
```

`defaults` are applied before `params` overrides and before registry fallbacks.
This is how `victor_cool3` automatically selects `annual_rate_cool3` without
requiring an explicit configuration entry.

---

## Circular Dependency Detection

`registry.discover_all()` runs a circular dependency check after all plugins
are registered. A `CircularDependencyError` is raised at startup — not at
computation time — if a cycle is detected.

---

## Sub-plugin Kinds

The two built-in sub-plugin kinds consumed by penetrance models are:

| Kind | Built-in | Purpose |
|------|----------|---------|
| `rr_model` | `tabular` | Relative risk lookup by gene / sex / age / phenotype / zygosity |
| `crhf_model` | `lookup` | CRHF value per genetic entity |

Both are registered as full plugin kinds, so external plugins can supply
alternative implementations (e.g. a Bayesian RR model or a population-specific
CRHF source).
