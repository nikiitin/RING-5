---
layout: default
title: Testing
parent: Development
grand_parent: Developer Guide
nav_order: 3
permalink: /developer-guide/development/testing/
---

# Testing

Place a test at the lowest layer that proves the contract without hiding a cross-component failure.

| Location | Scope |
| --- | --- |
| `tests/unit/` | Core, parser, rendering, and public helpers in isolation |
| `tests/integration/` | Cross-component workflows and the supported `ring5` API |
| `tests/ui_logic/` | UI decisions separated from Streamlit rendering |
| `tests/ui_unit/` and `tests/ui/` | Streamlit component units and real AppTest page workflows |
| `tests/e2e/` | Browser workflows against a running application |
| `tests/performance/` | Explicit performance contracts |
| `tests/tests_principle_compliance/` | Architecture and design invariants |
| `tests/visual/` | Native rendering and visual workflows; included in full browser acceptance |

Reuse fixtures from `tests/conftest.py` and existing xdist groups for shared state. Tests should
assert public outcomes and typed errors, not implementation call order unless orchestration is the
contract.

## Performance regression checks

<!--
`uman~ring5.quality.performance-regression-gates.documentation~1`

Covers:
- req~ring5.quality.performance-regression-gates~1

-->

Performance tests use repeatable fixtures and explicit thresholds for large-data transformations,
caches, rendering, and worker-pool throughput. Treat a threshold change as a reviewed contract
change rather than weakening it merely to accommodate a regression. They participate in
`make test` and `make test-ci`. Run the subset directly with
`python_venv/bin/pytest tests/performance -n 0 --no-cov`.

## Commands

```bash
make test-unit        # fast unit and UI-unit tests
make test             # non-browser tests plus serial Plotly export tests
make test-ci          # non-browser suite with coverage enforcement
make test-export      # serial Kaleido export tests
make test-latex       # PGF tests; requires XeLaTeX
make test-e2e         # complete browser acceptance, including visual workflows
make test-visual      # focused rerun of the visual browser suite
```

Use markers declared in `pyproject.toml`. Repository test commands run serially by default.
`make test-e2e` uses two workers for grouped browser tests so ordered, stateful classes stay together,
then runs resource-heavy tests serially and the complete visual suite with one process.
Chromium, the pinned Chrome for Plotly static exports, and TeX Live for PGF are required. Prepare
a supported Linux environment with:

```bash
make playwright-install install-latex check-latex
export BROWSER_PATH="$(python_venv/bin/python -m ring5.cli install-chrome)"
```

CI installs these prerequisites before the same gate. Use `E2E_WORKERS=0` for a single process
on machines with limited memory, or `E2E_WORKERS=1` for one worker. The `-n auto` hook is capped
at two workers.

Make targets also limit native numerical runtimes to two threads. Set `RING5_NATIVE_THREADS=1` for
a tighter local budget. Parser deployments can tune `RING5_WORK_POOL_SIZE` and
`RING5_PERL_POOL_SIZE`; both default to two and each value must be a positive integer.

For a public API addition, extend `tests/integration/test_ring5_public_api.py`. For serialized
changes, test the current writer/reader round trip and rejection of unsupported versions and keys.

## Browser acceptance

The complete gate is `make test-e2e`. A failed stage stops the command. A successful focused rerun
helps diagnose a failure; it does not replace a successful complete run after the fix. Preserve
failed-run logs and browser traces separately from the final accepted result. Do not remove cases,
add skips, weaken outcomes, or increase time limits to turn a failure into a pass.

Assert the user-visible result at the browser boundary: the current native figure and numerical
observations, downloaded data or document contents, preserved workspace, or explicit rejection and
recovery. A visible control, iframe, success message, or plot name is insufficient evidence for
data correctness. Keep lower-layer unit and integration tests for numerical edge cases and
cross-component contracts that have no browser interface.

The workflow inventory below describes the assertions in the suite. It does not replace the
complete acceptance run. Test paths are relative to `tests/e2e/` unless stated otherwise.

| Workflow | Browser evidence | Cases and remaining boundary |
| --- | --- | --- |
| Import, parse and recover | Exact imported and parsed CSV values; rejected rows; explicit partial loading; failed-attempt retry; missing measurements; incremental additions and removals; reset defaults. | `test_data_journeys.py`, especially `TestParserEvidence`, `TestParserRecovery` and `TestParserResetDefaults`. Live authenticated remote transfers and cancellation races need separate coverage; remote browser cases prove rejection before authorization. |
| Transform, inspect and compare tables | Downloaded arithmetic results, seed means and sample deviations, outlier removal, filtered views, quality counts, append/join contents, revisions, snapshots, and comparison CSV/JSON/JUnit results. | `test_data_journeys.py`. Numerical edge cases and the full set of join relationships also require unit/integration tests. |
| Schema contracts and units | An edited minimum rejects one row without changing the dataset; labels and units persist; conversion scales both the metric and its uncertainty; incompatible units preserve data; undo restores the prior values and metadata. | `TestSchemaContractSemantics` in `test_data_journeys.py` uses the real keyboard editor and downloaded CSV values. Other schema rule types and affine unit conversions remain unit/integration contracts. |
| Render all 17 plot families | Independent expected Plotly trace values and calculated observations; each example also produces a fresh, decoded Matplotlib image. Dual-axis tests check both metric groups and axis assignments. | `test_gallery_rendering.py`, `test_dual_axis.py`. Matplotlib image decoding does not inspect every native artist value; connector and numerical tests cover that boundary. |
| Configure all 13 shaper editors | Three composed workflows verify exact processed CSV values, current native chart values, and preserved source data. | `test_shaper_semantics.py`. Missing values, category ordering, nested branches and malformed configuration also require lower-layer tests. |
| Dashboards and drill-down | Two native panels and offline HTML retain their observations; real selection gestures apply highlight/filter and clear them; bar, histogram and heatmap clicks expose the expected raw rows. | `test_dashboard_composer.py`, `test_plot_drill_down.py`. `test_plot_small_multiples.py` checks panel labels, retained controls and engine switching, rather than exact facet values. |
| Figure themes and settings | Theme JSON round-trips, native background colors change, observations stay fixed, and imported data bindings are rejected. | `TestFigureThemePreset` in `test_settings.py`. Most other settings cases check control visibility or retained input values; the accessible-theme case checks its palette and visible audit result. |
| Download figures | Seven engine/format combinations transfer actual PDF, SVG, PNG and PGF bytes; HTML downloads render offline with exact chart/source-data checks. | `test_static_downloads.py`, `test_export_presets.py`, `test_portfolio.py`. Static-file structure and decoded pixels do not establish every glyph's numerical placement. |
| Portfolios, recipes and reports | Downloaded bundles and signed portfolios restore exact data and figures; tampering and wrong secrets fail; recipe import/conflict/replace/delete and downloaded Python execution are exercised; gallery and publication downloads contain real output and stale report downloads disappear. | `test_portfolio_lifecycle.py`. Python runs outside the checkout with the current source on its import path; this does not prove an installed wheel. PDF structure checks do not replace page-by-page layout review. |
| Sessions and workspace tools | Independent sessions retain different row counts and plot names after one resets; commands navigate; search links target exact guides; tags and review text persist in the UI. | `test_session_isolation.py`, `test_command_palette.py`, `test_workspace_search.py`, `test_workspace_organizer.py`, `test_analysis_review.py`. `test_autosave_recovery.py` verifies a recovered plot name, rather than a complete recovered dataset. |
| Visual workflows | Real parser/manager journeys and selected native SVG geometry assertions run alongside screenshots. | The complete `tests/visual/` suite runs in `make test-e2e`. Screenshot capture alone is diagnostic evidence, not a numerical or pixel-baseline assertion. |

This is a finite workflow inventory. Parser variants, worker shutdown, unit semantics, arbitrary
malformed documents, relayout persistence and the full styling/configuration space need unit and
integration tests in addition to representative browser workflows. Document the boundary of a new
browser test instead of claiming coverage of every dataset, setting combination or external service.
