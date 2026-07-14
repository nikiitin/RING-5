---
layout: default
title: Install RING-5
parent: Getting Started
grand_parent: User Guide
nav_order: 1
permalink: /user-guide/getting-started/installation/
---

# Install RING-5

RING-5 requires Python 3.12 or newer. Install Git and Make before using the repository targets.
Parsing gem5 statistics requires Perl; loading an existing CSV does not.

## Install a development checkout

Use this path when you will run the application, tests, or documentation locally:

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
```

The target creates `python_venv`, installs RING-5 in editable mode with development and test
dependencies, installs Playwright Chromium, and prepares test fixtures. It can take several minutes
on the first run.

Start the web application:

```bash
make run
```

Open <http://localhost:8501>. Stop the server with <kbd>Ctrl</kbd>+<kbd>C</kbd>.

## Install runtime dependencies only

Use the runtime target if you only need the web application, Python API, and CLI:

```bash
make install
make run
```

This path does not install a browser for Playwright or Plotly static image export. Plotly HTML
export and Matplotlib PDF, PNG, and SVG export remain available without those optional tools.

## Check external dependencies

Activate the environment and run the dependency report:

```bash
source python_venv/bin/activate
ring5 doctor
```

The report distinguishes the essential Perl dependency from optional tools:

- A Chrome-family browser enables Plotly PNG, SVG, and PDF export. Plotly HTML export does not need
  Chrome.
- XeLaTeX enables Matplotlib PGF export. Install it with `make install-latex` where that target
  supports your package manager.

RING-5's Matplotlib PDF export does not require LaTeX.

## Verify the installation

```bash
source python_venv/bin/activate
python -c "import ring5; print(ring5.__version__)"
ring5 --help
```

If either command fails, confirm that you are in the repository root and that
`python_venv/bin/python` exists. See
[Troubleshooting and FAQ]({{site.baseurl}}/user-guide/reference/troubleshooting/) for dependency,
parser, rendering, and portfolio failures.

Next: [Core Concepts]({{site.baseurl}}/user-guide/getting-started/concepts/) and
[First Analysis]({{site.baseurl}}/user-guide/getting-started/first-analysis/).
