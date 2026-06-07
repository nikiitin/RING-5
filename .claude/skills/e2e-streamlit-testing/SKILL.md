---
name: e2e-streamlit-testing
description: Write or debug RING-5's Streamlit UI tests — the no-browser AppTest/ui_logic/ui_unit layers and the Playwright browser e2e/visual suite (Page Object Model, data-testid selectors, and Streamlit-specific gotchas). Use for any UI test, Playwright, AppTest, screenshot, or flaky-UI-test task.
---

# Testing the Streamlit UI

RING-5 tests the UI at four levels — pick the cheapest that covers the behavior:

| Level | Dir | Tooling | Browser |
|-------|-----|---------|---------|
| UI unit | `tests/ui_unit/` | mock `st.*` (use `columns_side_effect` from root `conftest.py`) | no |
| UI logic | `tests/ui_logic/` | controllers/protocols, mocked services | no |
| AppTest | `tests/ui/` | `streamlit.testing.v1.AppTest` | no |
| E2E / visual | `tests/e2e/`, `tests/visual/` | **Playwright** (`requires_browser`), Page Object Model | yes |

Run: `make test-unit` (no-browser), `make test-visual` (browser; spins up Streamlit on :8502).
E2E marker: `-m requires_browser`. Visual is excluded from default collection.

> `tests/ui/conftest.py` monkey-patches a Streamlit **1.53.1** bug (`ButtonGroup.indices` iterating
> string chars in single-select). If you bump Streamlit, re-check whether that patch is still needed.

## Page Object Model (Playwright)
- Locators are **`@property`** (never methods); actions are **methods** that take no locator params.
- **No assertions inside Page Objects** — assert in the test with auto-retrying `expect()`.
- Locator priority: `get_by_role()` > `get_by_text()` > `get_by_label()` > `get_by_test_id()`.
- Existing POMs live in `tests/e2e/` (+ `fixtures/`) and `tests/visual/pages/`. `DataSourcePage` is
  the richest; `ManagePlotsPage` is thin — extend it when adding plot e2e coverage.

## Streamlit `data-testid` selector map
`stSidebar`, `stMainBlockContainer`, `stSelectbox`, `stMultiSelect`, `stBaseButton-primary` /
`stBaseButton-secondary`, `stStatusWidget`, `stDialog`, `stExpander`, `stPlotlyChart`, `stDataFrame`,
`stFileUploader`. Segmented controls render as `stButtonGroup` (with active/inactive testid
suffixes). **Tabs:** `role="tab"`, and **all tab panels stay in the DOM at once** — scope with the
`_by_label` pattern, never `.first`/`.nth()`.

```python
def _by_label(page, test_id, label):   # scope a widget duplicated across tabs
    return page.locator(f"[data-testid='{test_id}']").filter(has_text=label)
```

## Critical Streamlit × Playwright gotchas (these cause most flakes)
- **Page-ready wait:** `wait_for_load_state("networkidle")` **then** wait for
  `[data-testid='stStatusWidget']` to disappear. (networkidle alone races the script start.)
- **Wait for the rerun to *start*, not just end** (the subtle one that silently loses state):
  the status widget appears a beat *after* the triggering click (client→server round-trip). If you
  only wait for it to be *hidden*, you can observe the **pre-rerun** idle state and return too early —
  then a fast follow-up action (navigate / another click) **aborts the rerun before it commits**, and
  Streamlit discards the now-unrendered widget's session state. Symptoms: a rename/delete that
  "doesn't take", the wrong plot deleted. Fix: for actions guaranteed to rerun, first wait for
  `stStatusWidget` to become **visible** (bounded ~3s) *then* hidden — `BasePage.wait_for_streamlit(expect_rerun=True)`.
  Used by rename/delete/duplicate/create/finalize/add_shaper/select_plot.
- **Segmented control toggle:** clicking the *already-active* option **deselects** it. Use an
  `ensure_*`/idempotent pattern: check the active state (`data-testid='stBaseButton-pillsActive'`)
  first, click only if needed, then assert it became active (`select_plot`, `select_engine`).
- **Creating a plot does NOT auto-select it.** `st.pills(key="plot_selector")`'s persisted session
  value (the old plot) wins over `set_current_plot_id(new)`, and the selector then resets current
  back to it — so config/pipeline edits hit the *previously-selected* plot. `create_plot` must
  explicitly `select_plot(name)` after creating. (Likewise: rename has no `st.rerun()`, so the pill
  label is stale until the next rerun — navigate away+back to refresh.)
- **Expanders are `<details><summary>`** — click the **`summary`** (there is no
  `stExpanderToggleDetails` testid). Opening is a *client-side* toggle (no rerun) so verify-then-act
  by waiting for the body to be visible; the open state *survives* later reruns.
- **Per-plot-type config UIs differ — don't assume X/Y axes:** `stacked_bar` has **no Y-axis / "Stack
  by"** (it stacks numeric *statistics* via a "Statistics to Stack" multiselect, defaulting to the
  first numeric cols); `histogram` needs gem5 bucket columns (`var..0-10`) or it warns "No histogram
  variables detected"; the plot-config axis-label fields are **"X-label"/"Y-label"** (not "X-axis label").
- **Settings pills:** the basic sections (Layout/Typography/Legends) **always** render; "Show advanced
  settings" only *adds* the advanced sections (Axes/Data Labels/Colors/Advanced). To test the toggle,
  key off an advanced-only pill (e.g. "Colors"), not the whole pills group. (Preset pills
  `render_preset_pills` exist but are **not wired** into the render flow — no preset UI appears.)
- **Fragment reruns** (`@st.fragment`) need an extra `wait_for_timeout(500)` after interaction.
- **`st.rerun()` closes dialogs** — don't expect a `stDialog` to survive a rerun.
- **Forms batch** their widget changes (no per-widget rerun) — submit, then assert.
- **`@st.cache_resource` is a singleton** → `ApplicationAPI` (and its `PlotRepository`, which stores
  plots in plain instance attrs, *not* `st.session_state`) persists across browser "sessions" on the
  same server, so plots/data bleed across test classes. **Isolation is enforced by an autouse,
  class-scoped `_reset_app_state` fixture** in both `tests/e2e/conftest.py` and `tests/visual/conftest.py`
  that clicks "Reset All" (`BasePage.reset_all()` → `api.reset_session()`) before each class's setup.
  Required even under `-n 3 --dist loadgroup` (one worker can run several `xdist_group`s against one
  server), and it makes `-n 0` work too. Don't remove it; new browser-test classes inherit the clean
  slate automatically (all classes use `shared_page`).

## -n 3 contention sizing (run the gate with `--timeout=180`)
Under `-n 3` three browsers + three Streamlit servers compete, so the heaviest work is genuinely
slower than single-run timeouts assume — size for *parallel* latency, not retries:
- `CHART_TIMEOUT = 60s` (Plotly iframe JS resize / Matplotlib `st.pyplot` can exceed 30s under load).
- `EXPORT_TIMEOUT = 120s` for the raster download button — `download_section` computes Kaleido
  `fig.to_image()` **eagerly** before `st.download_button`, so three parallel Chromium exports starve
  (90s proved insufficient for pdf/svg/png). Run the e2e gate at **`--timeout=180`** so a slow-but-
  progressing export isn't killed by the per-test cap. (test_07's role/enabled check uses kaleido-free
  `html` to stay fast.)

## Efficiency pattern (worth it for browser tests)
Class-scoped page fixtures + ordered, semantically-related tests cut a prior suite from 148 → 37
tests (~18 min saved). Trade-off: tests in a class share state and are ordered — acceptable for
E2E flows. A "tier" snapshot ladder works well: **Tier 0** empty → **Tier 1** CSV loaded →
**Tier 2** + plot created → **Tier 3** + shaper pipeline; share via fixture scope (or Portfolio
save/load) so each class doesn't redo expensive setup.

## Manage Plots preconditions (the usual cause of "nothing renders")
Data must be loaded; the shaper pipeline must be **finalized**; X/Y axes must be set — only then does
the chart render. Happy path: Data Source → parse → Manage Plots → create plot → add shaper →
finalize → select X/Y → refresh. Session-state keys are `plot_id`-suffixed for isolation.

## Verify after
`make test-unit` for no-browser layers; `make test-visual` (or
`./python_venv/bin/pytest tests/e2e/ -m requires_browser --timeout=120`) for browser layers.
The `playwright` MCP server (see CLAUDE.md §8) is handy for reproducing UI bugs interactively.
