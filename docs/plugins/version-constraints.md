# Version Constraints

HerediCalc uses semantic versioning for the plugin API. Plugins declare which
API versions they are compatible with, allowing safe independent evolution of
the core and third-party plugins.

---

## API Version Fields

Every `PluginMeta` includes two version fields:

| Field | Required | Description |
|-------|----------|-------------|
| `version` | yes | Plugin's own version string, e.g. `"1.0.0"` |
| `min_api_version` | yes | Minimum HerediCalc API version required |
| `max_api_version` | no | Maximum API version supported (`None` = no upper bound) |

```python
meta = PluginMeta(
    name="my_plugin",
    version="1.2.0",
    kind="trait_mapper",
    min_api_version="1.0.0",
    max_api_version=None,   # works with any future API version
    ...
)
```

---

## How Constraints Are Checked

When the registry loads a plugin, it compares the plugin's `min_api_version`
and `max_api_version` against the running HerediCalc API version
(exposed as `heredicalc.__api_version__`).

- If the running version is **below** `min_api_version`, the plugin is rejected.
- If the running version is **above** `max_api_version` (when set), the plugin
  is rejected.
- Rejected plugins log a warning and are skipped; they do not abort startup.

---

## Compatibility Declaration

The `compatible_with` field records which specific plugin names this plugin
works with. It is checked when the pipeline is assembled, not at load time:

```python
compatible_with={
    "incidence_source": ["ci5_viii", "ci5_ix", "ci5_x", "ci5_xi", "ci5_xii"],
    "phenotype_model": ["hbopc"],
}
```

A `PluginCompatibilityError` is raised at pipeline startup if the active
combination violates any `compatible_with` constraint.

---

## Plugin's Own `version`

The `version` field identifies the plugin itself (not the API). Multiple
versions of the same plugin can coexist in the registry. The registry resolves
to the highest available version by default; a specific version can be requested
with a constraint string:

```yaml
plugins:
  trait_mapper: ci5_ix_hbopc==1.0.0   # exact version pin
  trait_mapper: ci5_ix_hbopc>=1.1.0   # lower bound
```

---

## Guidelines for Plugin Authors

- Set `min_api_version` to the API version where the protocol methods you use
  were introduced. For plugins targeting the current release, use `"1.0.0"`.
- Leave `max_api_version` as `None` unless your plugin is known to break with
  a future API change. Broad compatibility is preferable.
- Increment your plugin's `version` whenever the behaviour changes in a way
  that could affect reproducibility of results.
