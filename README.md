# RING-5

**R**eproducible **I**nstrumentation for **N**umerical **G**raphics for gem5

RING-5 turns raw gem5 simulator output into publication-ready figures. Point it at your stats files, pick your variables, and get clean, reproducible plots for your next ISCA, MICRO, or ASPLOS paper -- no scripting required.

[![Python](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-1110%20passing-success)](tests/)
[![License](https://img.shields.io/badge/license-GPL--3.0--or--later-green)](LICENSE)

---

## Why RING-5?

If you work with gem5, you know the drill: parse `stats.txt`, wrangle the data in pandas, fight with matplotlib, and pray the numbers are right. RING-5 handles all of that behind a web interface.

- **Parse once, plot many times.** Scan and parse gem5 stats files into structured CSVs with automatic variable discovery.
- **Transform without code.** Normalize against baselines, aggregate across seeds, remove outliers, compute geometric means -- all through a visual pipeline builder.
- **Publication quality out of the box.** Bar charts, grouped bars, stacked bars, line plots, scatter plots, and histograms with full style control. Export to PDF, SVG, PGF, or PNG.
- **Reproducible by design.** Save your entire analysis as a portfolio -- data, transformations, and plots -- and reload it months later for camera-ready revisions.

---

## Getting Started

### Requirements

- Python 3.12+
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
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

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

| Plot Type          | Typical Use                           |
|--------------------|---------------------------------------|
| Bar                | Comparing a single metric             |
| Grouped Bar        | Comparing multiple configurations     |
| Stacked Bar        | Part-to-whole breakdowns              |
| Line               | Trends over parameters or time        |
| Scatter            | Correlations between two metrics      |
| Histogram          | Value distributions                   |

### 4. Save

On the **Portfolio** page, save the entire workspace -- data, plots, and pipeline configurations -- as a portable snapshot. Reload it later for revisions or to share with collaborators.

---

## Documentation

Full documentation is available at **[nikiitin.github.io/RING-5](https://nikiitin.github.io/RING-5/)**.

Quick links:

- [Quick Start](https://nikiitin.github.io/RING-5/Quick-Start) -- 5-minute setup
- [Parsing Guide](https://nikiitin.github.io/RING-5/Parsing-Guide) -- gem5 stats parsing in depth
- [Data Transformations](https://nikiitin.github.io/RING-5/Data-Transformations) -- shapers and pipelines
- [Creating Plots](https://nikiitin.github.io/RING-5/Creating-Plots) -- visualization options
- [Architecture](https://nikiitin.github.io/RING-5/Architecture) -- system design for contributors

---

## Development

### Setup

```bash
make dev                    # Create venv and install all dependencies
make pre-commit-install     # Install git hooks (black, flake8, mypy, isort, bandit)
```

### Quality checks

```bash
make test           # Run all 1110 tests
make pre-commit     # Run all 14 pre-commit hooks
```

### Project structure

```
src/
  core/
    models/          # Data models, protocols, configuration
    state/           # Repository-based state management
    parsing/         # gem5 stats parser (async, strategy-based)
    services/        # Business logic
      managers/      #   Arithmetic, outlier, reduction operations
      data_services/ #   CSV pool, config, variables, portfolios
      shapers/       #   Pipeline CRUD + transformation strategies
  web/
    pages/           # Streamlit page components
    ui/              # Reusable widgets, data managers, plotting
```

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. The short version:

1. Branch from `main`.
2. Write tests first.
3. All tests, type checks (`mypy --strict`), and linting must pass.
4. Open a pull request.

---

## Performance

RING-5 uses persistent Perl worker pools for parsing. Compared to spawning subprocesses per variable:

| Operation           | Subprocess | Worker Pool | Speedup   |
|---------------------|-----------|-------------|-----------|
| Parse 20 variables  | 54s       | 1s          | **54x**   |
| Scan 1000 variables | 120s      | 8s          | **15x**   |
| Full pipeline       | 180s      | 12s         | **15x**   |

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
