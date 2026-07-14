# RING-5

RING-5 (Reproducible Instrumentation for Numerical Graphics for gem5) parses simulator statistics,
transforms tabular results, and renders figures through a Streamlit application or the supported
`ring5` Python API and CLI. The included parser supports gem5; parser protocols allow additional
simulators to be added.

RING-5 requires Python 3.12 or newer. Parsing gem5 statistics also requires Perl.

## Install and run the web application

```bash
git clone https://github.com/nikiitin/RING-5.git
cd RING-5
make dev
make run
```

`make dev` creates `python_venv`, installs the application and development dependencies, installs
the Chromium browser used by Plotly image export, and prepares test data. Open
<http://localhost:8501> after Streamlit starts.

See the [installation guide](https://nikiitin.github.io/RING-5/user-guide/getting-started/installation/)
for system dependencies and a smaller runtime-only installation.

## Use the Python API

```python
import pandas as pd
import ring5

data = pd.DataFrame(
    {"benchmark": ["mcf", "xalancbmk"], "ipc": [1.08, 1.31]}
)

with ring5.Session() as session:
    spec = ring5.FigureSpec(
        x="benchmark",
        y_columns=["ipc"],
        title="IPC",
    )
    figure = session.plot(
        "bar", data=data, config=spec, engine="matplotlib"
    )
    session.export(figure, "ipc.pdf", deterministic=True)
```

Use `ring5.available_plot_types()` to discover registered plot identifiers. The
[scripting workflow](https://nikiitin.github.io/RING-5/user-guide/features/scripting/) covers
parsing, transformations, portfolios, and the CLI.

## Documentation

- [User Guide](https://nikiitin.github.io/RING-5/user-guide/) — installation, web and scripting
  workflows, comparison guides, export, and troubleshooting.
- [Developer Guide](https://nikiitin.github.io/RING-5/developer-guide/) — architecture,
  contributor workflow, subsystems, extension guides, and stable interfaces.
- [Contributing](CONTRIBUTING.md) — local setup, tests, and pull-request expectations.

## Verify a change

```bash
make quality-gate
make test-ci
make test-e2e
make package-check
```

Run focused tests while developing. Browser and serial export tests are separated by the Make
targets; see the [developer workflow](https://nikiitin.github.io/RING-5/developer-guide/development/workflow/)
for details.

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
