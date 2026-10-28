---
layout: default
title: Manage Portfolios
parent: Workflows
grand_parent: User Guide
nav_order: 4
permalink: /user-guide/workflows/portfolios/
---

# Manage portfolios

<!--
`uman~ring5.workspace.application-data-directory.documentation~1`

Covers:
- req~ring5.workspace.application-data-directory~1
-->

A portfolio stores exact typed tables together with plot definitions, shaper pipelines,
parser configuration, and operation history. Use it to reopen or batch-render a RING-5 workspace.
Keep original simulator output and analysis code separately; a portfolio is not a substitute for
research data storage.

| Your task | Go to |
| --- | --- |
| Try an example without data files | [Load the bundled examples](#load-the-bundled-examples) |
| Retain the current browser workspace | [Save and restore in the web application](#save-and-restore-in-the-web-application) |
| Save figures from a script | [Save and restore in Python](#save-and-restore-in-python), then [render every saved plot](#render-every-saved-plot) |
| Replay an analysis on new input | [Save a reusable analysis recipe](#save-a-reusable-analysis-recipe) |
| Transfer a reviewed analysis | [Share a portable analysis bundle](#share-a-portable-analysis-bundle) |

## Load the bundled examples

<!--
`uman~ring5.portfolio.example-catalog.documentation~1`

Covers:
- req~ring5.portfolio.example-catalog~1

-->

On an empty **Data Source** page, select **Load example portfolio**. The application opens
**Manage Plots** with synthetic examples of every built-in chart type. The bundled current-format
portfolio works offline and creates no saved portfolio or revision files. Use **Save Portfolio**
under your own name to retain a copy after editing it. Follow the
[example tour]({{site.baseurl}}/user-guide/getting-started/showcase/) for questions, expected values,
and changes to try.

Scripts use the same built-in resource:

```python
import ring5

with ring5.Session() as session:
    report = session.load_example_portfolio()
    if not report.complete:
        raise RuntimeError(report)
    figure = session.render(session.plots[0], engine="matplotlib")
    session.export(figure, "example-ipc.pdf", deterministic=True)
```

## Document and table contracts

Current portfolios use schema 13 (`version: "13.0"`); analysis recipes use schema 8. Typed workspace
and plot tables preserve native Distribution geometry, omission policy and explicit column roles.
Restoring those tables needs no reparse. Parser recipe replay uses the captured full declaration and
regenerates the same native layout once, without inferring geometry from labels. Unsupported current
document versions and malformed layouts fail before restoration.

## Save and restore in the web application

<!--
`uman~ring5.portfolio.save.documentation~1`

Covers:
- req~ring5.portfolio.save~1

`uman~ring5.portfolio.restore.documentation~1`

Covers:
- req~ring5.portfolio.restore~1

-->

Open **Save/Load Portfolio** and enter a descriptive name under **Save Portfolio**. Names must be
non-empty, at most 120 characters, and cannot contain control characters, path separators,
traversal sequences such as `..`, or a leading dot. Saving from the web application replaces an
existing portfolio with the same exact name, so check **Manage Saved Portfolios** before reusing it.

Saving is also allowed before data is loaded. That creates a configuration-only portfolio for the
current settings and parser state; it does not invent an empty table.

Under **Load Portfolio**, choose a saved name and select **Load Portfolio**. Restoration is
best-effort: compatible data and plots can load even when another item is invalid. Review every
warning before trusting a restored workspace.

## Review the saved environment

<!--
`uman~ring5.portfolio.environment-metadata.documentation~1`

Covers:
- req~ring5.portfolio.environment-metadata~1

-->

Choose a portfolio under **Load Portfolio**, then open **Reproducibility environment** before
restoring it. RING-5 compares the versions recorded when the portfolio was saved with the current
runtime. The table covers RING-5, Python, the operating system and architecture, direct Python
dependencies, Plotly and Matplotlib, and the optional Perl, Chrome, and XeLaTeX tools.

An exact match means every recorded value is the same. A difference is evidence to review, not an
automatic incompatibility verdict. **Not available** means a saved component and the current runtime
provide no version. **Not recorded** means that component is absent from the saved record. RING-5
never substitutes current versions for missing historical provenance.

The environment record intentionally excludes hostnames, usernames, executable paths, and
environment-variable values. Python callers can make the same comparison without restoring the
portfolio. For a saved portfolio named `paper-a`:

```python
import ring5

with ring5.Session() as session:
    current = session.environment_metadata()
    comparison = session.compare_portfolio_environment("paper-a")
    for difference in comparison.differences:
        if difference.status == "changed":
            print(difference.component, difference.recorded, difference.current)
```

Portfolios are JSON files in the application's `portfolios/` directory:

- A source checkout stores application data under `<checkout>/.ring5/`.
- An installed package uses the Linux user-data directory, normally `$XDG_DATA_HOME/ring5/` or
  `~/.local/share/ring5/` when `XDG_DATA_HOME` is unset.
- `RING5_DATA_DIR` overrides the application data root in either case; portfolios then live under
  `$RING5_DATA_DIR/portfolios/`.

Set the override before starting the application or Python process when you need isolated or
backed-up storage. The read-only bundled example is packaged with RING-5 and is independent of this
saved-portfolio directory.

## Check integrity and authenticate a portfolio

<!--
`uman~ring5.portfolio.signed-manifests.documentation~1`

Covers:
- req~ring5.portfolio.signed-manifests~1

-->

Every newly saved portfolio contains SHA-256 checksums for the complete document and for three
reviewable areas: **Inputs** covers embedded data and source/parser provenance; **Configuration**
covers workspace settings, histories, plot definitions, and pipelines; **Outputs** covers each
plot's processed data and semantics. Open **Portfolio integrity** before loading to see whether each
area still matches. RING-5 blocks restoration when any checksum differs or the manifest is invalid.

The status wording deliberately separates integrity from authenticity:

| Status | Meaning |
| --- | --- |
| Checksums match — unsigned | Content is unchanged since the checksums were created; its author is not authenticated. |
| Signature needs secret | Content is unchanged and carries a signature, but RING-5 has not authenticated it yet. |
| Checksums and signature verified | Content is unchanged and the supplied shared secret verifies its HMAC-SHA-256 signature. |
| Missing or invalid manifest | Required manifest data is absent or malformed; restoration is blocked. |
| Modified content or invalid signature | Content checks or signature verification fail; restoration is blocked. |

To sign from the web application, select **Sign integrity manifest**, give the key a non-secret ID,
and enter the shared secret. The secret is used only for that save and is not written into the
portfolio. When loading a signed portfolio, enter the matching secret; the web application will not
restore it as though it were authenticated without that check.

Python callers can enforce the same trust policy. Keep the secret outside source control, logs, and
the portfolio itself:

```python
import os
import ring5

secret = os.environ["RING5_PORTFOLIO_SIGNING_SECRET"]

with ring5.Session() as session:
    session.save_portfolio(
        "paper-a",
        signing_key=secret,
        signing_key_id="lab-key-2026",
    )

with ring5.Session() as session:
    evidence = session.verify_portfolio("paper-a", signing_key=secret)
    if evidence.status != "signature-valid":
        raise RuntimeError(evidence.message)
    session.load_portfolio(
        "paper-a",
        signing_key=secret,
        require_signature=True,
    )
```

`require_signature=True` is the anti-downgrade control: use it whenever the workflow expects an
authenticated portfolio. Without that external policy, a checksum-only portfolio remains
restorable because signatures are optional. HMAC uses a shared secret, so it authenticates only
among parties that protect that secret; it is not a public-key or identity certificate.

## Share a portable analysis bundle

<!--
`uman~ring5.portfolio.portable-bundles.documentation~1`

Covers:
- req~ring5.portfolio.portable-bundles~1

-->

Choose a saved portfolio, open **Portable analysis bundle**, and select **Prepare portable bundle**.
The download always contains the exact portfolio, a source-provenance manifest, captured environment
metadata, and pinned Python package requirements. You can also select one existing reusable dataset
snapshot. The result is a single `.ring5-bundle` file.

To review a received bundle, open **Data Source**, choose the file, and inspect its source count,
requirements, optional snapshot, generated results, and portfolio integrity status. RING-5 verifies
the archive structure, every member checksum, the nested dataset snapshot, and the portfolio
manifest before enabling restoration. A signed portfolio requires its shared secret. Restoration
changes only the workspace; included snapshot and result files are not silently written to server
storage.

Python can attach generated result bytes and read every artifact without restoring it. This
example assumes `paper-a`, the `exact-input` dataset snapshot, `figures/ipc.svg`, and `report.html`
already exist:

```python
from pathlib import Path

import ring5

with ring5.Session() as session:
    bundle = session.export_portfolio_bundle(
        "paper-a",
        snapshot_name="exact-input",
        results={
            "figures/ipc.svg": Path("figures/ipc.svg").read_bytes(),
            "report.html": Path("report.html").read_bytes(),
        },
        signing_key="shared transfer secret",
        signing_key_id="lab-transfer-2026",
    )

with ring5.Session() as session:
    info = session.inspect_portfolio_bundle(bundle)
    contents = session.read_portfolio_bundle(
        bundle,
        signing_key="shared transfer secret",
        require_signature=True,
    )
    print(info.result_names)
    report = session.restore_portfolio_bundle(
        bundle,
        signing_key="shared transfer secret",
        require_signature=True,
    )
```

Result names are safe paths relative to the bundle's `results/` directory. Bundle input, expanded
members, file count, and total result bytes are bounded. Bundles are data-only ZIP archives: they do
not contain or execute scripts, notebooks, package installers, or source datasets. Source manifests
record provenance paths and embedded-data checksums; they do not copy external simulator output.

## Compare saved portfolio versions

<!--
`uman~ring5.portfolio.history-diff.documentation~1`

Covers:
- req~ring5.portfolio.history-diff~1

-->

Every successful save retains an immutable version. Under **Manage Saved Portfolios**, expand a
portfolio to see its versions in save order, their source mode, plot count, current status, and a
short content ID. Choose an earlier and later version, then select **Compare saved versions**.

The comparison groups field-level changes into **Data sources**, **Pipelines**, **Plots**, and
**Figure settings**. Embedded table values are deliberately excluded: changing only stored table
values does not expose those values in this report. Comparisons stop after 5,000 field changes and
show a warning when that safety limit is reached. Deleting a portfolio also deletes all of its
retained versions.

Python callers receive immutable `PortfolioRevisionInfo`, `PortfolioDiff`, and
`PortfolioDiffEntry` records. A retained version can be restored for inspection without making it
the current saved version. After saving `paper-a` at least twice:

```python
import ring5

with ring5.Session() as session:
    versions = session.list_portfolio_revisions("paper-a")
    changes = session.compare_portfolio_revisions(
        "paper-a",
        versions[-2].revision_id,
        versions[-1].revision_id,
    )
    for change in changes.entries:
        print(change.section, change.path, change.before, change.after)

    report = session.restore_portfolio_revision("paper-a", versions[-2].revision_id)
```

Opening history records the current saved portfolio if its revision is not already retained.
Revision IDs are SHA-256 checksums of the exact saved JSON bytes; RING-5 verifies the
checksum before loading or comparing a version.

## Review restoration outcomes

<!--
`uman~ring5.portfolio.partial-report.documentation~1`

Covers:
- req~ring5.portfolio.partial-report~1

-->

Restoration handles data, parser variables, and plots independently. The web application reports
data errors, skipped plots, and malformed parser-variable entries before rerunning. Python callers
receive the same details in `RestoreReport`; `report.complete` is false when any item was lost.

## Inspect and delete saved portfolios

<!--
`uman~ring5.portfolio.manage.documentation~1`

Covers:
- req~ring5.portfolio.manage~1

-->

**Manage Saved Portfolios** lists each stored snapshot. Expanding one and selecting **Delete
portfolio and saved versions** removes that named portfolio and its retained history. Keep a
separate backup when a snapshot cannot be recreated.

## Save a reusable analysis recipe

<!--
`uman~ring5.portfolio.analysis-recipes.documentation~1`

Covers:
- req~ring5.portfolio.analysis-recipes~1

-->

Open **Analysis recipes** on the **Save/Load Portfolio** page. The **Save current** tab captures the
active CSV or parser source, parser-variable definitions, every plot configuration, and each
plot's ordered shaper pipeline. Source paths are runtime parameters by default, so the same recipe
can run against another compatible input without editing its JSON.

Select **Download each current plot when the recipe runs** to store an engine, format,
deterministic output setting, and parameterized output path for every plot. Recipe names do not
overwrite silently; select **Replace a saved recipe with this name** only when replacement is
intentional. The **Saved** tab shows the source, parameter, transformation, plot, and download
counts and downloads a portable `ring5.analysis-recipe` JSON file. The **Import** tab validates
that versioned file before saving it. Recipe JSON is limited to 512 KiB and does not embed dataset
rows. Recipe schema 8 stores complete runnable `StatConfig` payloads; incomplete parser editor
drafts remain savable in portfolios but cannot become an executable recipe. To construct a parser
recipe in Python, serialize the public dataclass with `dataclasses.asdict`:

```python
from dataclasses import asdict
import ring5

stat = ring5.StatConfig(
    name="IPC", source_name="system.cpu.ipc", type="scalar",
    params={"source_type": "scalar"},
)
source = ring5.RecipeSource(
    kind="parser",
    path="simulations",
    variables=(asdict(stat),),
)
```

Python can construct recipes with shared transformations and arbitrary typed parameters as well as
run recipes captured by the web application. For this example, `results/candidate.csv` must contain
`benchmark` and numeric `ipc` columns:

```python
import ring5

recipe = ring5.AnalysisRecipe(
    name="IPC paper",
    parameters=(
        ring5.RecipeParameter("input_csv", "path"),
        ring5.RecipeParameter("output_dir", "path", default="figures"),
    ),
    source=ring5.RecipeSource(kind="csv", path="{{input_csv}}"),
    plots=(
        ring5.RecipePlot(
            name="IPC",
            plot_type="bar",
            config={"x": "benchmark", "y": "ipc"},
        ),
    ),
    exports=(
        ring5.RecipeExport(
            plot="IPC",
            path="{{output_dir}}/ipc.pdf",
            engine="matplotlib",
            format="pdf",
        ),
    ),
)

with ring5.Session() as session:
    session.save_analysis_recipe(recipe)
    result = session.run_analysis_recipe(
        "IPC paper",
        {"input_csv": "results/candidate.csv"},
    )
    print(result.exported_paths)
```

Parameter types are `string`, `integer`, `number`, `boolean`, and `path`. A placeholder occupying a
whole value preserves its declared type; a placeholder embedded in text is formatted as text.
Execution validates all parameters, shapers, and plot mappings before replacing the session's
plots. Parser recipes use the normal owned scan and parse lifecycle. Failures use `RecipeError` or
the narrower scan, parse, pipeline, plot-validation, and export errors. Local recipes are stored
under `analysis_recipes/` in the application data directory described above; `RING5_DATA_DIR`
overrides that root.

## Take a recipe into Python or Jupyter

<!--
`uman~ring5.automation.script-notebook-export.documentation~1`

Covers:
- req~ring5.automation.script-notebook-export~1

-->

Open **Analysis recipes**, select **Saved**, and choose **Download Python script** or **Download
Jupyter notebook**. Both downloads contain the exact validated recipe shown in the browser: its
source, typed parameters, transformations, plots, and file exports. They do not depend on private
`src.*` modules and do not save a second recipe behind the scenes.

The Python file is ready for a terminal wherever the `ring5` package and the recipe's input files
are available. Run `python downloaded-recipe.py --help` to see one typed option per parameter, then
pass any required paths or overrides. It prints a compact JSON summary with the row count, columns,
plots, and written files when the run succeeds.

The notebook begins with a plain-language recipe summary, followed by setup, parameters, and run
cells. Replace every parameter value marked `REQUIRED`, edit defaults when needed, and run the cells
from top to bottom. No `nbformat` package is needed to create the download; the file uses the
standard Jupyter notebook v4 JSON format.

To generate the same byte-stable artifacts from Python, first save the portable recipe JSON as
`downloaded.ring5-recipe.json` using **Download recipe JSON** in **Analysis recipes → Saved**.
The script below reads that validated document and writes runnable Python and notebook files:

```python
from pathlib import Path

import ring5

recipe_path = Path("downloaded.ring5-recipe.json")
with ring5.Session() as session:
    recipe = session.decode_analysis_recipe(recipe_path.read_bytes())
    script = session.export_analysis_recipe_script(recipe)
    notebook = session.export_analysis_recipe_notebook(recipe)

Path("reproduce.py").write_bytes(script)
Path("reproduce.ipynb").write_bytes(notebook)
```

`decode_analysis_recipe` only validates and returns the immutable recipe. It does not execute or
persist it. Generated artifacts validate their embedded recipe again immediately before execution
and run it through `Session.run_analysis_recipe`, so their behavior stays aligned with the supported
public API.

## Save and restore in Python

<!--
`uman~ring5.portfolio.safe-overwrite.documentation~1`

Covers:
- req~ring5.portfolio.safe-overwrite~1

-->

```python
import ring5

with ring5.Session() as session:
    # results.csv has benchmark and numeric ipc columns.
    data = session.load("results.csv")
    session.create_plot(
        "bar",
        data=data,
        config=ring5.FigureSpec(
            x="benchmark", y_columns=["ipc"], title="IPC by benchmark"
        ),
        name="IPC by benchmark",
    )
    session.save_portfolio("paper-a")

with ring5.Session() as session:
    report = session.load_portfolio("paper-a")
    if not report.complete:
        raise RuntimeError(report)
```

`Session.save_portfolio` refuses to overwrite by default. Pass `overwrite=True` only when replacing
the named snapshot is intentional. `load_portfolio` returns a `RestoreReport` with data, plot, and
parse-variable outcomes. Every newly saved schema-13 portfolio captures its execution environment
and an integrity manifest. Workspace data and each plot’s source and processed tables retain
their exact supported values, dtypes, axes and attributes. Empty tables remain present tables.
Unsupported objects or cyclic metadata are rejected before a save replaces retained files.

## Render every saved plot

<!--
`uman~ring5.portfolio.batch-replay.documentation~1`

Covers:
- req~ring5.portfolio.batch-replay~1

-->

```python
import ring5

written = ring5.render_portfolio(
    "paper-a",
    "figures/",
    engine="matplotlib",
    fmt="pdf",
)
```

The CLI provides the same batch operation:

```bash
ring5 render paper-a --out-dir figures/ \
  --engine matplotlib --format pdf
```

Rendering defaults to deterministic output, Matplotlib PDF, or Plotly HTML. The command stops with a
typed error when a plot cannot be restored, rendered, or exported.
