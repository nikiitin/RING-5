---
name: ui-check
description: Gate the RING-5 web layer — the Page→Controller→Component pattern (no presenter), namespaced UI state, dual-engine rendering, and the UI test layers. Use when reviewing/verifying anything under src/web/, Streamlit pages/components, or UI state.
---

# UI check (the presentation-layer gate)

Layer C (`src/web/` + `app.py`) is Streamlit + Plotly/Matplotlib. This gate verifies the UI
conventions and runs the right test layers. For *writing* UI tests, use the
`e2e-streamlit-testing` skill; this skill is the conformance gate.

## Conventions to verify
- **Page → Controller → Component (PCC).** Pages
  (`src/web/pages/`) wire controllers (`src/web/controllers/plot/`: creation/pipeline/render) to
  self-contained components (`src/web/components/`). A new "presenter" module is a regression.
- **UI state is namespaced & typed** via `src/web/state/ui_state_manager.py::UIStateManager` —
  plot controls use `plot.<id>.widgets.*`, with appearance controls in `widgets.appearance.*`;
  data managers use `manager.<name>.*`, and navigation uses `nav.current_page`.
  Construct plot/manager keys through `WidgetKeyBuilder`. Use `plot.reset_widgets` before rendering
  reset controls, `plot.cleanup` for deletion, and `cleanup_all` for workspace reset/restore.
- Parse progress identity and the persistent last-consumed notice use the typed `parse.*` owner.
  Accepted submission/retry clears the old notice; `cleanup_all` clears it on workspace reset or
  restore. Completion is recorded only after facade consumption succeeds, using the receipt job ID.
- **Per-plot widget keys are unique**: preserve semantic series, group and shaper identities within
  the owning plot's namespace. Shared keys or suffix-based cleanup cause cross-talk.
- **Dual engine**: rendering goes through `FigureConfig` → connectors; the engine is switched by the
  `ring5_engine_mode` session key (`EngineManager`). Default palette is `wong`. The plot class never
  calls `go.*`/`plt.*` (see `plot-type-check`).
- **Settings ownership:** Layout, Themes, Typography and Legends are basic sections; advanced mode
  adds Axes, Data Labels, Colors and Advanced. Theme application/import/export is wired through
  `ThemePresetsSettingsComponent`. Tick marks / tick pad / grid dash belong in Axes; font sizes and
  colors in Typography; Y-axis title standoff and vertical shift in Axes Y-Left.
- Components are self-contained widgets — no business logic; that belongs in a service behind the facade.

## Run the tests (no browser → browser)
```bash
./python_venv/bin/pytest tests/ui tests/ui_logic tests/ui_unit -q   # AppTest + controllers + mocked-st
make test-visual                                                    # Playwright, starts an isolated Streamlit server
```
- `tests/ui/` — Streamlit `AppTest` (no browser). `tests/ui_logic/` — controllers/UI logic.
  `tests/ui_unit/` — components with a mocked `st`.
- **Reuse `columns_side_effect`** from the root `tests/conftest.py` for mocking `st.columns` — don't
  redefine it.
- `tests/e2e/` + `tests/visual/` are Playwright (`requires_browser`), Page Object Model,
  `data-testid` selectors. Mind the segmented-control toggle & fragment-rerun gotchas documented in
  `e2e-streamlit-testing`.

## Quick smells
```bash
rg -ni 'presenter' src/web/ -g '*.py'             # inspect additional presentation layers
rg -n 'st.session_state\[' src/web/ -g '*.py'      # prefer UIStateManager/WidgetKeyBuilder
```

## Keep this skill sharp
Edit this guide in place when the UI conventions change:
- Namespaces, the engine key, and settings-ownership above mirror `ui_state_manager.py`,
  `engine_manager.py`, and the settings pills. If those change, update this list.
- New UI footgun found in review? Add it here (and to `e2e-streamlit-testing` if it's test-mechanics);
  document durable contracts in the developer guide.

## Verify after
`make arch-check && ./python_venv/bin/pytest tests/ui tests/ui_logic tests/ui_unit -q`
