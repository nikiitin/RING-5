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
