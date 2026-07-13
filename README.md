# RING-5

**R**eproducible **I**nstrumentation for **N**umerical **G**raphics for gem5

RING-5 turns raw simulator output into publication-ready figures. It supports interactive analysis
through a Streamlit application and repeatable automation through the `ring5` Python API and CLI.
RING-5 currently supports **gem5** and provides an extension point for additional simulators.

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-passing-success)](tests/)
[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-green)](LICENSE)

---

## Why RING-5?

Simulator analysis combines statistics parsing, table transformations, visualization, and
repeatable export. RING-5 provides those stages through one web and scripting interface.

- **Parse once, plot many times.** Scan and parse simulator stats files into structured CSVs with automatic variable discovery.
- **Transform without code.** Normalize against baselines, aggregate across seeds, remove outliers, compute geometric means -- all through a visual pipeline builder.
- **Publication quality out of the box.** Bar charts, grouped bars, stacked bars, line plots, scatter plots, and histograms with full style control. Export to PDF, SVG, PGF, or PNG.
- **Reproducible by design.** Save your entire analysis as a portfolio -- data, transformations, and plots -- and reload it months later for camera-ready revisions.

---

## Getting Started

### Requirements

- Python 3.12, 3.13, or 3.14
- Linux (tested on Ubuntu 20.04+)
- `make` and `pip`

### Install

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
source python_venv/bin/activate
```

For LaTeX export support (PDF/PGF/EPS):

```bash
make install-latex
```

### Launch

```bash
make run
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

### Use the Python API

The supported `ring5` package provides the same workflow without a browser:

```python
import pandas as pd
import ring5

data = pd.DataFrame({"benchmark": ["a", "b"], "ipc": [1.0, 1.4]})
with ring5.Session() as session:
    figure = session.plot(
        "Bar Chart",
        data=data,
        config={"x": "benchmark", "y": "ipc", "title": "IPC"},
        engine="matplotlib",
    )
    session.export(figure, "ipc.pdf", deterministic=True)
```

Plot identifiers and display names are both accepted; call `ring5.available_plot_types()` to
discover the registered identifiers. See
[Scripting & Headless Use](https://nikiitin.github.io/RING-5/user-guide/features/scripting/) for
parsing, typed figure specifications, transformations, and portfolio replay.

---

## Workflow

RING-5 is organized around four steps, each with its own page in the web interface:

### 1. Parse

Navigate to **Data Source**, point RING-5 at a directory containing gem5 output, and set your stats file pattern (e.g., `stats.txt`). Click **Scan Variables** to discover all available metrics -- IPC, cache miss rates, cycles, branch mispredictions, and so on. Select the ones you care about and hit **Parse**. RING-5 generates a consolidated CSV.

### 2. Transform

On the **Manage Data** page, clean and reshape your data:

- **Reduce seeds** -- aggregate multiple random seeds into mean + standard deviation.
- **Remove outliers** -- discard statistical outliers per group using IQR thresholds.
- **Arithmetic operations** -- derive new metrics from existing columns (e.g., MPKI from misses and instructions).
- **Mix columns** -- merge multiple columns with sum, average, or concatenation.

### 3. Plot

On the **Manage Plots** page, create visualizations:

- Pick a plot type (bar, grouped bar, stacked bar, line, scatter, histogram).
- Build a shaper pipeline to prepare the data: normalize against a baseline, sort categories, compute means, filter benchmarks.
- Configure axes, grouping columns, colors, and legend placement.
- Preview interactively, then export.

| Plot Type   | Typical Use                       |
| ----------- | --------------------------------- |
| Bar         | Comparing a single metric         |
| Grouped Bar | Comparing multiple configurations |
| Stacked Bar | Part-to-whole breakdowns          |
| Line        | Trends over parameters or time    |
| Scatter     | Correlations between two metrics  |
| Histogram   | Value distributions               |

### 4. Save

On the **Portfolio** page, save the entire workspace -- data, plots, and pipeline configurations -- as a portable snapshot. Reload it later for revisions or to share with collaborators.

---

## Documentation

Full documentation is available at **[nikiitin.github.io/RING-5](https://nikiitin.github.io/RING-5/)**.

Quick links:

- [Quick Start](https://nikiitin.github.io/RING-5/user-guide/getting-started/first-steps/) -- 5-minute setup
- [Parsing Guide](https://nikiitin.github.io/RING-5/developer-guide/parsing/parsing-architecture/) -- gem5 stats parsing in depth
- [Data Transformations](https://nikiitin.github.io/RING-5/user-guide/features/shapers/) -- shapers and pipelines
- [Creating Plots](https://nikiitin.github.io/RING-5/user-guide/pages/manage-plots/) -- visualization options
- [Python API and CLI](https://nikiitin.github.io/RING-5/user-guide/features/scripting/) -- headless automation
- [Architecture](https://nikiitin.github.io/RING-5/developer-guide/architecture/overview/) -- system design for contributors

---

## Development

### Setup

```bash
make dev                    # Create the environment and install exact dependencies
make pre-commit-install     # Install repository git hooks
```

### Quality checks

```bash
make quality-gate   # Architecture, comments, docs, dependencies, style, types, security
make test-ci        # Non-browser tests and coverage
make test-e2e       # Playwright browser workflows
make package-check  # Validate wheel and source distributions
```

### Project structure

```text
src/
  core/
    models/          # Data models, protocols, configuration
    state/           # Repository-based state management
    services/        # Business logic
      managers/      #   Arithmetic, outlier, reduction operations
      data_services/ #   CSV pool, config, variables, portfolios
      shapers/       #   Pipeline CRUD + transformation strategies
  web/
    pages/           # Streamlit page components
    components/      # Reusable Streamlit components
    rendering/       # Plotly and Matplotlib connectors
  parsing/           # Simulator protocols and gem5 implementation
ring5/               # Supported headless Python API and CLI
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. The short version:

1. Branch from `main`.
2. Add focused tests for changed behavior.
3. Run the repository quality, test, and package gates.
4. Open a pull request.

---

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).

## Citation

If RING-5 is useful for your research, please cite:

```bibtex
@software{ring5,
  title  = {RING-5: Reproducible Instrumentation for Numerical Graphics for gem5},
  author = {Nicolas, V.},
  year   = {2026},
  url    = {https://github.com/nikiitin/RING-5}
}
```
