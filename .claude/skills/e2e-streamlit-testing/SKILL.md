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
- **Segmented control toggle:** clicking the *already-active* option **deselects** it. Use an
  `ensure_*_mode` pattern: check active state first, click only if needed.
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
