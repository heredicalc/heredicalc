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
| `is_affected` | 1 / 0 — follows the assigned liability class (see below) |
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
- **Members whose affection the phenotype model does not track** (e.g. a
  non-TNBC breast cancer under a TNBC-only model): the unaffected row for their
  sex and age-last-contact band — they count as free of the tracked phenotype
- **Members whose affection is one of several tracked phenotypes** (subtype
  unknown): a composite class, see below
- **Unknown-sex** members: the uninformative slot (all genotype penetrances equal)

The `victor_standard` assigner implements this matching. The zero-based index
is passed to `segregatr` as the `liability_class` column.

### Affections That Are One of Several Tracked Phenotypes

A member can be known to be affected while the exact tracked phenotype is not:
a breast cancer whose TNBC status was never recorded, under a model that tracks
TNBC and nonTNBC separately. Picking one row would bias the result in a fixed
direction; marking the member `.` would discard the fact that they are affected.

A phenotype model may therefore map such an affection to a **sequence** of
tracked phenotypes ("exactly one of these"). `victor_standard` then builds a
**composite liability class**: for the member's sex and age band it takes the
affected row of every candidate and adds the penetrances column-wise
(`nc`, `het`, `hom` separately). Because the candidate events are mutually
exclusive, the sum is exactly the probability that the member has one of them
given the genotype — the marginalisation over the unknown subtype, not an
approximation, since the likelihood factorises over members once genotypes are
fixed. The composite row is appended to the penetrance table on first use
(phenotype name `A|B`, sorted), reused for later members of the same sex and
band, and reaches `segregatr` through the penetrance TSV like any other class.

The composite row carries `is_affected = True`, so the affected flag passed to
R (next section) is `1` for such members. A sequence of one phenotype behaves
exactly like that single phenotype; an empty sequence like `None`. Members
with a completely unknown phenotype (`.`) are untouched: they never enter this
path and remain affection-unknown for `segregatr`. If every candidate row is
zero for the member's group, the composite has no penetrance either and
`ZeroPenetranceError` is raised as for a single class.

### The Affected Flag Follows the Liability Class

`segregatr` uses the penetrance `p` of a member's class when the member is
affected and `1 - p` when unaffected. The affected flag HerediCalc passes to R
is therefore derived from the *assigned class*, not from the raw pedigree: a
member is passed as affected only if the pedigree marks them affected **and**
their liability class is an affected class. A member with an untracked
affection sits in an unaffected class and is passed as unaffected, exactly like
an `unaff` member of the same age; `.` (affection unknown) is still passed as
unknown. Before v4.4.0 the raw pedigree flag was passed through, so such
members were scored with the cumulative risk of the tracked phenotype as if
they were cases of it — a bias in favour of the causal hypothesis for carriers.

### Affected Members Without Penetrance Data

A penetrance model can legitimately have no data for a subgroup. For example,
when the incidence source and RR model only cover women, VICTOR emits male rows
whose penetrance is zero for every genotype. Unaffected members of such a group
are assigned as usual: a zero probability of being affected makes them
uninformative, and the FLB is unaffected. An **affected** member of such a
group, however, has probability zero under every genotype, so the likelihood
is zero under both hypotheses and `segregatr` would return `0/0 = NaN`.

HerediCalc raises `heredicalc.core.exceptions.ZeroPenetranceError` instead of
returning `NaN`. The exception carries the member's `individual_id`, the
`group` that lacks data (sex, phenotype, age band), a `reason`, and, where
known, the `pedigree_id`:

- `victor_standard` raises when an affected member is matched to a row whose
  penetrance values are all zero or undefined (`NaN`).
- `segregatr` re-checks the `liability_map` it receives and raises with the
  `pedigree_id` attached. A `ZeroPenetranceError` is never wrapped into a
  `SegregaError` or turned into a `NaN` FLB; it propagates unchanged to the
  caller.

The check applies to any group without penetrance data, not only to sex: it
fires whenever no genotype gives the observed affection a defined, non-zero
probability. It uses the same affected status as the hand-off to R: a member
with an untracked affection in an all-zero unaffected class is passed as
unaffected and does not trigger it. To compute an FLB for such a pedigree, supply penetrance data for
the group (incidence and RR rows) or exclude the affected member's family.

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
