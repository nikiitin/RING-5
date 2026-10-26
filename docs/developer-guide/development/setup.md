---
layout: default
title: Development Setup
parent: Development
grand_parent: Developer Guide
nav_order: 1
permalink: /developer-guide/development/setup/
---

# Development setup

RING-5 requires Python 3.12 or newer. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
for checkout setup. Make uses `uvx` to run the pinned project tool, uv 0.13.5.
Install Git, Make, and Perl before running parser tests.

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
make pre-commit-install
```

`make dev` creates `python_venv`, installs the project in editable mode with the `dev`, `ci`, and
`e2e` extras from `uv.lock`, installs Playwright Chromium and the reviewed Chrome for Testing release,
downloads the integration archive when needed, and generates mock fixtures.

Use the environment executables for focused commands:

```bash
python_venv/bin/python --version
python_venv/bin/pytest tests/unit/test_target.py -n 0 --no-cov
python_venv/bin/mypy path/to/module.py
```

Start the web application with `make run`. Use `RING5_DATA_DIR` to redirect the CSV pool,
portfolios, and saved configuration during isolated testing. Source checkouts default to `.ring5`
below the repository. Installed wheels default to the platform user-data directory reported by
`platformdirs.user_data_path("ring5", appauthor=False)`. The environment override takes precedence.

`make sync-dev` reproduces all development dependencies without downloading browsers. The lock
covers Python 3.12 through 3.15; CI tests each supported version. After editing dependency pins, run
`make lock` and review `uv.lock` before running the full gates. To upgrade transitive packages
intentionally, run `uv lock --upgrade`, then `make sync-dev`.

Documentation uses Ruby 3.3 and Bundler 4.0.23 with `Gemfile.lock`. Install Ruby development headers
and a C/C++ build toolchain before `bundle install`; several gems compile native extensions.
`make docs-security` audits the complete Ruby lock against the current advisory database.

Optional dependencies are purpose-specific:

- `make chrome-install` delegates to `ring5 install-chrome` for Kaleido static exports. Set
  `BROWSER_PATH` to the printed executable path before launching RING-5.
- `make playwright-install` installs Chromium for browser tests.
- `make install-latex` installs TeX on supported package managers.
- `make check-latex` verifies the tools required by PGF tests.

## Chrome release policy

`ring5/_chrome_install.py` is the installer used by the public `ring5 install-chrome` command,
Make, and CI. Its packaged `ring5/resources/chrome-for-testing.json` admits one exact Stable
release and the six official native artifacts. Use the CLI from installed wheels as well as
checkouts; no repository script or vendor installer is required. Native Windows can run
`python_venv/Scripts/python.exe -m ring5.cli install-chrome`; Make callers can override `PYTHON`.

Installation uses only pinned official HTTPS URLs. It verifies the expected size, object
generation, provider MD5 transfer checksum, and reviewed project SHA-256 before safe staged
extraction and atomic publication. A receipt identifies the release and installed files. Publication
requires native exclusive rename support from the cache filesystem; unavailable support produces
an installation error. Relative archive links contain no parent-traversal components. Reuse
checks the receipt and file contents. Failures preserve existing and unrelated cache directories.
The CLI never executes a browser; CI explicitly passes the returned path through `BROWSER_PATH`
to its serial native export tests.

To review a release update, inspect only `channels.Stable` in the provider's
[named-channel catalog](https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json).
Match the version, revision, platform, and archive URL to that catalog. Acquire each archive over
official HTTPS, compare the provider's object size, MD5, and generation, and record the computed
SHA-256 and ZIP layout before updating the manifest. Google publishes no archive SHA-256 or
release-signature field in that catalog; the first verified HTTPS acquisition is the bootstrap
trust step. MD5 is a transfer check, and the reviewed SHA-256 is a project pin. Preserve the
acquisition evidence with the review and run all-platform inert archive tests, installed-wheel
checks, and the supported native serial export gates before admission.

A newer Stable catalog entry requires a reviewed manifest update. Dependabot's Python, Actions,
and Bundler coverage does not refresh this custom manifest; metadata inspection has separate
ownership and does not authorize unattended downloads or admission.

Next: [Contributor Workflow]({{site.baseurl}}/developer-guide/development/workflow/).
