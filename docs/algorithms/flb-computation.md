# FLB Computation

The Full Likelihood Bayes (FLB) factor quantifies cosegregation evidence for a
genetic variant in a pedigree. Values greater than 1 support pathogenicity;
values less than 1 argue against it.

$$
\text{FLB} = \frac{\prod_i P(\text{observations}_i \mid \text{heterozygous})}
                   {\prod_i P(\text{observations}_i \mid \text{non-carrier})}
$$

---

## Pipeline Overview

HerediCalc computes the FLB in six steps:

```
incidence_source  →  trait_mapper  →  hazard_model
                                           ↓
                                    penetrance_model
                                           ↓
                               liability_assigner (per member)
                                           ↓
                                    flb_calculator  →  FLB
```

Each step is handled by a plugin. The default configuration uses:

| Step | Plugin |
|------|--------|
| Incidence data | `ci5_ix` (or another CI5 edition) |
| Trait mapping | `ci5_ix_hbopc` |
| Hazard rates | `annual_rate` |
| Penetrance | `victor` |
| Liability assignment | `victor_standard` |
| FLB calculation | `segregatr` |

---

## The `segregatr` FLB Calculator

HerediCalc delegates the FLB calculation to the R package
[segregatr](https://cran.r-project.org/package=segregatr) via subprocess.
This avoids re-implementing the Elston-Stewart algorithm and ensures numerical
compatibility with the reference implementation.

### What `segregatr` Receives

Two temporary TSV files are written for each computation:

**Pedigree TSV** — one row per pedigree member:

| Column | Description |
|--------|-------------|
| `individual_id` | Integer member ID |
| `father_id` | Father's ID, or 0 for founders |
| `mother_id` | Mother's ID, or 0 for founders |
| `sex_code` | 1 = male, 2 = female |
| `is_affected` | 1 / 0 |
| `is_proband` | 1 / 0 |
| `affection_known` | 1 / 0 |
| `genotype` | `"het"`, `"hom"`, `"nc"`, or `"NA"` |
| `liability_class` | Zero-based index into the penetrance table |

**Penetrance TSV** — one row per liability class, three columns:
`penetrance_nc`, `penetrance_het`, `penetrance_hom`.

Each row stores the probability that a member in that liability class
is in their observed state (affected with a specific disease in a specific
age band, or unaffected up to their last-known age). See
[VICTOR Model Tracks](victor-model.md) for how these values are computed.

### Execution

```
Rscript --vanilla compute_flb.R <pedigree.tsv> <penetrance.tsv> <allele_freq>
```

The R script calls `segregatr::FLB(...)` and returns a single JSON line:
`{"flb": <value>}`. HerediCalc parses the value and cleans up the temp files.
On error, temp files are preserved for diagnostics.

---

## Liability Classes

Every pedigree member is assigned a **liability class index** by the
`liability_assigner` plugin. The index maps to a row in the penetrance table:

- **Affected** members: the row for their canonical disease and age-at-diagnosis band
- **Unaffected** members: the row for their sex and age-last-contact band
- **Unknown-sex** members: the uninformative slot (all genotype penetrances equal)

The `victor_standard` assigner implements this matching. The zero-based index
is passed to `segregatr` as the `liability_class` column.

---

## Allele Frequency

The allele frequency `q` (CRHF — cumulative risk haplotype frequency) enters
the Hardy-Weinberg prior used by `segregatr` to weight heterozygote vs.
homozygote carriers. It is loaded from the `crhf_model` sub-plugin
(built-in: `lookup`) using the `genetic_entity` name from the pipeline config.

---

## Interpreting FLB Values

| FLB | Evidence |
|-----|---------|
| < 0.1 | Against pathogenicity |
| 0.1–1 | Weak evidence against |
| 1–8 | Weak to moderate evidence for |
| 8–350 | Strong evidence for pathogenicity |
| ≥ 350 | Very strong evidence (PP1_Strong per ACMG/InSiGHT) |

Exact thresholds depend on the classification framework (ACMG, InSiGHT, ClinGen).
The FLB from a single family is combined with other evidence lines in a
multi-factorial likelihood model.

---

## Further Reading

- [VICTOR Model Tracks](victor-model.md) — how penetrance values are computed
- [Competing-Risk Model](competing-risk-model.md) — mathematical derivation
- [Penetrance Models](../plugins/penetrance-models.md) — plugin reference
