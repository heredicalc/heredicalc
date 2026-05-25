# Penetrance Models

A penetrance model converts a hazard DataFrame (output of the hazard model) into a
MECE `PenetranceTable` — one row per (age band × sex × phenotype) combination —
for use by the FLB calculator.

HerediCalc ships two built-in penetrance models.

---

## `victor`

**The mathematically correct VICTOR competing-risk model.**

Implements the full five-step VICTOR algorithm as described in
[Competing-Risk Model](../algorithms/competing-risk-model.md):

1. Hardy-Weinberg correction to back-calculate carrier-free baseline rates
2. All-cause hazard including OtherTrait ($RR_g = 1$)
3. All-cause survival $S_g(a)$ at band end
4. Cause-specific cumulative incidence functions (CIF)
5. MECE penetrance table: affected rows as CIF increments; unaffected row as $1 - S_g(a_1)$

### Configuration

```yaml
plugins:
  penetrance_model: victor   # default — can be omitted
  hazard_model: annual_rate  # default — can be omitted
```

### Plugin metadata

| Field | Value |
|-------|-------|
| Name | `victor` |
| Kind | `penetrance_model` |
| Compatible with | `flb_calculator: segregatr`, `liability_assigner: victor_standard` |
| Sub-plugins | `rr_model` (default: `tabular`), `crhf_model` (default: `lookup`) |

---

## `victor_cool3`

**COOL3-compatible VICTOR variant — for validation and comparison only.**

Replicates the three systematic deviations present in COOL3 v3. See
[VICTOR Model Tracks](../algorithms/victor-model.md) for a detailed analysis.

| Deviation | Description |
|-----------|-------------|
| Tracked-only survival | OtherTrait excluded from all-cause hazard |
| Band-midpoint evaluation | Unaffected rows use $S_g((a_0+a_1)//2)$ instead of $S_g(a_1)$ |
| No band-width normalisation | Delegated to `annual_rate_cool3` hazard model |

!!! warning "Use with `annual_rate_cool3`"
    `victor_cool3` must be paired with `annual_rate_cool3` to reproduce COOL3 output.
    HerediCalc applies this automatically when `hazard_model` is not explicitly set.
    Using `victor_cool3` with `annual_rate` will produce internally inconsistent results.

### Configuration

```yaml
plugins:
  penetrance_model: victor_cool3
  # hazard_model: annual_rate_cool3  ← set automatically; explicit override possible
```

Or via CLI (hazard-model is set automatically by the cascade):

```bash
heredicalc run pedigree.ped \
  --penetrance-model victor_cool3 \
  [other options...]
```

### Plugin metadata

| Field | Value |
|-------|-------|
| Name | `victor_cool3` |
| Kind | `penetrance_model` |
| Default | `hazard_model: annual_rate_cool3` |
| Compatible with | `flb_calculator: segregatr`, `liability_assigner: victor_standard` |
| Sub-plugins | `rr_model` (default: `tabular`), `crhf_model` (default: `lookup`) |

---

## Comparison

| Feature | `victor` | `victor_cool3` |
|---------|----------|----------------|
| All-cause hazard | All phenotypes incl. OtherTrait | Tracked phenotypes only |
| Unaffected row | $1 - S_g(a_1)$ (band end) | $1 - S_g((a_0+a_1)//2)$ (midpoint) |
| Default hazard model | `annual_rate` | `annual_rate_cool3` |
| Scientific validity | ✅ Correct | ⚠️ COOL3-compatible only |
| Use for | Publication, analysis | Validation, COOL3 comparison |

---

## Sub-Plugin Dependencies

Both penetrance models require two sub-plugins, injected automatically:

| Sub-plugin kind | Default | Purpose |
|-----------------|---------|---------|
| `rr_model` | `tabular` | Relative risk lookups by gene, sex, age, phenotype, zygosity |
| `crhf_model` | `lookup` | Cumulative risk haplotype frequency (CRHF) per gene |

Override in config:

```yaml
plugins:
  params:
    rr_model: tabular
    crhf_model: lookup
```
