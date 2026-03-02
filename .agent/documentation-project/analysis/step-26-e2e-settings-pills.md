# Step 26 — E2E Tests: Settings Pills (11 Panels × 9 Plot Types × 2 Engines)

> **Objective**: Design E2E tests for every settings pill panel applied to each plot type
> on both rendering engines. This is the largest combinatorial surface in the application.
> Uses Tier 2 state snapshots (plot already created) to avoid re-parsing and re-creating.

---

## Scope

### Combinatorial Surface
```
11 settings panels × 9 plot types × 2 engines = 198 combinations

However, NOT all settings apply to all plot types:
  - Some settings are universal (Layout, Typography, Legend, Colors)
  - Some are type-specific (Ordering only for bar-types, Shapes for scatter, etc.)
  - Some are engine-specific (Advanced settings differ by engine)

Realistic testing matrix: ~120-150 valid combinations
```

### Settings Panels
```
1.  Layout          — width, height, margins (UNIVERSAL)
2.  Typography      — fonts, sizes (UNIVERSAL)
3.  Legend          — position, naming, visibility (UNIVERSAL)
4.  Axes            — labels, ranges, ticks (UNIVERSAL)
5.  Colors          — palette, custom colors (UNIVERSAL)
6.  Data Labels     — show/hide, format, position (MOST types)
7.  Ordering        — sort criteria (BAR types only)
8.  Reference Lines — add, configure (LINE/BAR types)
9.  Shapes          — add, configure (SCATTER type)
10. Engine          — engine-specific controls (PER ENGINE)
11. Advanced        — advanced options (PER ENGINE)
```

---

## Files to Analyze
```
src/web/components/plotting/settings/layout_settings.py
src/web/components/plotting/settings/typography_settings.py
src/web/components/plotting/settings/legend_settings.py
src/web/components/plotting/settings/axes_settings.py
src/web/components/plotting/settings/colors_settings.py
src/web/components/plotting/settings/data_labels_settings.py
src/web/components/plotting/settings/ordering_settings.py
src/web/components/plotting/settings/reference_line_settings.py
src/web/components/plotting/settings/shapes_settings.py
src/web/components/plotting/settings/engine_settings.py
src/web/components/plotting/settings/advanced_settings.py
src/web/components/plotting/settings/widget_factory.py
src/web/pages/ui/plotting/settings_pills.py

tests/visual/test_settings_verification.py          (existing)
tests/ui_logic/test_settings_pills.py               (existing)
tests/ui_logic/test_settings_pills_e2e.py           (existing — 55 KB!)
```

---

## Test Strategy

### Tier Structure (leveraging state snapshots)
```
For each plot type (using Tier 2 snapshot):
  → Navigate to Manage Plots (plot already exists)
  → For each applicable settings pill:
    → Click pill → verify panel rendered
    → Modify 2-3 key settings → verify UI feedback
    → Verify chart re-renders with changes
    → Capture screenshot (media asset)
    → Switch engine → verify settings preserved/adapted
```

### Applicability Matrix
```
| Setting | bar | line | scatter | histogram | heatmap | g_bar | s_bar | gs_bar | dual |
|---------|-----|------|---------|-----------|---------|-------|-------|--------|------|
| Layout  | YES | YES  | YES     | YES       | YES     | YES   | YES   | YES    | YES  |
| Typo    | YES | YES  | YES     | YES       | YES     | YES   | YES   | YES    | YES  |
| Legend  | YES | YES  | YES     | YES       | YES     | YES   | YES   | YES    | YES  |
| Axes    | YES | YES  | YES     | YES       | YES     | YES   | YES   | YES    | YES  |
| Colors  | YES | YES  | YES     | YES       | YES     | YES   | YES   | YES    | YES  |
| DataLbl | YES | YES  | YES     | YES       | NO?     | YES   | YES   | YES    | YES  |
| Order   | YES | NO   | NO      | NO        | NO      | YES   | YES   | YES    | YES  |
| RefLine | YES | YES  | YES     | NO        | NO      | YES   | YES   | YES    | YES  |
| Shapes  | NO  | NO   | YES     | NO        | NO      | NO    | NO    | NO     | NO   |
| Engine  | YES | YES  | YES     | YES       | YES     | YES   | YES   | YES    | YES  |
| Advanced| YES | YES  | YES     | YES       | YES     | YES   | YES   | YES    | YES  |
```

### Tests per Settings Panel

#### Layout Settings:
- [ ] Verify width/height inputs visible
- [ ] Modify width → verify chart resizes
- [ ] Modify margins → verify spacing changes
- [ ] Test on Plotly → verify
- [ ] Test on Matplotlib → verify

#### Typography Settings:
- [ ] Verify font controls visible
- [ ] Modify title font size → verify chart
- [ ] Modify axis labels → verify chart
- [ ] Font family selection (if available)

#### Legend Settings:
- [ ] Verify legend controls visible
- [ ] Toggle legend visibility → verify on chart
- [ ] Change legend position → verify on chart
- [ ] Legend naming mode (Primary/Secondary/Tertiary)

#### Axes Settings:
- [ ] Verify axis label inputs
- [ ] Modify X-axis label → verify on chart
- [ ] Modify Y-axis range → verify on chart
- [ ] Tick configuration

#### Colors Settings:
- [ ] Verify palette selector
- [ ] Change palette → verify chart colors change
- [ ] Custom color assignment
- [ ] Colorblind-safe palette verification

#### Data Labels Settings:
- [ ] Toggle data labels → verify on chart
- [ ] Change format → verify display
- [ ] Change position → verify location

#### Ordering Settings:
- [ ] Change sort column → verify bar order
- [ ] Toggle ascending/descending
- [ ] Multi-key sorting

#### Reference Lines Settings:
- [ ] Add reference line → verify on chart
- [ ] Configure line properties (value, color, style)
- [ ] Remove reference line

#### Shapes Settings (scatter only):
- [ ] Add shape annotation
- [ ] Configure shape properties

#### Engine Settings:
- [ ] Toggle engine → verify chart re-renders
- [ ] Engine-specific options visible

#### Advanced Settings:
- [ ] Scan all advanced options per engine

---

### Documentation Media
```
Screenshots (10 — one per settings panel):
  settings-pills-overview.png
  settings-layout.png
  settings-typography.png
  settings-legend.png
  settings-axes.png
  settings-colors.png
  settings-data-labels.png
  settings-ordering.png
  settings-reference-lines.png
  settings-shapes.png
  settings-advanced.png

GIFs (1):
  engine-toggle.gif (switch Plotly ↔ Matplotlib and see chart change)
```

### POM Additions Needed
- [ ] Per-pill navigation method: `select_pill(pill_name)`
- [ ] Per-panel widget locators (all 11 panels)
- [ ] Chart change verification helper (compare before/after)
- [ ] Engine toggle method with wait
- [ ] Widget factory interaction helpers

---

## Output Template

### 1. Applicability Matrix (filled)
```
[To be filled: Which settings apply to which plot types]
```

### 2. Per-Panel Test Specifications
```
[To be filled: 11 sections with per-type variations]
```

### 3. POM Additions
```
[To be filled]
```

### 4. Media Asset Manifest
```
[To be filled]
```

---

## Downstream Dependencies

- Uses Tier 2 snapshots from Step 25 (9 snapshots, one per plot type)
- Media feeds into USER_GUIDE_PLAN → plot-settings.md
- Feeds into Step 28 (engine comparison)
