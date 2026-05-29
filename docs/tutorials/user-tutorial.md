# User Tutorial: Cosegregation Analysis with BRCA2

This tutorial walks you through a complete cosegregation analysis for a gene
that is not included as a built-in. The running example is **BRCA2**.

---

## Prerequisites

- HerediCalc ≥ 4.1.0 installed — verify with:
  ```bash
  heredicalc --version
  ```
- R ≥ 4.2 with the `segregatr` and `kinship2` packages:
  ```r
  install.packages("kinship2")
  install.packages("segregatr")
  ```
- A pedigree file in COOL3-TSV format

---

## Step 1 — Orientation: What Is Already Built In?

Start by checking which plugins are available:

```bash
heredicalc plugins list --kind phenotype_model
heredicalc plugins list --kind trait_mapper
```

HerediCalc ships a complete built-in configuration for **BRCA1**
(RR table + CRHF value). For **BRCA2**, the CRHF value (0.0013) is built in,
but the RR table is missing — you must supply it.

---

## Step 2 — Prepare the RR Table

### Format

The RR table is a CSV file with the following columns:

| Column | Description |
|--------|-------------|
| `gene` | Name of the genetic entity, e.g. `BRCA2` |
| `gender` | `F` (female) or `M` (male) |
| `age_from` | Lower bound of the age band (inclusive) |
| `age_to` | Upper bound (inclusive); **leave blank** for an open upper end |
| `phenotype` | Canonical phenotype name (see below) |
| `heterozygous_rr` | Relative risk for heterozygous carriers |
| `homozygous_rr` | Relative risk for homozygous carriers (for dominant genes: same as `heterozygous_rr`) |

**Canonical phenotype names** for the `hbopc_prca` model:
`BreastCancer`, `OvarianCancer`, `PancreaticCancer`, `ProstateCancer`

### Generate a Template

If you do not yet have an RR file, HerediCalc can generate a pre-filled template
with all default age bands and RR = 1.0:

```bash
heredicalc add trait BRCA2
```

The wizard asks for CRHF, kind, and optional metadata. Because no `--rr-file`
was provided, it writes the template and displays the path:

```
No --rr-file provided. A template has been written to:
  ~/Library/Application Support/heredicalc/traits/rr/BRCA2_template.csv
```

Open the file, fill in your RR values, then continue with Step 3.

### Example Values for BRCA2

!!! warning "For illustration only"
    The values below are simplified estimates based on Antoniou et al. (2003)
    and are intended solely as a tutorial example. For production analyses,
    use validated RR estimates from current literature.

```csv
gene,gender,age_from,age_to,phenotype,heterozygous_rr,homozygous_rr
BRCA2,F,0,29,BreastCancer,7.5,7.5
BRCA2,F,30,39,BreastCancer,11.0,11.0
BRCA2,F,40,49,BreastCancer,6.5,6.5
BRCA2,F,50,59,BreastCancer,4.5,4.5
BRCA2,F,60,69,BreastCancer,3.8,3.8
BRCA2,F,70,79,BreastCancer,2.8,2.8
BRCA2,F,80,,BreastCancer,1.0,1.0
BRCA2,M,0,79,BreastCancer,6.0,6.0
BRCA2,M,80,,BreastCancer,1.0,1.0
BRCA2,F,0,29,OvarianCancer,1.0,1.0
BRCA2,F,30,39,OvarianCancer,4.0,4.0
BRCA2,F,40,49,OvarianCancer,8.5,8.5
BRCA2,F,50,59,OvarianCancer,7.0,7.0
BRCA2,F,60,69,OvarianCancer,5.0,5.0
BRCA2,F,70,79,OvarianCancer,2.5,2.5
BRCA2,F,80,,OvarianCancer,1.0,1.0
BRCA2,M,0,,OvarianCancer,1.0,1.0
BRCA2,F,0,49,PancreaticCancer,3.5,3.5
BRCA2,F,50,79,PancreaticCancer,2.0,2.0
BRCA2,F,80,,PancreaticCancer,1.0,1.0
BRCA2,M,0,49,PancreaticCancer,3.5,3.5
BRCA2,M,50,79,PancreaticCancer,2.0,2.0
BRCA2,M,80,,PancreaticCancer,1.0,1.0
BRCA2,M,0,49,ProstateCancer,2.5,2.5
BRCA2,M,50,69,ProstateCancer,4.5,4.5
BRCA2,M,70,79,ProstateCancer,2.0,2.0
BRCA2,M,80,,ProstateCancer,1.0,1.0
```

---

## Step 3 — Register the Trait

Import the completed RR file together with the CRHF value and optional metadata:

```bash
heredicalc add trait BRCA2 \
  --crhf 0.0013 \
  --kind gene \
  --meta "locus=13q12.3" \
  --meta "omim_nr=600185" \
  --rr-file BRCA2_rr.csv
```

On success:

```
✓ RR table imported from BRCA2_rr.csv
✓ Trait 'BRCA2' added (CRHF=0.0013, kind=gene).
```

Data is stored locally at:

- **macOS:** `~/Library/Application Support/heredicalc/traits/`
- **Linux:** `~/.local/share/heredicalc/traits/`

---

## Step 4 — Choose a Phenotype Model

HerediCalc ships two built-in phenotype models:

| Model | Phenotypes | Suitable for |
|-------|-----------|--------------|
| `hbopc` | Breast, Ovarian, Pancreatic | BRCA1, PALB2, … |
| `hbopc_prca` | Breast, Ovarian, Pancreatic, **Prostate** | **BRCA2**, HOXB13, … |

Because BRCA2 is associated with prostate cancer, use `hbopc_prca` and the
corresponding mapper `ci5_ix_hbopc_prca` (for CI5 edition IX).

---

## Step 5 — Create a Configuration File

Rather than specifying all parameters on every invocation, store them in a
YAML file:

```bash
heredicalc add config
```

The interactive wizard asks for the genetic entity, allele frequency, incidence
source, and population. Provide a filename at the end (e.g. `brca2_latvia.yml`).
Result:

```yaml
computation:
  genetic_entity: BRCA2
  allele_freq: 0.0013

plugins:
  incidence_source: ci5_ix
  phenotype_model: hbopc_prca
  trait_mapper: ci5_ix_hbopc_prca
  params:
    population: "Latvia"
    age_bands: [30, 40, 50, 60, 65, 70, 80]
```

!!! note "Set the phenotype model manually"
    The wizard derives the mapper name automatically from the incidence source
    (`ci5_ix` → `ci5_ix_hbopc`). For `hbopc_prca`, edit `phenotype_model` and
    `trait_mapper` in the YAML file manually to `hbopc_prca` and
    `ci5_ix_hbopc_prca` respectively.

---

## Step 6 — Run the Analysis

```bash
heredicalc run pedigree.ped --config brca2_latvia.yml
```

Output:

```
FLB = 12.3450  (pedigree.ped)
```

For machine-readable JSON output:

```bash
heredicalc run pedigree.ped --config brca2_latvia.yml --format json
# {"pedigree": "pedigree.ped", "flb": 12.345}
```

Multiple pedigrees at once:

```bash
heredicalc batch ./pedigrees/ --config brca2_latvia.yml
```

---

## Step 7 — Interpret the Result

The FLB value quantifies cosegregation evidence:

| FLB | Interpretation |
|-----|----------------|
| < 1 | Against cosegregation |
| 1–8 | Weak to moderate evidence |
| ≥ 8 | Strong evidence for pathogenicity |
| ≥ 350 | Very strong evidence (ACMG/InSiGHT PP1_Strong) |

Exact thresholds depend on the classification framework used
(ACMG, InSiGHT, ClinGen). Consult the relevant guidelines.

For the mathematical foundations of the FLB algorithm, see
[FLB Computation](../algorithms/flb-computation.md).

---

## Managing Traits

```bash
# Overview of all user-defined traits
cat "$(python -c 'import platformdirs; print(platformdirs.user_data_dir("heredicalc"))')/traits/traits.yaml"

# Replace RR values retroactively
heredicalc edit trait BRCA2 --rr-file updated_brca2.csv

# Clone BRCA2 as a starting point for a new gene
heredicalc clone trait BRCA2 PALB2 --crhf 0.0003

# Remove a trait
heredicalc remove trait BRCA2
```
