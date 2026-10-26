---
layout: default
title: Public Python API
parent: Stable Interfaces
grand_parent: Developer Guide
nav_order: 1
permalink: /developer-guide/api-reference/public-python-api/
---

# Public Python API

`ring5` is the supported headless surface. Public names are exported from `ring5/__init__.py`. The
tests marked `public_api` enforce exact line and branch coverage for the package (`make test-api`).

## Workspace

<!--
`uman~ring5.api.plot-validation.documentation~1`

Covers:
- req~ring5.api.plot-validation~1

`uman~ring5.ingestion.scan-limits.documentation~1`

Covers:
- req~ring5.ingestion.scan-limits~1

-->

`ring5.Session` owns one headless workspace. It can submit or complete parsing, load CSV data, run
manager operations and shaper pipelines, create and render plots, export figures, and save or
restore portfolios. Use it as a context manager so pending session work and temporary parser output
are released.

`Session.scan_submit` returns an owned `ScanJob`; `Session.scan` waits and returns `ScanResult`.
Likewise, `parse_submit` returns `ParseJob` and `parse` returns `ParseResult`. A job can be
cancelled without touching work from another handle. A finalized result owns `output` (the explicit
`ParsedOutput` descriptor), its immutable `source_context`, and missing variable names as a tuple.
Use `session.load(result)` to retain exact numeric/text semantics and source provenance.
`result.csv_path` is the derived external exchange location; `session.load(result.csv_path)` uses
ordinary CSV inference/null policy. The descriptor's SHA-256 binds schema meaning and CSV bytes.
The public typed backend constructors and `resolve_parsed_output`/`publish_parsed_output` helpers
are documented in the [parser extension guide]({{ site.baseurl }}/developer-guide/extension-guides/adding-a-parser/).

Use `ring5.StatConfig` for explicit runnable parser settings. Configuration fields and `params`
use snake_case; `repeat` is a positive integer, `entries` and `statistics` are separate text lists,
and `source_name` preserves an output alias without replacing the simulator statistic. Every runnable
configuration declares `params.source_type`, a compatible source contract before output reinterpretation.
`ScannedVariable` requires `source_evidence` and `SourceInstance` records containing exact source names
and numeric display coordinates. Evidence is resolved or explicitly ambiguous; ambiguous sources have
no output suggestion (`type=None`) and require an explicit runnable `StatConfig`. Observed entry labels
do not supply native geometry. Numeric patterns require these current scan records;
`params.selected_sources` selects concrete names once at submission. An explicit empty selection
remains an unfinished draft. Scalar-source vector entries derive from instance coordinates, so they
do not accept caller-provided `entries`. Invalid
configuration raises `ParseError`; dictionary and duck-object execution routes are unsupported.
Histogram `statistics_only=True` extracts only configured summaries and retains missing summaries
as NaN. Saved editor drafts remain editable, while jobs and analysis recipes require runnable
configurations.

Native frequency requests declare `params={"source_type": "distribution", "minimum": 0.25,
"maximum": 1.25, "bucket_size": 0.5, "zero_policy": "missing"}`. `"nozero"` is an explicit
producer omission guarantee for present compatible observations. Full native geometry is independent
of rounded printed labels; summary-only extraction needs no grid.

Custom parser declarations use `DistributionGeometry`, `DistributionColumn`,
`NativeDistributionLayout` and `OpaqueDistributionLayout`. `ParsedVariableSchema` and
`ParsedVariableResult` require the keyword `layout`, including `layout=None` for ordinary output.
A layout binds exact numeric physical columns; full native layouts include every allocated slot,
both tails and optional summaries. Opaque layouts retain literal selected labels without geometry.
See [Add a Parser]({{site.baseurl}}/developer-guide/extension-guides/adding-a-parser/) for invariants.


Declared Session data methods use `ring5.Table`. `load`, `load_import`, dataset getters, joins,
appends and comparisons return independently owned tables. Transformation, quality, schema,
semantics, comparison and plot-data arguments require tables. Both operands of `compare` and
`compare_statistics` are tables; `create_report` accepts `Mapping[str, Table]` for its display tables.
Methods that return metadata, reports, jobs, figure handles or exported bytes retain those result
types.

`Table.from_rows` constructs a table without pandas. `Table(frame)` and `table.frame` are explicit
pandas entry and exit points that copy their data, including nested object cells and semantic
metadata. `Session.api` remains an advanced Core interoperability boundary with its documented
pandas-based service and state contracts. It is separate from the declared Session data methods.

`Session.background_jobs` returns immutable `BackgroundJobInfo` snapshots for tracked scan, parse,
transformation, and export work. `shape_submit` and `export_submit` add retryable work and retain
successful results for `background_job_result`; parser results remain on their original handles.
Successful transformation jobs publish a `Table` through `background_job_result`.
`cancel_background_job` reports a running cancellation request as `cancelling`,
`retry_background_job` reuses the stable job identity with a higher attempt, and
`dismiss_finished_background_jobs` releases terminal records and retained results.

`Session.parser_playground_submit` returns a `ParserPlaygroundJob` that runs the registered parser
against at most three lexically selected files. Finalization returns `ParserPlaygroundResult`
without retaining a CSV or changing workspace data. The result exposes exact sampled paths, output
cells, missing variables, diagnostics, and whether the configuration is ready for a full parse.

`Session.compare` aligns baseline and candidate rows by unique key columns and emits long-form
metric results. Directions and non-negative tolerances can be global or keyed by metric. Percentage
and absolute threshold modes are supported. Missing keys and non-finite values remain in the result;
invalid columns, duplicate keys, and invalid options raise `DataValidationError`.

`Session.annotate_comparison` copies a threshold-comparison result and adds plot-ready labels,
signed changes, outcome text, accessible symbols, Plotly marker names, and color-blind-safe colors.
It accepts and returns `ring5.Table`. Callers can follow the stored threshold mode or explicitly select
percentage or absolute changes; malformed comparison schemas raise `DataValidationError`.

`Session.compare_statistics` accepts repeated observations and optional grouping columns. It
returns Welch confidence intervals and p-values, Hedges' g, deterministic bootstrap estimates and
intervals, and sample-quality warnings. Confidence, alpha, bootstrap count, seed, and the
small-sample threshold are explicit parameters. Invalid options raise `DataValidationError`.

`Session.profile_data` returns an immutable `DataQualityReport` for a `ring5.Table`.
Dataset counts remain scalar fields; `columns` contains immutable `ColumnQuality` records and
`to_frame()` creates a new DataFrame for display or export. Optional expected types validate finite
values without conflating invalid values with missing cells.
`DatasetSemantics`, `DatasetSchemaContract`, `SchemaValidationReport`, and `AccessibilityReport`
also retain their explicit `to_frame()` conversions for display or external pandas work.

`ColumnContract` declares required presence, data type, nullability, finite numeric bounds, and
accepted scalar values. `DatasetSchemaContract` groups unique column rules and controls unexpected
columns. `Session.infer_schema_contract` returns a conservative editable starting point;
`Session.validate_schema` returns an immutable `SchemaValidationReport` and never coerces its input.
`ColumnContract.semantic_label` and `ColumnContract.unit` can also declare reader-facing metadata.
`Session.apply_semantics`, `inspect_semantics`, and `convert_unit` retain and transform that metadata
without mutating caller data. Missing plot labels are inferred from it for both render engines;
explicit figure labels take precedence.
Each `SchemaViolation` includes a rule, column, affected-row count, and at most ten row positions.

`Session.add_dataset` retains a defensive copy in a named, in-memory workspace and returns a
`DatasetInfo`. `list_datasets`, `get_dataset`, `select_dataset`, and `remove_dataset` manage that
workspace. Dataset getters return an owned `Table`. `compare_datasets` leaves both sources
unchanged; `join_datasets` and `append_datasets` store their result under a separate name and return
a table. The selected dataset supplies the active plot, transformation and portfolio workspace.

`Session.dataset_lineage` returns immutable `DatasetLineage` and `DatasetRevision` records with
operation labels, source and parent ancestry, content fingerprints, and the current undo/redo
state. `get_dataset_revision` inspects a defensive snapshot. `undo_dataset`, `redo_dataset`, and
`restore_dataset_revision` change the current state without mutating historical snapshots. Lineage
is session-owned and is cleared with the named workspace; portfolio persistence is not implied.

`Session.diagnose_join` returns immutable `JoinDiagnostics` for an explicit key relationship,
including duplicate rows and groups on each side, unmatched input rows, and matched distinct keys.
`join_datasets_validated` repeats that validation immediately before joining, refuses incompatible
cardinality without storing output, and returns `(Table, JoinDiagnostics)` on success.

`Session.save_dataset_snapshot` persists the selected, active, or explicitly named dataset in a
versioned non-executable archive. `list_dataset_snapshots` reads immutable `DatasetSnapshotInfo`
metadata without decoding table payloads. `load_dataset_snapshot` verifies the compressed payload
checksum and the reconstructed dataframe fingerprint before retaining it as a named dataset;
`delete_dataset_snapshot` removes one local cache entry. Snapshot storage follows `RING5_DATA_DIR`,
so separate processes can deliberately share the same catalog.

`AnalysisRecipe`, `RecipeSource`, `RecipeParameter`, `RecipePlot`, and `RecipeExport` define the
versioned automation contract. `Session.capture_analysis_recipe` derives source/parser provenance,
plots, and per-plot pipelines from live session state. `save_analysis_recipe`,
`list_analysis_recipes`, `load_analysis_recipe`, and `delete_analysis_recipe` manage the local
catalog without silent replacement. `export_analysis_recipe` and `import_analysis_recipe` use
deterministic bounded JSON. `materialize_analysis_recipe` resolves strict typed placeholders without
side effects; `run_analysis_recipe` loads or parses the source, applies shared and per-plot shapers,
validates mappings, replaces the session plots, and writes declared exports. Storage and validation
failures raise `RecipeError`; execution retains narrower parser, pipeline, plot, and export errors.
`decode_analysis_recipe` validates portable JSON without persisting it.
`export_analysis_recipe_script` and `export_analysis_recipe_notebook` generate deterministic,
documented artifacts that embed that canonical JSON and perform application work only through the
supported `ring5` package.
`run_analysis_recipe_matrix` executes at most 256 Cartesian cases in isolated sessions with a
caller-selected bound of one through eight workers. It returns ordered `AnalysisRecipeMatrixCase`
records and rewrites exports beneath stable case directories. `run_analysis_recipe_matrix_submit`
exposes the same result through the session-owned background-job lifecycle.

`Session.list_portfolio_revisions` returns checksum-verified `PortfolioRevisionInfo` records in
save order. `compare_portfolio_revisions` returns a bounded `PortfolioDiff` whose entries cover
source provenance, pipelines, plot definitions, and appearance settings but never embedded table
rows. `restore_portfolio_revision` restores one retained version without changing the saved current
version. Storage, checksum, and identifier failures use `PortfolioError`; unsupported schemas use
`PortfolioVersionError`.

`scan_limit=0` means exhaustive variable discovery up to the global 10,000-file ceiling; a positive
value is an exact sample cap. A scan with any failed files raises `ScanError` at the public boundary;
pass `strict=False` to `ScanJob.finalize` or `Session.scan` only when a documented partial result is
acceptable. Parser worker, aggregate resource, pattern expansion, and ten-minute batch timeout
failures are wrapped as `ParseError`.

The `config_aware` parser strategy adds deterministic `sim_path` and `config_json` columns. It
requires a readable, non-empty `config.ini` beside every selected stats file. Gem5 scalar-name
patterns, conventional distributions, range histograms, and pipe-delimited one-line histograms are
all supported by the public parse workflow.

`create_plot` registers a plot and `render` renders it. `plot` performs both. Plot identifiers come
from `ring5.available_plot_types()`. Scripts and saved configurations use those exact identifiers. Mapping configurations are validated before registration for required fields,
field types, and referenced columns. Every downstream engine failure is normalized to `RenderError`.
`ring5.available_shaper_types()` provides the equivalent registry for pipelines.
Run registered transformations through `Session.shape` or `shape_submit` with
`Sequence[Mapping[str, object]]`; the pipeline validates each exact registered definition before
execution. `ring5.shapers` exposes the plugin `Shaper` and `ShaperDefinition` types, registration,
and discovery.

`Session.drill_down` returns a public `DrillDownResult` with its plot identifier, exact filters and
an owned `rows: Table` snapshot. `row_count` and `columns` summarize those rows. This projection
preserves the shared plot and native figure handles used by rendering and dashboard operations.

Figures returned by `Session.render` remain usable after plot invalidation, replacement, workspace
reset or Session context exit. Matplotlib render managers are deregistered without clearing artists,
so retained figures remain exportable and unrelated pyplot figures remain independent.

## Figure configuration and export

### Annotations and web shapes

<!--
`uman~ring5.figure.shapes-annotations.documentation~1`

Covers:
- req~ring5.figure.shapes-annotations~1

-->

Typed figure configuration serializes text annotations with data or axes/panel-fraction (`paper`)
coordinates, optional arrows, font family, and multiline alignment. `x_shift_pixels` and
`y_shift_pixels` translate the complete annotation and arrow after resolving those coordinates;
positive values move right and up. These logical pixels use the figure's initial rendering scale,
so a Matplotlib export at twice the DPI doubles the display displacement along with the figure.
An empty annotation font family inherits the figure family. Stack-total offsets use this pixel
contract in both rendering engines. In the web application, editable line, circle, and rectangle
shapes are Plotly layout shapes and remain Plotly-specific.
The [shape editor]({{site.baseurl}}/user-guide/reference/settings/#edit-shapes) preserves literal
coordinates and native defaults, with an explicit number/text choice for edits.

### Typed FigureSpec

<!--
`uman~ring5.api.figure-spec.documentation~1`

Covers:
- req~ring5.api.figure-spec~1

-->

`ring5.FigureSpec` is an immutable typed common figure configuration. It covers data mappings,
dimensions, axes, grouping, legends, reference lines, and dual-axis options. `LegendOpts`,
`ReferenceLineOpts`, and `DualAxisOpts` are immutable values too. Constructor sequences and nested
mappings are owned immutable snapshots; later edits to their source objects cannot change the
specification. Unsupported objects and cycles raise ordinary configuration validation errors.
Immutable NumPy real, boolean and text scalars from explicit pandas work retain their exact values;
mutable arrays, opaque objects, void scalars and custom scalar subclasses are rejected.

The `extra` mapping carries supported flat configuration keys and takes precedence over typed
fields. `to_config()` returns a fresh mutable mapping with the same canonical editable format used
by the web interface and saved plots. `create_plot` and `plot` accept either a `FigureSpec` or that
configuration mapping. Existing raw mappings retain their exact settings and renderer defaults.
`to_config(plot_type="heatmap")` applies the built-in heatmap's contextual field admission;
`Session.create_plot` supplies this context automatically. Heatmaps use `color_palette`,
`reverse_colorscale` and `show_values`. Plugin-owned configurations and typed heatmap trace
colorscales keep their separate contracts.

Per-series overrides use `series_styles`, a mapping from original text series names to style mappings.
Display names use `legend_labels`, such as `{"ipc": "Instructions per cycle"}`. Set both mappings
through `FigureSpec.extra` or the editable configuration mapping. Styles and ordering keep using
`"ipc"` after the rename; repeated or empty display labels preserve each source series. Rendering
returns the selected engine's native figure. Source-to-native associations remain internal and
are not required to export that fully styled figure.

Its `pattern` field is a string: empty, `/`, `\`, `x`, `-`, `|`, `+`, `.`, `o`, `O`, or `*`.
Both native engines render this vocabulary. Plotly uses native SVG pattern paths for the
circle/star forms. An omitted `pattern` preserves the trace or theme hatch; an explicit empty
string selects Solid and clears it. Default stripe patterns apply before explicit series overrides.
Typed renderer styles express absence with `hatching_pattern=None` and Solid with `""`.
Other plugin-owned style fields are preserved. Recipe save/load retains parameter placeholders;
materialization validates the resolved pattern value before execution.

Legend font sizes retain fractional point values through both native engines and typed figure
round trips. `DualAxisOpts.legend` configures the separate right-axis legend; numbered mappings
use the available secondary or tertiary style independently. Raw mappings use `legend2_*` for
the separate right legend and `anchor_x`/`anchor_y` in every legend tier. Explicit `bgalpha`
replaces opacity encoded in `bgcolor`; omitting it preserves an RGBA color's embedded opacity
and each native renderer's default for opaque colors. Plotly preserves RGB/HSL/HWB,
Lab/LCh/OKLab/OKLCh component precision when applying this override. Its current Python validator
cannot encode per-legend opacity for `color(profile ...)` or resolve DDK `var(...)` colors.
Those forms remain accepted without `bgalpha`; requesting the override raises `RenderError`
and asks for a concrete supported color. Matplotlib's static projection accepts named,
hexadecimal, RGB and HSL colors; convert other color spaces before using that engine.
Legend orientations use exactly `horizontal` or `vertical` in every tier. Flat
`legend_xanchor`/`legend_yanchor` keys and their secondary/tertiary equivalents are rejected;
Plotly relayout events retain their native dotted wire names and decode to the canonical keys.

### Public coordinates and decorations

<!--
`uman~ring5.api.figure-decorations.documentation~1`

Covers:
- req~ring5.api.figure-decorations~1

-->

`grouped_bar_coordinates` exposes engine-independent grouped-bar geometry. `FigureDecorations`
applies supported post-render changes to Matplotlib figures, including labels, callout arrows,
axis limits, ticks, legends, and spines. Scripts use both without importing `src.*` modules.

`export_file` and `export_bytes` infer the engine from the figure object. `Session.export` delegates
to the same boundary. Unsupported formats raise `ExportError`; missing optional executables raise
`DependencyMissingError`.

## Portfolio replay and lifecycle

<!--
`uman~ring5.api.process-lifecycle.documentation~1`

Covers:
- req~ring5.api.process-lifecycle~1

-->

`Session.environment_metadata` captures the current runtime without machine identity or paths, and
`Session.compare_portfolio_environment` compares it with a saved portfolio before restoration.
`Session.preview_import` inspects a bounded delimited source without mutating state; its immutable
`ImportPreview` records detected format, inferred and corrected types, row outcomes, and a source
digest. `Session.load_import` verifies that digest and loads only the reviewed accepted rows.
`Session.create_report` captures selected plots or dashboards, bounded tables, narrative,
provenance, and that environment in an immutable `AnalysisReport`. `report_bytes` and
`export_report` generate deterministic self-contained HTML or multi-page PDF output.
`ring5.render_portfolio` restores and exports every plot. `ring5.doctor` reports parser and export
dependencies. `ring5.shutdown` releases process-wide worker pools early; they otherwise register
process-exit cleanup and restart on later use.

### Dependency preflight

`ring5.doctor(*, tex_system="xelatex")` returns a `DoctorReport` with `perl`, `chrome`, and
`tex_compiler` statuses. The compiler choice uses the same exact `xelatex`, `pdflatex`, or `lualatex`
identifiers as PGF export; unsupported choices raise `ExportError`. `tex_compiler.name` identifies
the selected compiler. `all_found` includes optional tools; `essential_found` checks only Perl.

Each `DependencyStatus` records `name`, executable availability in `found`, its selected `path`,
`needed_for`, and `install_hint`. An unavailable explicit browser choice retains its requested
literal in `path`. Every present `BROWSER_PATH` is authoritative, including an empty value; no
alternate browser is selected after that choice fails. An executable command name resolves through
`PATH`. Preflight runs no browser, compiler, or version subprocess. Saved environment capture
separately records bounded version facts for the same selected executable and all supported TeX
compilers, without storing their paths.

The CLI `ring5 install-chrome [--cache-dir PATH]` installs the reviewed Chrome for Testing Stable
release without launching it. Standard output contains only its absolute executable path; set
`BROWSER_PATH` to that path before starting the process that exports figures. Operational failures
use `Ring5Error` and CLI exit code 2. Installation and browser selection remain separate operations;
see the [installation instructions]({{site.baseurl}}/user-guide/getting-started/installation/#install-chrome-for-plotly-static-exports).

## Errors

<!--
`uman~ring5.api.typed-errors.documentation~1`

Covers:
- req~ring5.api.typed-errors~1

-->

Catch the narrow error from `ring5.errors` when recovery differs. All supported operational errors
inherit `Ring5Error`. `ScanError` covers empty, failed, or incomplete scans; `ParseError` covers
submission, resource-limit, worker, timeout, and assembly failures. Public boundaries preserve the
original failure as `__cause__` where wrapping adds API context. `JobError` covers invalid
background-job identifiers and lifecycle operations.

When adding a public name, export it lazily where appropriate, document parameters and exceptions,
add a `public_api` contract test, keep `make test-api` at 100%, and update the User Guide.

Session operations translate expected domain failures into the documented `ring5.errors` types.
Python configuration constructors use ordinary `TypeError` and `ValueError` validation. Malformed
or duplicate plugin registration raises `PipelineError`. Registered transformations run through
`Session.shape` or `shape_submit`; execution failures use a typed `PipelineError` with step
information where available.

Portfolio restore replaces the existing workspace, clears transient previews and named-data
history, and reports partial restoration failures. Parser strategy and simulator are retained;
serialized portfolios must declare both fields. Unit conversion also scales a metric's `.sd`
companion by the absolute unit scale, without applying affine offsets to uncertainties.
Generated recipe scripts preserve `--help` for usage; a parameter named `help` receives an
unoccupied `--parameter-help` option, with additional `parameter-` prefixes when needed.

## Loaded source and recipe replay

Automatic recipe capture describes the active loaded data, independently of parser editor settings.
A source is reusable only while its exact request is retained: named-data retention, selection and
revision restoration preserve it; generic frame or manager edits clear it. Partial parser results
and undeclared injected backends require an explicit caller `RecipeSource` for recipe creation.
Recipe schema 6 retains the declared simulator, current parser contract, actual discovery/strict policy and
resolved scanner metadata. Replay uses those records directly without scanning again.

`RecipeSource.csv_policy` is `InferredCsvPolicy(configuration_columns)` for ordinary CSV inference
with exact configured-column casts, or `ReviewedCsvPolicy(ImportOptions(...))` for a reviewed import.
The latter uses the same preview/load service and accepted-row exclusion policy as the import UI.
It retains encoding, delimiter, header, whitespace, null tokens and column corrections; later editor
changes do not alter replay. `ImportOptions` owns tuples of text tokens and `ImportColumnCorrection`
values, with exact typed scalar controls.

A successfully executed recipe retains its source and exact dataset-wide transformations. Capturing
without an explicit source includes those steps once, followed by any explicitly supplied additional
steps. Capturing with an explicit source uses only caller-supplied transformations. Portfolio schema 11 saves
this frame-associated origin separately from editable parser controls. A snapshot or arbitrary Table
has no inferred reusable origin.

Current documents use portfolio schema 11 (`version: "11.0"`) or recipe schema 6. Serialized
plot display names use `legend_labels`; per-series style mappings retain original series keys.
Unsupported schema versions and nested style name fields are rejected before restoration or replay.
