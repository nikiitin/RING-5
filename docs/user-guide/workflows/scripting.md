---
layout: default
title: Automate with Python and the CLI
parent: Workflows
grand_parent: User Guide
nav_order: 5
permalink: /user-guide/workflows/scripting/
---

# Automate with Python and the CLI

Import only `ring5` in user scripts. The package composes parsing, core services, and rendering
without exposing `src.*` modules as a supported interface. A `Session` owns the data, plots,
and jobs for one analysis; a `Table` owns analysis data; a `FigureSpec` describes a figure.

| I want to… | Start here |
| --- | --- |
| Try every built-in plot with no input files | [Explore the example portfolio]({{site.baseurl}}/user-guide/getting-started/showcase/). |
| Compare repeated runs and reproduce the figures | [Run a complete analysis](#run-a-complete-analysis). |
| Parse my gem5 results into a reusable table | [Parse simulator statistics](#parse-simulator-statistics). |
| Reuse an analysis with different inputs or thresholds | [Run a typed parameter matrix](#run-a-typed-parameter-matrix). |
| Regenerate reports when input files stabilize | [Generate reports](#generate-reports-from-stable-changed-inputs). |
| Look up methods, returns, and error contracts | [Public Python API]({{site.baseurl}}/developer-guide/api-reference/public-python-api/). |

The repository's [complete example scripts](https://github.com/nikiitin/RING-5/tree/main/examples)
include synthetic inputs and are executed by the integration suite. Run the commands below from
the checkout after `make dev`. `PYTHONPATH=.` selects this checkout's package; installed applications
can use `python` with their installed `ring5` package instead. CLI commands assume that the
repository environment is active (`source python_venv/bin/activate`) or that `ring5` is installed
in the current environment.

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

This example needs neither simulator output nor Chrome nor TeX:

```bash
PYTHONPATH=. python_venv/bin/python examples/python/compare_configurations.py
```

It reads `examples/data/repeated_runs.csv`: two benchmarks, two configurations, and three seeds
per group. It writes four reduced rows, normalized values, Matplotlib PDF, interactive Plotly HTML,
a saved portfolio, and a replayed PDF beneath `example-output/comparison/`. Expected ratios are
`1.0` for the baselines, `1.2` for the `mcf` candidate, and `1.5` for the `xalancbmk` candidate.
All example values are synthetic and do not establish a simulator performance result.

The analysis uses these public operations:

```python
import ring5

with ring5.Session() as session:
    raw = session.load("examples/data/repeated_runs.csv")
    reduced = session.reduce_seeds(
        raw,
        categorical_cols=["benchmark", "configuration"],
        statistic_cols=["ipc"],
    )
    normalized = session.shape(reduced, [{
        "type": "normalize",
        "normalizeVars": ["ipc"],
        "normalizerVars": ["ipc"],
        "normalizerColumn": "configuration",
        "normalizerValue": "baseline",
        "groupBy": ["benchmark"],
        "normalizeSd": True,
    }])
    plot = session.create_plot(
        "grouped_bar",
        data=normalized,
        name="IPC relative to baseline",
        config=ring5.FigureSpec(
            x="benchmark",
            group="configuration",
            y_columns=["ipc"],
            ylabel="IPC / baseline (higher is better)",
            extra={"show_error_bars": True},
        ),
    )
    figure = session.render(plot, engine="matplotlib")
    session.export(figure, "example-output/ipc.pdf", deterministic=True)
    session.save_portfolio("IPC comparison")

written = ring5.render_portfolio(
    "IPC comparison", "example-output/replayed", engine="matplotlib", fmt="pdf"
)
```

Reduction calculates means and sample standard deviations in `.sd` columns. Normalization divides
each mean and its `.sd` by its benchmark's baseline mean. These error bars show scaled run
variability; they do not estimate ratio uncertainty or establish statistical significance.
See [Compare configurations]({{site.baseurl}}/user-guide/guides/compare-configurations/) for the
statistical comparison workflow.

`create_plot` returns a registered plot that can be rendered repeatedly through either engine.
`render` returns that engine's native figure. `plot` combines those two calls when one render is
enough. Saving a portfolio retains the data and plot configurations; a recipe retains instructions
to rerun against external input files. The
[portfolio workflow]({{site.baseurl}}/user-guide/workflows/portfolios/) explains that choice.

The complete script isolates its default portfolio storage beneath its output directory. Set
`RING5_DATA_DIR` before starting the process to choose another shared catalog. Saving refuses a
name collision by default; use the script's `--replace-portfolio` only when deliberately replacing
its prior example. Direct API calls use `save_portfolio(..., overwrite=True)` for that decision.

## Parse simulator statistics

The parser example includes two tiny synthetic gem5 runs and requires Perl:

```bash
PYTHONPATH=. python_venv/bin/python examples/python/parse_gem5.py
PYTHONPATH=. python_venv/bin/python examples/python/parse_gem5.py /absolute/path/to/results \
  --variable simTicks --variable system.cpu.ipc --output-dir example-output/my-parser
```

For your own input, pass a directory containing `stats.txt` files and choose existing statistic
names. The script prints the actual columns and writes `measurements.csv`; directory-derived
column names depend on your input layout. It does not assume every results tree provides
`benchmark` or `configuration` columns.

```python
import ring5

with ring5.Session() as session:
    discovered = session.scan("examples/data/gem5", limit=0)
    print([variable.name for variable in discovered.variables])
    parsed = session.parse(
        "examples/data/gem5",
        variables=["simTicks", "system.cpu.ipc"],
        scan_limit=0,
    )
    data = session.load(parsed)
    data.to_csv("measurements.csv")
```

Pass the `ParseResult` to `load`, rather than its CSV path, to retain declared numeric/text types
and source provenance. The default strict workflow reports missing or failed inputs. `scan_limit=0`
discovers every matching file up to the global 10,000-file ceiling; the default parse scan samples
at most ten files. There is no need for a separate `scan` call when the requested names are known:
`parse` resolves them before submitting its owned asynchronous work.

The context manager cancels pending session work and removes temporary parser output. Process-wide
worker pools remain reusable; long-running programs can call `ring5.shutdown()` to release them
early. Use `scan_submit` or `parse_submit` when work should overlap with another application task,
then `job.finalize()` to wait for its result or `job.cancel()` to cancel that handle's work. A
session never deletes temporary output while an already-running parse worker can still write to it.

The optional `strategy="config_aware"` adds `sim_path` and compact, key-sorted `config_json` columns.
Every selected run must include a readable, non-empty `config.ini` beside its statistics file.
The tiny fixtures include these companions, so `parse_gem5.py --strategy config_aware` also runs.

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

The portfolio saved by the API example above can be replayed with explicit error handling:

```python
import ring5

try:
    written = ring5.render_portfolio("IPC comparison", "example-output/replayed")
except ring5.PortfolioError as exc:
    raise SystemExit(f"portfolio render failed: {exc}") from exc
```

Run `print(ring5.doctor(tex_system="lualatex"))` before a PGF export that selects LuaLaTeX. The report
identifies missing Perl, the selected browser, and the selected compiler without making optional
tools essential. `doctor()` defaults to XeLaTeX. Read `report.tex_compiler` for the compiler status.

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

Run the complete recipe example first:

```bash
PYTHONPATH=. python_venv/bin/python examples/python/parameterized_recipe.py
```

It defines and exports a recipe, a runnable Python script, and a notebook under
`example-output/recipe/`. Its scatter plot shows individual IPC/energy observations; it does not
reduce seeds. The two serial cases keep rows with IPC strictly above `0.0` or `1.5`, retaining
12 or seven example rows. This threshold is an exploratory filter rather than an estimator of
configuration performance.

The recipe declares its source, parameters, transformations, plot, and export explicitly:

{% raw %}
```python
import ring5

recipe = ring5.AnalysisRecipe(
    name="Efficiency observations",
    source=ring5.RecipeSource(kind="csv", path="{{input_csv}}"),
    parameters=(
        ring5.RecipeParameter("input_csv", "path"),
        ring5.RecipeParameter("minimum", "number", default=0.0),
    ),
    transformations=({
        "type": "conditionSelector",
        "column": "ipc",
        "mode": "greater_than",
        "threshold": "{{minimum}}",
    },),
    plots=(ring5.RecipePlot(
        name="IPC and energy",
        plot_type="scatter",
        config={"x": "energy_j", "y": "ipc", "color": "configuration"},
    ),),
    exports=(ring5.RecipeExport(
        plot="IPC and energy",
        path="efficiency.html",
        engine="plotly",
        format="html",
    ),),
)

with ring5.Session() as session:
    batch = session.run_analysis_recipe_matrix(
        recipe,
        {
            "input_csv": ["examples/data/repeated_runs.csv"],
            "minimum": [0.0, 1.5],
        },
        output_directory="example-output/matrix",
        max_workers=1,
    )

for case in batch.cases:
    print(case.case_id, case.successful, case.error)
```
{% endraw %}

A matrix is limited to 256 Cartesian cases and 8 concurrent workers. Each case runs in an isolated
session, but the returned cases always follow expansion order. File exports are redirected beneath
`case-NNN-<parameter digest>/` and receive indexed safe names such as `01-ipc.pdf`; concurrent
cases therefore cannot replace each other's files. One case failure does not stop the others, and
`batch.complete`, `completed_cases`, and `failed_cases` summarize the outcome.

Use `run_analysis_recipe_matrix_submit` to place the same work in the session background-job
center. Retrieve its completed `AnalysisRecipeMatrixResult` with `background_job_result`.

For the CLI, save these JSON arrays as `matrix.json`:

```json
{
  "input_csv": ["examples/data/repeated_runs.csv"],
  "minimum": [0.0, 1.5]
}
```

Then run:

```text
ring5 recipe-matrix example-output/recipe/analysis.ring5-recipe.json \
  --matrix matrix.json --output-dir example-output/cli-matrix --workers 1
```

The command prints a versioned JSON summary. It exits with `0` when every case succeeds, `1` when
one or more cases fail, and `2` when the recipe, matrix, or command input is invalid.

## Generate reports from stable, changed inputs

<!--
`uman~ring5.automation.scheduled-reporting.documentation~1`

Covers:
- req~ring5.automation.scheduled-reporting~1

-->

Use a scheduled report when an analysis recipe should become an HTML or PDF report without an
open browser. One invocation is one bounded check, which makes it suitable for cron, a CI timer, or
another scheduler. After running the recipe example above, create `nightly-values.json`:

```json
{"input_csv": "examples/data/repeated_runs.csv"}
```

Then run:

```text
ring5 report-schedule example-output/recipe/analysis.ring5-recipe.json \
  --parameters nightly-values.json \
  --report example-output/reports/nightly.html \
  --state example-output/reports/nightly.state.json \
  --stable-for 30
```

The command fingerprints the recipe's concrete source files. CSV recipes watch their CSV file;
parser recipes watch every matching statistics file and, for the config-aware strategy, each
corresponding `config.ini`. The first changed observation is recorded in the state file. A report
is generated only when the same fingerprint is still present after `--stable-for` seconds. Once
that fingerprint has been reported, later checks return `unchanged` without rewriting the report.
The materialized recipe, report title, format, and destination have a separate configuration
fingerprint, so changing report settings—or removing the output—regenerates a report even when its
source data is unchanged.

Each check prints one versioned JSON result with the outcome `generated`, `unchanged`, or
`waiting_for_stability`. The durable state means separate scheduler processes make the same
decision. For a long-running local watcher, add `--watch --interval 5`; it emits one JSON object per
line. `--max-checks` can bound a watch run.

The report is built in memory with the recipe plots and automatic provenance. RING-5 fingerprints
the sources again before publishing, so an input that changes during generation is not published.
The final report and state are written atomically. Recipe-level exports are deliberately suppressed
in this workflow so an unstable run cannot leave partial side files. Report and state paths must be
different from one another and from every source file.

Python schedulers can perform the same single check:

```python
from pathlib import Path
import ring5

payload = Path("example-output/recipe/analysis.ring5-recipe.json").read_bytes()
with ring5.Session() as session:
    recipe = session.decode_analysis_recipe(payload)
    result = session.run_scheduled_report(
        recipe,
        "example-output/reports/nightly.html",
        values={"input_csv": "examples/data/repeated_runs.csv"},
        stable_for_seconds=30,
    )
    print(result.outcome, result.source_fingerprint)
```

## Use the CLI

### Parse statistics to CSV

<!--
`uman~ring5.cli.parse.documentation~1`

Covers:
- req~ring5.cli.parse~1

-->

```bash
ring5 parse examples/data/gem5 --variable simTicks --variable system.cpu.ipc \
  --output example-output/parsed.csv
```

Repeat `--variable` for every statistic. By default a missing statistic fails the command; pass
`--lenient` to write the available values and report missing names. The requested output is copied
out of the session-owned temporary directory before the command exits.

### Render a portfolio

<!--
`uman~ring5.cli.render.documentation~1`

Covers:
- req~ring5.cli.render~1

-->

Use the portfolio created by the comparison script with the same application-data directory:

```bash
RING5_DATA_DIR=example-output/comparison/workspace \
  ring5 render "Documentation IPC comparison" --out-dir example-output/cli-figures \
  --engine matplotlib --format pdf
```

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
`Session.load` and dataset getters return `Table`. Transformation, comparison, plot-data and report
table arguments require `Table`; operations that produce analysis data return a new `Table`.
Run registered pipeline steps through `Session.shape` or `shape_submit`.

Use `Table.from_rows(...)` for records or `ring5.read_table(...)` for a CSV. For pandas operations
outside the supported table helpers, obtain a defensive copy with `table.frame`, then explicitly
wrap the result with `ring5.Table(frame)` before passing it to a Session data method. Immutable
quality, schema, semantics and accessibility reports also offer an explicit `to_frame()` conversion.

```text
ring5 doctor
ring5 parse STATS_PATH --variable NAME --output FILE
ring5 render PORTFOLIO --out-dir DIRECTORY
ring5 recipe-matrix RECIPE --matrix MATRIX --output-dir DIRECTORY
ring5 report-schedule RECIPE --report FILE [--parameters JSON]
```
