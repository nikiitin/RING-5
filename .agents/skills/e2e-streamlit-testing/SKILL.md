---
name: e2e-streamlit-testing
description: Write or debug RING-5's Streamlit UI tests — the no-browser AppTest/ui_logic/ui_unit layers and the Playwright browser e2e/visual suite (Page Object Model, data-testid selectors, and Streamlit-specific gotchas). Use for any UI test, Playwright, AppTest, screenshot, or flaky-UI-test task.
---

# Testing the Streamlit UI

Choose the least expensive layer that covers the behavior:

| Level | Directory | Tooling | Browser |
| --- | --- | --- | --- |
| UI unit | `tests/ui_unit/` | mocked `st.*` | no |
| UI logic | `tests/ui_logic/` | controllers/protocols, mocked services | no |
| AppTest | `tests/ui/` | `streamlit.testing.v1.AppTest` | no |
| E2E / visual | `tests/e2e/`, `tests/visual/` | Playwright, Page Object Model | yes |

`make test-unit` covers unit and UI-unit tests. Run AppTest and UI-logic tests explicitly when those
owners change. Reuse `columns_side_effect` from `tests/conftest.py` for `st.columns` mocks.
`tests/ui/conftest.py` clears cached session resources around each AppTest.

## Page objects and selectors

Shared page objects live in `tests/visual/pages/` and serve both browser suites. Stable locators use
`@property`; parameterized lookups such as `get_plot_pill(name)` are methods. Keep product assertions
in tests. Page-object actions may wait for and verify their own completion.

Prefer accessible roles/labels, then scoped text or `data-testid` selectors. Common Streamlit test
IDs include `stSidebar`, `stMainBlockContainer`, `stSelectbox`, `stMultiSelect`, `stStatusWidget`,
`stDialog`, `stExpander`, `stPlotlyChart`, `stDataFrame` and `stFileUploader`. Scope repeated controls
by their containing section and visible label using the existing `_by_label` helpers. Plot and
engine selectors use radio roles; inspect checked state before clicking an active option.

## Reruns and current UI contracts

- Navigate with `wait_until="domcontentloaded"`, then `BasePage.wait_for_streamlit()`. Persistent
  Streamlit/chart connections make network-idle unsuitable as the readiness boundary.
- For actions that trigger a rerun, use `wait_for_streamlit(expect_rerun=True)`. It observes the
  running indicator before waiting for idle and accommodates fast cycles. Verify the resulting
  widget/chart state with Playwright expectations before the next dependent action.
- Create, rename, delete and duplicate clear `plot_selector` and rerun in
  `src/web/controllers/plot/creation_controller.py`. Creation selects the new plot through the
  lifecycle service. `ManagePlotsPage.create_plot` also calls the idempotent `select_plot(name)`;
  rename waits for its rerun and does not need navigation away and back.
- `select_plot_type` accepts exact factory identifiers such as `bar` or `dual_axis_bar_dot`.
  Plot selection uses visible names, disambiguated by the controller when names repeat.
- Expanders are `<details><summary>` elements. Click the summary and verify body visibility;
  opening an expander is a client-side action. A subsequent format/settings rerun may require
  reopening the relevant expander before interacting with a hidden control.
- Settings basics are Layout, Themes, Typography and Legends. Advanced mode adds Axes, Data
  Labels, Colors and Advanced. Test the toggle with an advanced-only pill such as Colors.
  Themes exposes preset application and JSON import/export through the normal render flow.
- Per-family configuration differs: stacked bars select statistics through "Statistics to Stack".
  Histograms select a declared native layout by its logical variable key and explicit physical
  bindings, or use caller-declared generic interval columns such as `variable..0-9`. Native point
  or range labels do not infer continuous geometry or create additional prefix aliases. Native
  controls offer count, probability and percent with cumulative views/CDF, without continuous
  rebinning or noncumulative density. Opaque Distribution source-label layouts show a missing-grid
  explanation and cannot render a native histogram. Follow each family's actual labels and widgets.
- Forms batch changes until submission. Dialogs can close on rerun. For fragment interactions,
  synchronize the observable result with the existing action helper before asserting or navigating.
- `app.py` owns a browser-session-scoped `ApplicationAPI` and closes it via `on_release`.
  Browser classes reuse `shared_page`; their class-scoped `_reset_app_state` fixtures reset that
  context. Preserve session-isolation tests and avoid cross-class state assumptions.

## Browser execution and resource use

`make test-e2e` uses `E2E_WORKERS=2` with loadgroup scheduling for non-serial cases, then a separate
`-n 0` invocation for cases marked `serial`. `make test-visual` runs serially. The Make targets own
these defaults; inspect them before changing parallelism.

For a memory-constrained session or an isolated diagnosis, use:

```bash
make test-e2e E2E_WORKERS=0
./python_venv/bin/pytest tests/e2e/test_plot_types.py -m requires_browser -n 0 \
  --timeout=240 --timeout-method=thread --no-cov
```

Each browser worker can own a Streamlit server and Chromium processes. Check available memory,
native thread limits and other active jobs before increasing concurrency. A cgroup/systemd scope
can provide an additional local resource bound when appropriate; it is not a repository-wide
execution requirement. Timeouts and OOMs are failures to investigate, including application state,
synchronization and the resource budget.

Plotly static PDF/SVG/PNG downloads use `plotly_download_bytes` in
`src/web/rendering/figure_export.py`, which bounds Kaleido attempts and retries with a fresh browser.
Keep export cases serial; HTML export can verify download controls without Chromium. Synchronize
engine selection before asserting chart content so an old Matplotlib image cannot satisfy a
Plotly-render expectation.

## Stateful flows

Class-scoped fixtures can reuse meaningful setup when tests deliberately share an ordered flow.
Keep each class's reset boundary explicit. The fixture tiers represent an empty workspace, loaded
CSV, a created plot and a finalized shaper pipeline; do not rely on another class's residual state.

Manage Plots rendering needs loaded data, a finalized pipeline and valid family-specific mappings.
Plot controls use `plot.<id>.widgets.*` keys. Run the relevant no-browser tests first, then the
browser/visual cases that exercise the changed behavior.
