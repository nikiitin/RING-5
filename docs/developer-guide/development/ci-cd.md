---
title: "CI/CD Pipeline"
parent: Development
grand_parent: Developer Guide
nav_order: 4
---

# CI/CD Pipeline

RING-5 uses the same Make targets locally and in GitHub Actions. Run the local
quality and test gates before pushing so CI failures are reproducible without a
runner-specific command.

## Local setup

Install the exact development, security, and browser dependencies:

```bash
make dev
make pre-commit-install
```

Run all hooks manually with:

```bash
make pre-commit
```

The third-party hooks validate whitespace, file syntax, merge markers, large
files, debug statements, line endings, filename case, docstring placement, and
private keys. Direct commits to `main` are blocked locally.

Project hooks run the configured versions of Black, Flake8, MyPy, Bandit, and
the following semantic checks:

| Check | Command | Purpose |
|---|---|---|
| Architecture | `make arch-check` | Enforce layer boundaries and prohibited constructs |
| Comments | `make comments-check` | Reject assistant-specific and internal milestone language |
| Public docs | `make docs-check` | Require public docstrings and matching parameter names |
| Dependencies | `make dependency-check` | Compare imports with declared runtime dependencies and run `pip check` |

## Quality gate

```bash
make quality-gate
```

The quality gate runs architecture, comment, documentation, dependency,
formatting, lint, type, Bandit, and `pip-audit` checks. It covers `app.py`,
`ring5/`, `src/`, `scripts/`, and the test suite where applicable.

Run the full non-browser suite with the CI branch-coverage floor:

```bash
make test-ci
```

The coverage gate measures `src` and `ring5`, includes branch coverage, and
requires at least 84%. Plotly/Kaleido export tests run separately with one
worker because concurrent Chromium exports can starve each other.

Browser tests also separate normal parallel tests from serial export tests:

```bash
make test-e2e
```

## GitHub Actions

The repository has three workflows in `.github/workflows/`.

### CI (`ci.yml`)

CI runs for pushes and pull requests targeting `main`, and by manual dispatch.
All jobs create `python_venv` and install the exact extras from `pyproject.toml`.

| Job | Python | Work |
|---|---|---|
| Quality, security, and package | 3.12 | `make quality-gate`, then `make package-check` |
| Tests | 3.12, 3.13, 3.14 | Non-browser suite; 3.12 also enforces coverage |
| Figure exports | 3.12, 3.13, 3.14 | Serial Plotly/Kaleido export suite |
| Streamlit E2E | 3.12 | Chromium install, fixtures, and `make test-e2e` |

The test matrix waits for quality checks. E2E waits for the Python test matrix.
Coverage is uploaded from Python 3.12; upload failure does not mask the local
coverage gate.

### CodeQL (`codeql.yml`)

CodeQL runs Python security and quality queries on pushes and pull requests to
`main`, on its configured schedule, and by manual dispatch. Exclusions live in
`.github/codeql/codeql-config.yml`; findings appear in the repository Security
tab.

### Documentation (`pages.yml`)

The Pages workflow builds the Jekyll documentation and deploys it on applicable
changes to `main`. Concurrency control prevents an older deployment from
overwriting a newer one.

## Dependencies

Runtime and development dependencies use exact versions in `pyproject.toml` so
the application, CI, and figure exports remain reproducible. Audit the current
environment with:

```bash
make dependency-check
make security-audit
make check-outdated
```

Dependabot checks Python packages and GitHub Actions weekly. Its configuration
groups compatible minor and patch updates for production and development
dependencies; major upgrades remain separate reviews.

When updating a dependency:

1. Read its release and migration notes.
2. Update the exact version in `pyproject.toml`.
3. Recreate or update `python_venv` with `make dev`.
4. Run `make quality-gate`, `make test-ci`, `make test-e2e`, and
   `make package-check` as appropriate to the change.
5. Keep major upgrades in a dedicated pull request.

## Pull requests and releases

Pull requests target `main` and should pass all required CI jobs before merge.
Branch-protection settings should require the quality and test jobs at minimum.

Releases use Git tags. Test fixtures too large for the repository are published
as release assets and retrieved by `make test-data`. Documentation merged to
`main` is published through the Pages workflow.

## See also

- [Architecture overview](../architecture/overview.md)
- [Layer boundaries](../architecture/layer-boundaries.md)
- [Testing](testing.md)
- [Dependabot documentation](https://docs.github.com/en/code-security/dependabot)
