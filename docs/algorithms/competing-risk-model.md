# Competing-Risk Model (VICTOR)

The VICTOR algorithm converts population cancer incidence rates and relative risks
into a MECE (Mutually Exclusive, Collectively Exhaustive) penetrance table for
use with the `segregatr` FLB calculator.

## Background

Population incidence rates from CI5 reflect the observed rates in a population
that is a mixture of non-carriers (NC), heterozygous carriers (Het), and
homozygous carriers (Hom). To compute penetrance for genetic variant carriers,
we must first back-calculate the carrier-free baseline rate, then scale by the
relative risk (RR) for each genotype.

## Notation

| Symbol | Meaning |
|--------|---------|
| $j$ | Phenotype index |
| $a$ | Age in years (0–99) |
| $g$ | Genotype: nc, het, hom |
| $q$ | CRHF — cumulative risk haplotype frequency |
| $\lambda_\text{pop}(j,a)$ | Population hazard rate for phenotype $j$ at age $a$ |
| $RR_g(j,a)$ | Relative risk for genotype $g$, phenotype $j$, age $a$ |
| $\lambda_g(j,a)$ | Genotype-specific hazard for phenotype $j$ |
| $\lambda_{g,\text{all}}(a)$ | All-cause hazard for genotype $g$ at age $a$ |
| $S_g(a)$ | All-cause survival to age $a$ for genotype $g$ |
| $F_{j,g}(a)$ | Cause-specific CIF for phenotype $j$, genotype $g$, by age $a$ |

## Algorithm

### Step 1: Hardy-Weinberg correction

The population rate is a weighted mixture of NC, Het, and Hom rates.
Under Hardy-Weinberg equilibrium with allele frequency $q$:

$$D(j,a) = 1 + 2q \cdot (RR_\text{het}(j,a) - 1)$$

$$\lambda_\text{nc}(j,a) = \frac{\lambda_\text{pop}(j,a)}{D(j,a)}$$

$$\lambda_\text{het}(j,a) = RR_\text{het}(j,a) \cdot \lambda_\text{nc}(j,a)$$

$$\lambda_\text{hom}(j,a) = RR_\text{hom}(j,a) \cdot \lambda_\text{nc}(j,a)$$

**Critical invariant**: $\lambda_\text{het} / \lambda_\text{nc} = RR_\text{het}$ for every $(j,a,\text{sex})$.

**Never use**: $\lambda_\text{het} = RR \cdot \lambda_\text{pop} \cdot (1-q)$ — this is algebraically incorrect.

### Step 2: All-cause hazard per genotype

Sum over all tracked phenotypes $j$ (including OtherTrait with $RR=1$):

$$\lambda_{g,\text{all}}(a) = \sum_j \lambda_g(j, a)$$

### Step 3: All-cause survival

$$S_g(a) = \exp\!\left(-\sum_{i=0}^{a} \lambda_{g,\text{all}}(i)\right)$$

with $S_g(-1) = 1$ (boundary condition).

### Step 4: Cause-specific Cumulative Incidence Function (CIF)

$$F_{j,g}(a) = \sum_{i=0}^{a} S_g(i-1) \cdot \left(1 - e^{-\lambda_g(j,i)}\right)$$

### Step 5: Build MECE rows from age bands

For each age band $[a_0, a_1]$ and each sex:

**Affected rows** (one per tracked phenotype $j$):

$$P_\text{affected}(j, g, [a_0, a_1]) = F_{j,g}(a_1) - F_{j,g}(a_0 - 1)$$

This is the band-specific CIF increment — **not** the cumulative value $F_{j,g}(a_1)$.

**Unaffected row** (one per age band):

$$P_\text{unaffected}(g, [a_0, a_1]) = S_g(a_1)$$

This is the all-cause survival probability at the band end — "P(still event-free through
age $a_1$ | genotype $g$)". The implementation stores $1 - S_g(a_1)$; `segregatr`
inverts unaffected penetrances internally, recovering $S_g(a_1)$ as the likelihood
contribution for an unaffected member whose last follow-up was at age $a_1$.

## Competing Risks

Phenotypes not tracked by the phenotype model (e.g. non-HBOPC cancers) are
aggregated as `OtherTrait` with $RR_g = 1$ for all genotypes. This ensures
correct all-cause survival computation without inflating carrier risk.

Non-cancer mortality is excluded — consistent with the COOL3/VICTOR reference implementation.
