# Step 28 — E2E Tests: Rendering Engines Comparison & Engine-Specific Behavior

> **Objective**: Design E2E tests that compare Plotly and Matplotlib rendering for each
> plot type. Verify engine toggle works, engine-specific settings apply, and produce
> comparison documentation media.

---

## Scope

### Combinatorial Surface
```
9 plot types × 2 engines = 18 render combinations

Per combination:
  - Verify chart renders correctly
  - Verify engine-specific controls appear/disappear
  - Verify settings preservation on engine switch
  - Capture side-by-side comparison
```

---

## Files to Analyze
```
src/web/rendering/engine_manager.py
src/web/rendering/plotly_connector.py
src/web/rendering/matplotlib_connector.py
src/web/rendering/trace_to_plotly.py
src/web/rendering/matplotlib_trace_renderer.py
src/web/components/plotting/settings/engine_settings.py
src/web/components/common/chart_display.py
src/web/components/plotting/interactive_plot.py

tests/visual/test_manage_plots.py                    (engine toggle tests?)
tests/ui_logic/test_engine_specific_controls.py
tests/ui_logic/test_engine_toggle.py
```

---

## Tests to Design

### Engine Toggle Tests (per plot type, using Tier 2 snapshots)
- [ ] Default engine is Plotly → verify Plotly chart
- [ ] Switch to Matplotlib → verify chart changes rendering
- [ ] Switch back to Plotly → verify chart restores
- [ ] Verify chart content is equivalent (same data)
- [ ] Verify engine-specific controls show/hide

### Engine-Specific Controls Tests
- [ ] Plotly: interactive features (hover, zoom, pan)
- [ ] Matplotlib: static rendering, no interactivity
- [ ] Plotly-specific settings in Advanced panel
- [ ] Matplotlib-specific settings in Advanced panel

### Cross-Engine Comparison Tests
For each plot type produce side-by-side screenshots:
- [ ] bar: Plotly vs Matplotlib
- [ ] line: Plotly vs Matplotlib
- [ ] scatter: Plotly vs Matplotlib
- [ ] histogram: Plotly vs Matplotlib
- [ ] heatmap: Plotly vs Matplotlib
- [ ] (grouped, stacked, grouped-stacked, dual-axis as needed)

### Plotly Interactivity Tests
- [ ] Hover tooltip appears → capture in GIF
- [ ] Zoom in/out → verify chart responds
- [ ] Pan → verify chart responds
- [ ] Reset zoom → verify chart resets

### Settings Persistence Tests
- [ ] Configure settings on Plotly → switch to Matplotlib → verify settings kept
- [ ] Configure settings on Matplotlib → switch to Plotly → verify settings kept
- [ ] Engine-specific settings → verify they hide when switching

### Documentation Media
```
Screenshots:
  engine-comparison.png (side-by-side Plotly vs Matplotlib)
  manage-plots-landing.png (with engine selector visible)

GIFs:
  engine-toggle.gif (switch between engines, see chart change)
  plotly-interactive.gif (Plotly hover/zoom demonstration)

Extra:
  matplotlib-publication.png (Matplotlib rendered, publication-quality)
```

---

## Output Template

### 1. Engine Toggle Test Specifications (per plot type)
```
[To be filled]
```

### 2. Cross-Engine Comparison Matrix
```
[To be filled: visual differences, known divergences]
```

### 3. Interactivity Test Specifications
```
[To be filled]
```

### 4. Media Asset Manifest
```
[To be filled]
```

---

## Downstream Dependencies

- Uses Tier 2 snapshots from Step 25
- Media feeds into USER_GUIDE_PLAN → plots/*.md, manage-plots.md
- Comparison screenshots are key documentation assets
