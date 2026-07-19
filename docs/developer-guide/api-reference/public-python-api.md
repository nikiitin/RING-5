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
given one.

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

`ring5.FigureSpec` is the typed common figure configuration. `FigureSpecBuilder`, legend, reference
line, and dual-axis options support more structured construction. `FigureDecorations` and
`grouped_bar_coordinates` support script-defined annotations without importing rendering modules.

`export_file` and `export_bytes` infer the engine from the figure object. `Session.export` delegates
to the same boundary. Unsupported formats raise `ExportError`; missing optional executables raise
`DependencyMissingError`.

## Portfolio replay and lifecycle

`ring5.render_portfolio` restores and exports every plot. `ring5.doctor` reports parser and export
dependencies. `ring5.shutdown` releases process-wide worker pools early; they otherwise register
process-exit cleanup and restart on later use.

## Errors

Catch the narrow error from `ring5.errors` when recovery differs. All supported operational errors
inherit `Ring5Error`. `ScanError` covers empty, failed, or incomplete scans; `ParseError` covers
submission, resource-limit, worker, timeout, and assembly failures. Public boundaries preserve the
original failure as `__cause__` where wrapping adds API context.

When adding a public name, export it lazily where appropriate, document parameters and exceptions,
add a `public_api` contract test, keep `make test-api` at 100%, and update the User Guide.
