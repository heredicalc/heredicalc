# HerediCalc v4

**Full Likelihood Bayes (FLB) factor computation for Bayesian cosegregation analysis.**

HerediCalc quantifies whether a genetic entity co-segregates with a heritable
phenotype in a pedigree beyond what is expected by chance. The resulting FLB
factor supports pathogenicity classification of genetic variants (FLB > 10:
strong evidence of pathogenicity).

## Requirements

- Python ≥ 3.12
- R ≥ 4.2 with packages: `segregatr`, `kinship2`

## Quick Install

```bash
pip install heredicalc
```

For R dependency setup, see [docs/user-guide/cli.md](docs/user-guide/cli.md).

## Quick Start

```bash
# Generate a config file interactively
heredicalc init

# Run FLB computation
heredicalc run Belman.ped --config heredicalc.yml

# Batch computation over a directory of pedigrees
heredicalc batch pedigrees/ --config heredicalc.yml
```

Example `heredicalc.yml`:

```yaml
computation:
  genetic_entity: BRCA1
  allele_freq: 0.0001

plugins:
  incidence_source: ci5_ix
  phenotype_model: hbopc
  trait_mapper: ci5_hbopc
  penetrance_model: victor
  flb_calculator: segregatr
  params:
    population: Latvia
    age_bands: [30, 40, 50, 60, 65, 70, 80]
```

## Documentation

Full documentation: [https://heredicalc.readthedocs.io](https://heredicalc.readthedocs.io)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
