---
layout: default
title: Development Setup
parent: Development
grand_parent: Developer Guide
nav_order: 1
permalink: /developer-guide/development/setup/
---

# Development setup

RING-5 requires Python 3.12 or newer. Install [uv 0.13.5](https://docs.astral.sh/uv/getting-started/installation/)
for checkout setup. Install Git, Make, and Perl before running parser tests.

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
make pre-commit-install
```

`make dev` creates `python_venv`, installs the project in editable mode with the `dev`, `ci`, and
`e2e` extras from `uv.lock`, installs Playwright Chromium and Kaleido Chrome, downloads the integration archive when needed, and generates mock fixtures.

Use the environment executables for focused commands:

```bash
python_venv/bin/python --version
python_venv/bin/pytest tests/unit/test_target.py -n 0 --no-cov
python_venv/bin/mypy path/to/module.py
```

Start the web application with `make run`. Use `RING5_DATA_DIR` to redirect the CSV pool,
portfolios, and saved configuration away from the checkout during isolated testing.

`make sync-dev` reproduces all development dependencies without downloading browsers. The lock
covers Python 3.12 through 3.15; CI tests each supported version. After editing dependency pins, run
`make lock` and review `uv.lock` before running the full gates. To upgrade transitive packages
intentionally, run `uv lock --upgrade`, then `make sync-dev`.

Documentation uses Ruby 3.3 and Bundler 4.0.23 with `Gemfile.lock`. Install Ruby development headers
and a C/C++ build toolchain before `bundle install`; several gems compile native extensions.
`make docs-security` audits the complete Ruby lock against the current advisory database.

Optional dependencies are purpose-specific:

- `make chrome-install` installs Chrome for Kaleido static exports.
- `make playwright-install` installs Chromium for browser tests.
- `make install-latex` installs TeX on supported package managers.
- `make check-latex` verifies the tools required by PGF tests.

Next: [Contributor Workflow]({{site.baseurl}}/developer-guide/development/workflow/).
