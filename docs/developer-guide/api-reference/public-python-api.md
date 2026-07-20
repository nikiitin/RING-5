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
Likewise, `parse_submit` returns `ParseJob` and `parse` returns `ParseResult`. A job can be cancelled
without touching work from another handle. `Session.load` returns a DataFrame. `shape`,
`reduce_seeds`, `remove_outliers`, `apply_operation`, and `mix_columns` preserve `ring5.Table` when
given one. `Session.compare` returns a `Table` when both baseline and candidate inputs are tables;
otherwise it returns a DataFrame.

`Session.compare` aligns baseline and candidate rows by unique key columns and emits long-form
metric results. Directions and non-negative tolerances can be global or keyed by metric. Percentage
and absolute threshold modes are supported. Missing keys and non-finite values remain in the result;
invalid columns, duplicate keys, and invalid options raise `DataValidationError`.

`Session.annotate_comparison` copies a threshold-comparison result and adds plot-ready labels,
signed changes, outcome text, accessible symbols, Plotly marker names, and color-blind-safe colors.
It preserves `ring5.Table` inputs. Callers can follow the stored threshold mode or explicitly select
percentage or absolute changes; malformed comparison schemas raise `DataValidationError`.

`Session.compare_statistics` accepts repeated observations and optional grouping columns. It
returns Welch confidence intervals and p-values, Hedges' g, deterministic bootstrap estimates and
intervals, and sample-quality warnings. Confidence, alpha, bootstrap count, seed, and the
small-sample threshold are explicit parameters. Invalid options raise `DataValidationError`.

`Session.profile_data` returns an immutable `DataQualityReport` for a DataFrame or `ring5.Table`.
Dataset counts remain scalar fields; `columns` contains immutable `ColumnQuality` records and
`to_frame()` creates a new DataFrame for display or export. Optional expected types validate finite
values without conflating invalid values with missing cells.

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
workspace. `compare_datasets` leaves both sources unchanged; `join_datasets` and `append_datasets`
store their result under a separate name. The selected dataset remains the compatibility view used
by existing plot, transformation, and portfolio APIs.

`Session.dataset_lineage` returns immutable `DatasetLineage` and `DatasetRevision` records with
operation labels, source and parent ancestry, content fingerprints, and the current undo/redo
state. `get_dataset_revision` inspects a defensive snapshot. `undo_dataset`, `redo_dataset`, and
`restore_dataset_revision` change the current state without mutating historical snapshots. Lineage
is session-owned and is cleared with the named workspace; portfolio persistence is not implied.

`Session.diagnose_join` returns immutable `JoinDiagnostics` for an explicit key relationship,
including duplicate rows and groups on each side, unmatched input rows, and matched distinct keys.
`join_datasets_validated` repeats that validation immediately before joining, refuses incompatible
cardinality without storing output, and returns `(DataFrame, JoinDiagnostics)` on success.

`Session.save_dataset_snapshot` persists the selected, active, or explicitly named dataset in a
versioned non-executable archive. `list_dataset_snapshots` reads immutable `DatasetSnapshotInfo`
metadata without decoding table payloads. `load_dataset_snapshot` verifies the compressed payload
checksum and the reconstructed dataframe fingerprint before retaining it as a named dataset;
`delete_dataset_snapshot` removes one local cache entry. Snapshot storage follows `RING5_DATA_DIR`,
so separate processes can deliberately share the same catalog.

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
from `ring5.available_plot_types()`; display names are accepted but identifiers are preferable in
versioned scripts. Mapping configurations are validated before registration for required fields,
field types, and referenced columns. Every downstream engine failure is normalized to `RenderError`.
`ring5.available_shaper_types()` provides the equivalent registry for pipelines.

## Figure configuration and export

### Annotations and web shapes

<!--
`uman~ring5.figure.shapes-annotations.documentation~1`

Covers:
- req~ring5.figure.shapes-annotations~1

-->

`FigureSpec` serializes engine-independent text annotations; the Matplotlib connector applies their
text, coordinates, and optional arrow styling. In the web application, editable line, circle, and
rectangle shapes are Plotly layout shapes and remain Plotly-specific.

### Typed FigureSpec

<!--
`uman~ring5.api.figure-spec.documentation~1`

Covers:
- req~ring5.api.figure-spec~1

-->

`ring5.FigureSpec` is the typed common figure configuration. It covers data mappings, dimensions,
axes, grouping, legends, reference lines, and dual-axis options. The `extra` mapping carries
supported flat configuration keys that do not yet have typed fields.

### Fluent FigureSpec builder

<!--
`uman~ring5.api.figure-builder.documentation~1`

Covers:
- req~ring5.api.figure-builder~1

-->

`FigureSpecBuilder` groups related settings into chainable methods for data, size, palettes, axes,
bars, category labels, legends, reference lines, and dual axes. `build()` returns a validated
`FigureSpec`.

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
`Session.create_report` captures selected plots or dashboards, bounded tables, narrative,
provenance, and that environment in an immutable `AnalysisReport`. `report_bytes` and
`export_report` generate deterministic self-contained HTML or multi-page PDF output.
`ring5.render_portfolio` restores and exports every plot. `ring5.doctor` reports parser and export
dependencies. `ring5.shutdown` releases process-wide worker pools early; they otherwise register
process-exit cleanup and restart on later use.

## Errors

<!--
`uman~ring5.api.typed-errors.documentation~1`

Covers:
- req~ring5.api.typed-errors~1

-->

Catch the narrow error from `ring5.errors` when recovery differs. All supported operational errors
inherit `Ring5Error`. `ScanError` covers empty, failed, or incomplete scans; `ParseError` covers
submission, resource-limit, worker, timeout, and assembly failures. Public boundaries preserve the
original failure as `__cause__` where wrapping adds API context.

When adding a public name, export it lazily where appropriate, document parameters and exceptions,
add a `public_api` contract test, keep `make test-api` at 100%, and update the User Guide.
