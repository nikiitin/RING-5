---
layout: default
title: Public Python API
parent: Stable Interfaces
grand_parent: Developer Guide
nav_order: 1
permalink: /developer-guide/api-reference/public-python-api/
---

# Public Python API

`ring5` is the supported headless surface. Public names are exported from `ring5/__init__.py` and
covered by `tests/integration/test_ring5_public_api.py`.

## Workspace

`ring5.Session` owns one headless workspace. It can submit or complete parsing, load CSV data, run
manager operations and shaper pipelines, create and render plots, export figures, and save or
restore portfolios. Use it as a context manager so pending session work and temporary parser output
are released.

`Session.parse_submit` returns an owned `ParseJob`; `Session.parse` waits and returns `ParseResult`.
`Session.load` returns a DataFrame. `shape`, `reduce_seeds`, and `remove_outliers` preserve
`ring5.Table` when given one.

`create_plot` registers a plot and `render` renders it. `plot` performs both. Plot identifiers come
from `ring5.available_plot_types()`; display names are accepted but identifiers are preferable in
versioned scripts.

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
inherit `Ring5Error`. Public boundaries preserve the original failure as `__cause__` where wrapping
adds API context.

When adding a public name, export it lazily where appropriate, document parameters and exceptions,
add integration coverage, and update the User Guide.
