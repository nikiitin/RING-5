---
name: ui-check
description: Gate the RING-5 web layer — the Page→Controller→Component pattern (no presenter), namespaced UI state, dual-engine rendering, and the UI test layers. Use when reviewing/verifying anything under src/web/, Streamlit pages/components, or UI state.
---

# UI check (the presentation-layer gate)

Layer C (`src/web/` + `app.py`) is Streamlit + Plotly/Matplotlib. This gate verifies the UI
conventions and runs the right test layers. For *writing* UI tests, use the
`e2e-streamlit-testing` skill; this skill is the conformance gate.

## Conventions to verify
- **Page → Controller → Component (PCC). There is NO presenter layer** (it was removed). Pages
  (`src/web/pages/`) wire controllers (`src/web/controllers/plot/`: creation/pipeline/render) to
  self-contained components (`src/web/components/`). A new "presenter" module is a regression.
- **UI state is namespaced & typed** via `src/web/state/ui_state_manager.py::UIStateManager` —
  keys are `plot.{id}.*`, `manager.*`, `nav.*`, `export.*` (built by `WidgetKeyBuilder`). Raw ad-hoc
  `st.session_state["auto_42"]` strings are the anti-pattern.
- **Per-plot widget keys are unique**: `f"{prefix}_{field}_{plot_id}"` — shared keys across plots
  cause cross-talk.
- **Dual engine**: rendering goes through `FigureConfig` → connectors; the engine is switched by the
  `ring5_engine_mode` session key (`EngineManager`). Default palette is `wong`. The plot class never
  calls `go.*`/`plt.*` (see `plot-type-check`).
- **Settings ownership** (don't misfile a control): tick marks / tick pad / grid dash → **Axes** pill;
  Typography = font sizes/colors only; Y-axis title standoff & vshift → **Axes Y-Left** pill.
- Components are self-contained widgets — no business logic; that belongs in a service behind the facade.

## Run the tests (no browser → browser)
```bash
./python_venv/bin/pytest tests/ui tests/ui_logic tests/ui_unit -q   # AppTest + controllers + mocked-st
make test-visual                                                    # Playwright, spins Streamlit on :8502
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
grep -rni "presenter" src/web/ --include=*.py            # should be empty (layer removed)
grep -rn "st.session_state\[" src/web/ --include=*.py     # prefer UIStateManager/WidgetKeyBuilder
```

## Keep this skill sharp
Canon, not history — edit in place when the UI conventions move:
- Namespaces, the engine key, and settings-ownership above mirror `ui_state_manager.py`,
  `engine_manager.py`, and the settings pills. If those change, update this list.
- New UI footgun found in review? Add it here (and to `e2e-streamlit-testing` if it's test-mechanics);
  durable facts → a memory.

## Verify after
`make arch-check && ./python_venv/bin/pytest tests/ui tests/ui_logic tests/ui_unit -q`
