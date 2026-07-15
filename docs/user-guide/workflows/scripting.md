---
layout: default
title: Automate with Python and the CLI
parent: Workflows
grand_parent: User Guide
nav_order: 5
permalink: /user-guide/workflows/scripting/
redirect_from:
  - /user-guide/features/scripting/
---

# Automate with Python and the CLI

Import only `ring5` in user scripts. The package composes parsing, core services, and rendering
without exposing `src.*` modules as a supported interface.

## Run a complete analysis

```python
import ring5

with ring5.Session() as session:
    parsed = session.parse(
        "results/",
        variables=["simTicks", "system.cpu.ipc"],
    )
    data = session.load(parsed.csv_path)
    reduced = session.reduce_seeds(
        data,
        categorical_cols=["benchmark", "configuration"],
        statistic_cols=["system.cpu.ipc"],
    )
    spec = ring5.FigureSpec(
        x="benchmark",
        group="configuration",
        y_columns=["system.cpu.ipc"],
        title="IPC by configuration",
        ylabel="IPC",
    )
    figure = session.plot(
        "grouped_bar",
        data=reduced,
        config=spec,
        engine="matplotlib",
    )
    session.export(figure, "figures/ipc.pdf", deterministic=True)
```

The context manager cancels pending session work and removes temporary parser output. Process-wide
worker pools remain reusable; long-running programs can call `ring5.shutdown()` to release them
early.

## Discover and handle errors

Use `ring5.available_plot_types()` rather than copying a registry inventory. Public failures inherit
from `ring5.Ring5Error`, with narrower types such as `ParseError`, `PipelineError`, `RenderError`,
and `ExportError`.

```python
try:
    written = ring5.render_portfolio("paper-a", "figures/")
except ring5.PortfolioError as exc:
    raise SystemExit(f"portfolio render failed: {exc}") from exc
```

Run `print(ring5.doctor())` before an environment-dependent export. The report identifies missing
Perl, browser, and XeLaTeX dependencies without making optional tools essential.

## Use the CLI

```text
ring5 doctor
ring5 parse STATS_PATH --variable NAME --output FILE
ring5 render PORTFOLIO --out-dir DIRECTORY
ring5 upgrade PORTFOLIO
```

Run `ring5 COMMAND --help` for current options. `render` uses Matplotlib and PDF by default; Plotly
defaults to HTML. Pass `--no-deterministic` only when byte-stable output is not required.

## Use portable table scripts

`ring5.Table` and `ring5.read_table` provide a pandas-independent handle for figure scripts.
`Session.shape`, `reduce_seeds`, and `remove_outliers` return a `Table` when given one; plot methods
also accept it. Use a DataFrame when the analysis needs pandas operations outside the supported
surface.
