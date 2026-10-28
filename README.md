# RING-5

RING-5 (Reproducible Instrumentation for Numerical Graphics for gem5) turns simulator statistics
and tabular results into reproducible figures. Use the Streamlit application to explore data, the
supported `ring5` Python API to write analysis scripts, and the CLI to run repeatable batch jobs.
The included parser supports gem5; parser protocols allow additional simulators to be added.

RING-5 runs on Linux and requires Python 3.12 or newer. Parsing gem5 statistics also requires Perl.
Checkout setup uses [uv 0.13.5](https://docs.astral.sh/uv/getting-started/installation/).

## Start with a working example

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
make run
```

Open <http://localhost:8501>. On **Data Source**, select **Load example portfolio** to explore
configured examples of every built-in plot type. The bundled portfolio uses synthetic tutorial
data, works offline, and needs no simulator files. Loading it changes the current session; use
**Save/Load Portfolio** to save your own copy.

`make dev` creates `python_venv`, installs application and development dependencies, installs the
browsers used by Playwright and Plotly image export, and prepares test fixtures. The
[installation guide](https://nikiitin.github.io/RING-5/user-guide/getting-started/installation/)
provides system dependencies and a smaller runtime-only installation.

For Plotly PNG, SVG, or PDF export, activate `python_venv` and set
`export BROWSER_PATH="$(ring5 install-chrome)"` before starting RING-5. Plotly HTML and ordinary Matplotlib
PDF, PNG, and SVG exports need no browser or TeX installation.

## Choose your next task

| I want to… | Start here |
| --- | --- |
| See what each chart is useful for | [Example portfolio tour](https://nikiitin.github.io/RING-5/user-guide/getting-started/showcase/) |
| Learn the web application with known data | [First analysis](https://nikiitin.github.io/RING-5/user-guide/getting-started/first-analysis/) |
| Parse gem5 output or import a table | [Load and parse data](https://nikiitin.github.io/RING-5/user-guide/workflows/loading-data/) |
| Compare a candidate with a baseline | [Compare configurations](https://nikiitin.github.io/RING-5/user-guide/guides/compare-configurations/) |
| Prepare a figure for a paper | [Publication output](https://nikiitin.github.io/RING-5/user-guide/guides/publication-export/) |
| Automate an analysis or reproduce saved figures | [Python and CLI workflow](https://nikiitin.github.io/RING-5/user-guide/workflows/scripting/) |

## Use the Python API

This complete example writes `ipc.pdf` from an explicitly constructed table:

```python
import ring5

data = ring5.Table.from_rows([
    {"benchmark": "mcf", "ipc": 1.08},
    {"benchmark": "xalancbmk", "ipc": 1.31},
])

with ring5.Session() as session:
    spec = ring5.FigureSpec(
        x="benchmark",
        y_columns=["ipc"],
        title="IPC",
        ylabel="Instructions per cycle",
    )
    figure = session.plot("bar", data=data, config=spec, engine="matplotlib")
    session.export(figure, "ipc.pdf", deterministic=True)
```

Use `ring5.available_plot_types()` and `ring5.available_shaper_types()` to discover registered
identifiers. The [scripting workflow](https://nikiitin.github.io/RING-5/user-guide/workflows/scripting/)
provides complete examples with input files, transformations, expected values, saved portfolios,
and CLI commands. The [public API reference](https://nikiitin.github.io/RING-5/developer-guide/api-reference/public-python-api/)
explains method contracts and typed errors.

## Contribute

The [Developer Guide](https://nikiitin.github.io/RING-5/developer-guide/) covers architecture,
subsystems, extension points, and the contributor workflow. Read [CONTRIBUTING.md](CONTRIBUTING.md)
for local setup and pull-request expectations.

```bash
make quality-gate
make test-api
make test-ci
make test-e2e
make package-check
```

Run focused tests while developing. Browser and serial export tests are separated by Make targets;
see the [development workflow](https://nikiitin.github.io/RING-5/developer-guide/development/workflow/).

## License and citation

RING-5 is licensed under GPL-3.0-or-later. See [LICENSE](LICENSE).

```bibtex
@software{ring5,
  title  = {RING-5: Reproducible Instrumentation for Numerical Graphics for gem5},
  author = {Nicolas, V.},
  year   = {2026},
  url    = {https://github.com/nikiitin/RING-5}
}
```
