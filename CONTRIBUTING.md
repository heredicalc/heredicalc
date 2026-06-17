# Contributing to HerediCalc

## Development Setup

```bash
git clone <repo>
cd heredicalc_v4
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest tests/ --tb=short
mkdocs build --strict
```

## CI5 incidence data

The CI5 incidence data is © IARC and is **not** committed (see
[DATA-NOTICE.md](DATA-NOTICE.md)). The test suite runs in two modes, selected
automatically by whether the full data is installed in the package:

- **Without the data** (default): the incidence-source plugins fall back to the
  de-minimis mini fixtures under `tests/fixtures/ci5_mini/` (via the
  `HEREDICALC_CI5_DATA_DIR` environment variable), and the real-FLB validation tests
  are skipped. This is the fast CI lane — quick and offline.
- **With the data**: run `python scripts/fetch_ci5_data.py` to install the full data
  into the package, then `pytest` runs the complete suite including FLB validation.
  This is the `full-validation` CI lane (manual `workflow_dispatch` and on `v*` tags,
  with the IARC download cached).

Set `HEREDICALC_CI5_DATA_DIR=/path/to/data` to point the plugins at a CI5 data tree
outside the package (each band under `<dir>/<band>/`); unset, the packaged `data/`
directory is used.

## Commit Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(scope): short description
fix(scope): short description
docs(scope): short description
test(scope): short description
chore(scope): short description
```

Every `feat(scope):` commit must be immediately followed by a `docs(scope):`
commit updating the relevant manual page.

## Plugin Development

See [docs/plugins/writing-plugins.md](docs/plugins/writing-plugins.md).

## Pull Request Workflow

1. Create a feature branch from `main`
2. Implement changes with accompanying tests and docs
3. Ensure `pytest` and `mkdocs build --strict` pass
4. Open a PR against `main`

## Releasing

Pushing a `v*` tag (e.g. `v4.2.0`) to this repository triggers two workflows, both
operating on the canonical repo itself with the automatic `GITHUB_TOKEN`:

- **ci.yml** runs the `full-validation` lane — it fetches the CI5 data and runs the
  complete suite including FLB validation. This is where the tag is verified; the
  release workflow does not re-test.
- **release.yml** builds the sdist + wheel (hatch-vcs), creates a GitHub Release in
  this repo with notes extracted from `CHANGELOG.md` and the build artifacts attached,
  and deploys the documentation to the `gh-pages` branch via `mkdocs gh-deploy`.

PyPI publishing is intentionally deferred and will be added later.
