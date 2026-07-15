---
layout: default
title: Continuous Integration
parent: Development
grand_parent: Developer Guide
nav_order: 5
permalink: /developer-guide/development/ci-cd/
---

# Continuous integration

The CI workflow separates quality and package validation, non-browser tests, serial figure exports,
LaTeX exports, and Streamlit browser tests. The test matrix covers every Python version declared in
`pyproject.toml`; one job produces the coverage report.

Run the corresponding local targets before pushing:

```bash
make quality-gate
make docs-build docs-audit
make package-check
make test-ci
make test-export
make test-latex     # when XeLaTeX is installed
make test-e2e
```

The documentation CI job installs the locked root `Gemfile`, performs a Jekyll production build,
then audits canonical routes, redirects, assets, and internal links in `_site/`. This catches theme
or plugin mismatches that a Markdown-only check cannot see. CodeQL runs separately on pushes, pull
requests, and its scheduled audit. GitHub Pages uses the same locked build and audit path, and
deploys only from `main`.

When CI differs from a local run, compare the Python version, optional system dependencies, test
markers, xdist mode, and generated fixtures. Reproduce the exact Make target before changing code.
