---
title: "Scripting & Headless Use"
parent: Features
grand_parent: User Guide
nav_order: 7
---

# Scripting & Headless Use

Everything the web app does is also available from plain Python (the
`ring5` package) and from the shell (the `ring5` command) — no Streamlit
server, no browser. Use it for batch parsing, CI figure regression, and
regenerating every figure of a paper from a saved portfolio.

## The Python API

```python
import ring5

with ring5.Session() as s:
    # 1. Parse a tree of gem5 runs (a scan resolves each stat's type)
    result = s.parse("/path/to/sims", variables=["simTicks", "hostSeconds"])

    # 2. Load and transform
    df = s.load(result.csv_path)
    df = s.reduce_seeds(df, ["config_description_abbrev"], ["simTicks"])
    df = s.shape(df, [{"type": "sort", "by": ["simTicks"]}])

    # 3. Create and render a plot in one call
    fig = s.plot(
        "Bar Chart",
        data=df,
        config={"x": "config_description_abbrev", "y": "simTicks",
                "title": "Simulated Ticks"},
        engine="matplotlib",
    )

    # 4. Export
    s.export(fig, "out/simticks.pdf", deterministic=True)

    # 5. Snapshot the whole session
    s.save_portfolio("my_paper")

# Reproduce every figure from the snapshot:
ring5.render_portfolio("my_paper", "figs/", engine="matplotlib", fmt="pdf")
```

Key points:

- **`Session`** owns one isolated workspace (the same state one browser
  session holds). Multiple sessions in one process are independent.
- **Engine is always an explicit argument** (`engine="plotly"` or
  `"matplotlib"`); the rendered figure is a regular `plotly` /
  `matplotlib` figure object.
- **Plot names are forgiving.** `Session.plot` and `Session.create_plot`
  accept identifiers such as `"grouped_bar"` and display names such as
  `"Grouped Bar"`; spaces and hyphens are normalized. Use
  `ring5.available_plot_types()` to discover every registered identifier.
- **Choose the workflow that fits.** `Session.plot(...)` creates, registers,
  and renders in one call. Use `Session.create_plot(...)` followed by
  `Session.render(...)` when the registered plot must be inspected or changed
  before rendering.
- **Configuration can be typed or mapping-based.** Pass a regular mapping for
  concise scripts, or a `ring5.FigureSpec` for editor completion and static
  type checking.
- **Errors are typed.** Everything raised derives from
  `ring5.Ring5Error`: `ScanError`, `ParseError`, `MissingStatError` (a
  typoed stat name fails loudly instead of producing an all-NaN column),
  `PipelineError` (carries the failing step index), `ColumnNotFoundError`,
  `DataLoadError`, `DataValidationError`, `RenderError`, `PortfolioError`,
  `PortfolioVersionError`, `ExportError`, `DependencyMissingError`.
- **Regex stats**: pass a `ring5.StatConfig(name=r"system.cpu\d+.ipc",
  type="scalar", is_regex=True)` instead of a plain name.
- The full application facade stays reachable as `session.api`
  (history, previews, CSV pool, saved configs).
- For long-running processes, `ring5.shutdown()` releases the worker
  pools (they restart transparently on next use).

## The command line

```bash
ring5 doctor                                  # check perl / chrome / xelatex
ring5 parse /path/to/sims -v simTicks -v hostSeconds -o out.csv
ring5 render my_paper -o figs/ --engine matplotlib --format pdf
ring5 upgrade my_paper                        # persist at the current schema
```

`ring5 render` is the reproducibility workflow: it restores a portfolio
saved from the app (or a script) and regenerates every figure file.

## Export formats & external dependencies

| Format | Engine | Needs |
|--------|--------|-------|
| `html` | plotly | nothing |
| `png`, `svg`, `pdf` | matplotlib | nothing |
| `png`, `svg`, `pdf` | plotly | a Chrome-family browser (Kaleido); install with `kaleido_get_chrome` or set `BROWSER_PATH` |
| `pgf` | matplotlib | `xelatex` (e.g. `make install-latex`) |

Parsing requires `perl`. `ring5 doctor` checks all three in an instant.

## Deterministic exports (CI regression)

`deterministic=True` (the CLI default) makes re-exports of the same figure
**byte-identical**, so a checksum is a regression test:

- plotly **PNG** and matplotlib **PGF** are byte-stable as-is;
- plotly **HTML** gets a fixed div id; plotly **SVG/PDF** have their one
  random uid / date stamps normalized;
- matplotlib **PNG/SVG/PDF** are stabilized via `SOURCE_DATE_EPOCH` and a
  fixed `svg.hashsalt`.

The cheapest regression artifact needs no image at all:
`s.render(plot, engine="plotly").to_json()` is deterministic and
hash-seed-proof.
