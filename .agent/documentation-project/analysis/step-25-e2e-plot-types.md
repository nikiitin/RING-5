# Step 25 — E2E Tests: Plot Creation & Per-Type Coverage (9 Plot Types)

> **Objective**: Design E2E tests for creating each of the 9 plot types, verifying their
> type-specific configuration, data mapping, and initial rendering.
> Each plot type produces a **Tier 2 state snapshot** reusable by settings/engine tests.

---

## Scope

### Combinatorial Surface
```
9 plot types, each requiring:
  - Plot creation (name, type selection)
  - Type-specific configuration UI verification
  - Data column mapping
  - Initial render (verify chart appears)
  - Type-specific settings (e.g., histogram bins, heatmap colorscale)

Plot Types:
  1. bar          — Simple bar chart
  2. line         — Line/time-series
  3. scatter      — Scatter/correlation
  4. histogram    — Distribution histogram
  5. heatmap      — Heatmap grid
  6. grouped_bar  — Grouped bar chart
  7. stacked_bar  — Stacked bar chart
  8. grouped_stacked_bar — Grouped-stacked bar chart
  9. dual_axis_bar_dot   — Dual-axis bar + dot overlay
```

---

## Files to Analyze (per plot type)
```
# Each plot type has up to 3 files:
src/web/pages/ui/plotting/types/{type}_plot.py          (plot type class)
src/web/components/plotting/config/{type}_config.py     (config UI)
src/web/pages/ui/plotting/styles/{type}_ui.py           (style UI, if exists)

# Shared files:
src/web/pages/ui/plotting/plot_factory.py
src/web/pages/ui/plotting/base_plot.py
src/web/pages/ui/plotting/plot_config_ui.py
src/web/pages/ui/plotting/types/_trace_helpers.py
src/web/components/plotting/config/base_plot_config.py
src/web/components/plotting/config/plot_config_components.py

# Existing tests:
tests/visual/test_manage_plots.py
tests/visual/test_comprehensive_e2e.py
tests/visual/pages/manage_plots_page.py              (existing POM — 870 lines)
```

---

## Tests to Design

### Per-Plot-Type Test Class (9 classes, each using Tier 1 snapshot)

For EACH of the 9 plot types:
```python
class TestBarPlotCreation:    # (and 8 more for each type)
    """Uses Tier 1 snapshot (parsed data available)."""

    def test_create_plot(self):
        """Create a new bar plot → verify it appears."""

    def test_type_specific_config_visible(self):
        """Verify type-specific config options are rendered."""

    def test_data_column_mapping(self):
        """Map data columns to x/y/color → verify mapping."""

    def test_initial_render_plotly(self):
        """Render with Plotly → verify chart visible."""

    def test_initial_render_matplotlib(self):
        """Render with Matplotlib → verify chart visible."""

    def test_screenshot_for_docs(self):
        """Capture rendered chart for documentation."""
        # → media/plots/{type}-example.png

    def test_creation_gif(self):
        """Capture animated creation workflow for documentation."""
        # → media/plots/{type}-creation.gif (for select types)
```

### Type-Specific Configuration Tests

#### Bar Chart:
- [ ] X/Y column selection
- [ ] Orientation (horizontal/vertical)
- [ ] Bar width configuration

#### Line Plot:
- [ ] X/Y column selection
- [ ] Line style (solid, dashed, dotted)
- [ ] Marker configuration

#### Scatter Plot:
- [ ] X/Y column selection
- [ ] Size/color column mapping
- [ ] Marker size/shape

#### Histogram:
- [ ] Column selection
- [ ] Bin count/size
- [ ] Normalization mode

#### Heatmap:
- [ ] X/Y/Z column mapping
- [ ] Color scale selection
- [ ] Annotation display

#### Grouped Bar:
- [ ] Group column selection
- [ ] Category column selection
- [ ] Value column selection
- [ ] Group layout

#### Stacked Bar:
- [ ] Stack column selection
- [ ] Category column
- [ ] Value column
- [ ] Stack ordering

#### Grouped-Stacked Bar:
- [ ] Group + stack column selection
- [ ] Theme configuration
- [ ] Complex layout options

#### Dual-Axis Bar-Dot:
- [ ] Primary axis (bar) configuration
- [ ] Secondary axis (dot) configuration
- [ ] Axis synchronization

---

### State Snapshot Output (Tier 2, per plot type)

After each plot type is created and configured:
- Save **9 Tier 2 snapshots** (one per plot type with data loaded + plot created)
- These snapshots are the INPUT for Steps 26-28 (settings, shapers, engines)
- Sharing these snapshots means Steps 26-28 skip both parsing AND plot creation

---

### Documentation Media
```
Screenshots (9 — one per plot type):
  bar-chart-example.png
  line-plot-example.png
  scatter-plot-example.png
  histogram-example.png
  heatmap-example.png
  grouped-bar-example.png
  stacked-bar-example.png
  grouped-stacked-bar-example.png
  dual-axis-example.png

GIFs (4 — for the most common types):
  bar-chart-creation.gif
  line-plot-creation.gif
  scatter-plot-creation.gif
  (+ 1 more for grouped-stacked or dual-axis)

Additional:
  plot-type-selection.png
  create-plot-dialog.png
  plot-created.png (generic)
```

### POM Additions Needed for ManagePlotsPage
- [ ] Per-plot-type configuration locators
- [ ] Data column mapping widget locators
- [ ] Chart render area locators (per engine)
- [ ] Plot creation dialog locators
- [ ] Plot type selection dropdown locator
- [ ] "Chart rendered" assertion helper

---

## Output Template

### 1. Per-Type Test Specification
```
[To be filled: 9 sections, one per plot type]
```

### 2. POM Additions
```
[To be filled: New ManagePlotsPage properties/methods]
```

### 3. Tier 2 Snapshot Specification
```
[To be filled: How to save/restore per-plot-type state]
```

### 4. Media Asset Manifest
```
[To be filled: Every screenshot and GIF]
```

---

## Downstream Dependencies

- Uses Tier 1 snapshot from Step 23
- Produces 9 × Tier 2 snapshots for Steps 26, 27, 28
- Media feeds into USER_GUIDE_PLAN → plots/*.md
