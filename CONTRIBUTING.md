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
