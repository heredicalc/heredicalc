# CLI User Guide

!!! note
    This page is a stub. Full documentation will be added in Phase 1.

## R Dependency Setup

HerediCalc requires R ≥ 4.2 with the `segregatr` and `kinship2` packages.

```r
install.packages("kinship2")
install.packages("segregatr")
```

## Commands

- `heredicalc run` — compute FLB for a single pedigree
- `heredicalc batch` — batch computation over a directory
- `heredicalc init` — interactive config file generator
- `heredicalc plugins` — manage plugins
