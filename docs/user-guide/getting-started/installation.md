---
layout: default
title: Install RING-5
parent: Getting Started
grand_parent: User Guide
nav_order: 1
permalink: /user-guide/getting-started/installation/
---

# Install RING-5

RING-5 runs on Linux and requires Python 3.12 or newer. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
for checkout setup. Make uses `uvx` to run uv 0.13.5. Install Git and Make before using the repository targets.
Parsing gem5 statistics requires Perl; loading an existing CSV does not.

## Install a development checkout

Use this path when you will run the application, tests, or documentation locally:

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
```

The target creates `python_venv`, installs RING-5 in editable mode with development and test
dependencies, installs Playwright Chromium and the reviewed Chrome for Testing release, and prepares test fixtures. It can take several minutes
on the first run.

Start the web application:

```bash
make run
```

Open <http://localhost:8501>. Stop the server with <kbd>Ctrl</kbd>+<kbd>C</kbd>.

The web application can read statistics only below its configured filesystem roots. When
`RING5_ALLOWED_STATS_ROOTS` is unset, the root is the directory where you start RING-5. Start it
from the common parent of your result trees, or configure one or more roots before `make run`:

```bash
export RING5_ALLOWED_STATS_ROOTS="$HOME/gem5-results:/mnt/shared-results"
make run
```

Separate roots with `:`. The Data Source page shows
the active roots. This restriction applies to paths submitted through the web application; a
trusted local Python script can open paths available to its own process.

## Install runtime dependencies only

Use the runtime target if you only need the web application, Python API, and CLI:

```bash
make install
make run
```

This path does not install a browser for Playwright or Plotly static image export. Plotly HTML
export and Matplotlib PDF, PNG, and SVG export remain available without those optional tools.

## Check external dependencies

<!--
`uman~ring5.api.doctor.documentation~2`

Covers:
- req~ring5.api.doctor~2

-->

Activate the environment and run the dependency report:

```bash
source python_venv/bin/activate
ring5 doctor
```

The report distinguishes the essential Perl dependency from optional tools:

- A Chrome-family browser enables Plotly PNG, SVG, and PDF export. Plotly HTML export does not need
  Chrome.
- A selected TeX compiler enables Matplotlib PGF export. The default is XeLaTeX; use
  `ring5 doctor --tex-system pdflatex` or `--tex-system lualatex` to check another supported compiler.
  `make install-latex` provides the default XeLaTeX setup where it supports your package manager.

`BROWSER_PATH`, when present, selects the required browser. It can be an executable path or a
command available on `PATH`. An empty selection or a missing/non-executable target is reported
as missing; exports fail without choosing another browser. When the variable is absent, discovery includes
Kaleido's downloaded browser before system locations. The report does not launch external tools.

RING-5's Matplotlib PDF export does not require LaTeX.

## Install Chrome for Plotly static exports

<!--
`uman~ring5.cli.install-chrome.documentation~2`

Covers:
- req~ring5.cli.install-chrome~2

-->

`ring5 install-chrome` works from both a checkout and an installed wheel. It downloads the exact
Stable release in the packaged manifest into the Linux user cache's `ring5` application directory,
under its `chrome` subdirectory. Use
`--cache-dir PATH` to choose a different installation cache. The command prints only the absolute
browser executable path to standard output; instructions and errors go to standard error.

Select that executable before starting the application or a Python export process:

```bash
export BROWSER_PATH="$(ring5 install-chrome)"
```

With another activated environment, use its `ring5 install-chrome` command. `make chrome-install`
delegates to the same CLI; a child process cannot set `BROWSER_PATH` in its parent shell. The
installer neither launches Chrome nor changes browser selection. Installation failure returns
exit code 2 and preserves existing installations. A corrupt or unowned destination is rejected;
inspect the reported path before explicitly removing it and retrying.

The manifest lists native Linux x64 and ARM64 artifacts. ARM64 is untested and may be unavailable.
Other hosts and architectures are rejected without choosing an emulated build. Archive installation
does not establish native static-export support: Chrome's system libraries and a compatible host are
still required. Playwright installs a separate browser for application tests and does not select
RING-5's export browser.

The reviewed SHA-256 values are computed from official HTTPS downloads checked against Google's
object size, MD5, and generation. They are project integrity pins, not a Google signature. See the
[developer setup]({{site.baseurl}}/developer-guide/development/setup/#chrome-release-policy) for the
release policy.

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
