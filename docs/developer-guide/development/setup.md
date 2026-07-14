---
layout: default
title: Development Setup
parent: Development
grand_parent: Developer Guide
nav_order: 1
permalink: /developer-guide/development/setup/
---

# Development setup

RING-5 requires Python 3.12 or newer. Install Git, Make, and Perl before running parser tests.

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
make pre-commit-install
```

`make dev` creates `python_venv`, installs the project in editable mode with the `dev`, `ci`, and
`e2e` dependency groups, installs Playwright Chromium, downloads integration test data when needed,
and generates mock fixtures.

Use the checked-in executables for focused commands:

```bash
python_venv/bin/python --version
python_venv/bin/pytest tests/unit/test_target.py -n 0 --no-cov
python_venv/bin/mypy path/to/module.py
```

Start the web application with `make run`. Use `RING5_DATA_DIR` to redirect the CSV pool,
portfolios, and saved configuration away from the checkout during isolated testing.

Optional dependencies are purpose-specific:

- `make playwright-install` installs Chromium for browser tests.
- `make install-latex` installs TeX on supported package managers.
- `make check-latex` verifies the tools required by PGF tests.

Next: [Contributor Workflow](workflow/).
