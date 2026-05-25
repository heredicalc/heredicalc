# VICTOR Model Tracks

HerediCalc implements two parallel model tracks for FLB computation: a
mathematically correct implementation and a COOL3-compatible emulation.
Both tracks use the same VICTOR competing-risk algorithm; they differ only
in three deliberate deviations applied in the COOL3 track.

For the full mathematical derivation of the VICTOR algorithm, see
[Competing-Risk Model](competing-risk-model.md).

---

## Two Tracks

| Track | Plugins | Purpose |
|-------|---------|---------|
| **HerediCalc correct** | `victor` + `annual_rate` | Mathematically correct FLB computation |
| **COOL3 emulation** | `victor_cool3` + `annual_rate_cool3` | Reproduces COOL3 v3 output for comparison |

The COOL3 emulation track is intended for validation and cross-tool comparison only.
For scientific results, use the correct track.

---

## COOL3 Deviations

Reverse engineering of COOL3 v3 penetrance tables identified three systematic
deviations from mathematically correct competing-risk theory.

### Deviation 1 — Band-Midpoint Evaluation for Unaffected Rows

**Correct**: Survival evaluated at band end $a_1$:
$$P_\text{unaffected}(g, [a_0, a_1]) = S_g(a_1)$$

**COOL3**: Survival evaluated at band midpoint $(a_0 + a_1) // 2$:
$$P_\text{unaffected}^\text{COOL3}(g, [a_0, a_1]) = S_g\!\left(\frac{a_0 + a_1}{2}\right)$$

**Empirical proof** (band 0–29, male, non-carrier):

```
P_unaffected(M, nc)  = 0.000023574
Σ P_affected(M, nc)  = 0.000047148
ratio                = 2.000000   (exact to 9 decimal places)
```

The unaffected value equals exactly half the sum of affected values — a
consequence of the midpoint approximation producing $S_g(14)$ while the correct
value is $S_g(29)$. For the first band, $S_g(14) \approx \frac{1}{2} S_g(29)$
because the hazard is approximately linear.

This deviation makes COOL3 internally inconsistent: affected rows integrate
over the full band $[a_0, a_1]$, while the unaffected row reflects only the
first half of the band.

Implemented in `victor_cool3/plugin.py`.

### Deviation 2 — Tracked-Only Survival

**Correct**: All-cause hazard includes OtherTrait ($RR_g = 1$ for all genotypes):
$$\lambda_{g,\text{all}}(a) = \sum_j \lambda_g(j, a) \quad \text{(all } j \text{)}$$

**COOL3**: OtherTrait is excluded from the all-cause hazard:
$$\lambda_{g,\text{all}}^\text{COOL3}(a) = \sum_{j \neq \text{OtherTrait}} \lambda_g(j, a)$$

This inflates survival probabilities (since competing-risk deaths from non-tracked
cancers are ignored) and inflates the CIF for tracked phenotypes.

Implemented in `victor_cool3/plugin.py`.

### Deviation 3 — No Band-Width Normalisation of Hazard Rates

**Correct**: Annual hazard rate = cases / person-years / band-width:
$$\lambda(j, a) = \frac{\text{cases}(j, [a_0, a_1])}{\text{person-years}(j, [a_0, a_1]) \cdot (a_1 - a_0 + 1)}$$

**COOL3**: Divides only by person-years, omitting the band-width denominator:
$$\lambda^\text{COOL3}(j, a) = \frac{\text{cases}(j, [a_0, a_1])}{\text{person-years}(j, [a_0, a_1])}$$

For 5-year CI5 age bands, this produces hazard rates approximately 5× larger
than correct. The survival curves and CIF are distorted accordingly.

Implemented in `annual_rate_cool3/plugin.py`.

!!! warning
    Using `victor_cool3` with the correct `annual_rate` hazard model does **not**
    reproduce COOL3 output. Both plugins must be used together. HerediCalc
    automatically selects `annual_rate_cool3` when `victor_cool3` is configured
    (plugin-specific default); an explicit `--hazard-model` always takes precedence.

---

## Empirical FLB Comparison

**Dataset**: 226 Belman pedigree permutations, CI5-IX Latvia, BRCA1, allele frequency 0.0001.

| Metric | Value |
|--------|-------|
| Signed deviation (HerediCalc − COOL3) / COOL3 | −15.6 % to +4.1 % |
| Median deviation | −6.6 % |
| Primary case `Belman.ped` | −5.4 % |
| HerediCalc correct FLB (`Belman.ped`) | 25.65 |
| COOL3 reference FLB (`Belman.ped`) | 19.47 |

The systematic negative bias (HerediCalc < COOL3) is consistent with
Deviation 3 inflating COOL3 hazard rates, which in turn inflates COOL3 FLB values.
The residual spread (−15.6 % to +4.1 %) reflects interactions between all three
deviations and varies by pedigree composition (phenotype mix, affected proportions).

---

## When to Use Each Track

| Situation | Recommended track |
|-----------|-------------------|
| Scientific analysis, publication | `victor` + `annual_rate` |
| Reproducing a COOL3 v3 result | `victor_cool3` + `annual_rate_cool3` |
| Comparing HerediCalc to COOL3 | Both — run with each config |
| Regression testing | Both — separate test suites |
