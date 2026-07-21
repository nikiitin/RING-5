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

<!--
`uman~ring5.api.session.documentation~1`

Covers:
- req~ring5.api.session~1

`uman~ring5.ingestion.async-parse.documentation~1`

Covers:
- req~ring5.ingestion.async-parse~1

`uman~ring5.ingestion.async-scan.documentation~1`

Covers:
- req~ring5.ingestion.async-scan~1

`uman~ring5.ingestion.config-aware-strategy.documentation~1`

Covers:
- req~ring5.ingestion.config-aware-strategy~1

`uman~ring5.ingestion.simple-strategy.documentation~1`

Covers:
- req~ring5.ingestion.simple-strategy~1

-->

```python
import ring5

with ring5.Session() as session:
    discovered = session.scan("results/", limit=0)
    assert any(variable.name == "system.cpu.ipc" for variable in discovered.variables)
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

Use `scan_submit`/`parse_submit` when work should overlap with other application tasks. Their
`ScanJob` and `ParseJob` handles own cancellation and finalization. A session never deletes its
temporary output while an already-running parse worker can still write to it.

The optional `strategy="config_aware"` parse mode adds `sim_path` and compact, key-sorted
`config_json` columns. Each run must contain a valid `config.ini` beside its stats file.

## Discover and handle errors

<!--
`uman~ring5.api.registry-discovery.documentation~1`

Covers:
- req~ring5.api.registry-discovery~1

-->

Use `ring5.available_plot_types()` and `ring5.available_shaper_types()` rather than copying registry
inventories. Plot mappings are checked for required keys and referenced columns before a plot is
registered. Public failures inherit from `ring5.Ring5Error`, with narrower types such as
`ParseError`, `PipelineError`, `RenderError`, and `ExportError`.

```python
try:
    written = ring5.render_portfolio("paper-a", "figures/")
except ring5.PortfolioError as exc:
    raise SystemExit(f"portfolio render failed: {exc}") from exc
```

Run `print(ring5.doctor())` before an environment-dependent export. The report identifies missing
Perl, browser, and XeLaTeX dependencies without making optional tools essential.

## Run a typed parameter matrix

<!--
`uman~ring5.automation.batch-matrices.documentation~1`

Covers:
- req~ring5.automation.batch-matrices~1

-->

Use a recipe matrix to run every combination of selected inputs and settings. Matrix keys are
declared recipe parameters and each value is an ordered sequence. RING-5 expands parameters in
recipe declaration order, fills omitted parameters from their defaults, and rejects unknown,
empty, duplicate, or mistyped values before starting work.

```python
with ring5.Session() as session:
    recipe = session.decode_analysis_recipe(recipe_json)
    batch = session.run_analysis_recipe_matrix(
        recipe,
        {
            "input_csv": ["results/base.csv", "results/candidate.csv"],
            "minimum": [0.0, 1.5],
        },
        output_directory="matrix-output",
        max_workers=2,
    )

for case in batch.cases:
    print(case.case_id, case.successful, case.error)
```

A matrix is limited to 256 Cartesian cases and 8 concurrent workers. Each case runs in an isolated
session, but the returned cases always follow expansion order. File exports are redirected beneath
`case-NNN-<parameter digest>/` and receive indexed safe names such as `01-ipc.pdf`; concurrent
cases therefore cannot replace each other's files. One case failure does not stop the others, and
`batch.complete`, `completed_cases`, and `failed_cases` summarize the outcome.

Use `run_analysis_recipe_matrix_submit` to place the same work in the session background-job
center. Retrieve its completed `AnalysisRecipeMatrixResult` with `background_job_result`.

For the CLI, store the matrix as JSON arrays:

```json
{
  "input_csv": ["results/base.csv", "results/candidate.csv"],
  "minimum": [0.0, 1.5]
}
```

Then run:

```text
ring5 recipe-matrix analysis.ring5-recipe.json \
  --matrix matrix.json --output-dir matrix-output --workers 2
```

The command prints a versioned JSON summary. It exits with `0` when every case succeeds, `1` when
one or more cases fail, and `2` when the recipe, matrix, or command input is invalid.

## Use the CLI

### Parse statistics to CSV

<!--
`uman~ring5.cli.parse.documentation~1`

Covers:
- req~ring5.cli.parse~1

-->

Repeat `--variable` for every statistic. By default a missing statistic fails the command; pass
`--lenient` to write the available values and report missing names. The requested output is copied
out of the session-owned temporary directory before the command exits.

### Render a portfolio

<!--
`uman~ring5.cli.render.documentation~1`

Covers:
- req~ring5.cli.render~1

-->

`ring5 render` restores every valid plot in the named portfolio and writes it under `--out-dir`.
Select the engine and format explicitly when a script depends on them.

Run `ring5 COMMAND --help` for current options. `render` uses Matplotlib and PDF by default; Plotly
defaults to HTML. Pass `--no-deterministic` only when byte-stable output is not required.

## Use portable table scripts

<!--
`uman~ring5.api.table.documentation~1`

Covers:
- req~ring5.api.table~1

-->

`ring5.Table` and `ring5.read_table` provide a pandas-independent handle for figure scripts.
`Session.shape`, `reduce_seeds`, `remove_outliers`, `apply_operation`, and `mix_columns` return a
`Table` when given one; plot methods also accept it. Use a DataFrame when the analysis needs pandas
operations outside the supported surface.

```text
ring5 doctor
ring5 parse STATS_PATH --variable NAME --output FILE
ring5 render PORTFOLIO --out-dir DIRECTORY
ring5 recipe-matrix RECIPE --matrix MATRIX --output-dir DIRECTORY
ring5 upgrade PORTFOLIO
```
