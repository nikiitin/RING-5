# Step 12 — Settings Pills & Widget Factory Analysis

> **Objective**: Document the settings pill navigation pattern, the widget factory, every
> settings panel, and how user-configurable plot settings flow from UI widgets to
> visualization configuration.

---

## Scope

This step analyzes the **settings UI system** — the pill-based navigation that organizes
all plot customization options, and the widget factory that standardizes widget creation.

---

## Files to Analyze

### Settings Pills
```
src/web/pages/ui/plotting/settings_pills.py        (pill navigation system)
```

### Widget Factory
```
src/web/components/plotting/settings/widget_factory.py (standardized widget creation)
```

### Settings Panels
```
src/web/components/plotting/settings/__init__.py
src/web/components/plotting/settings/advanced_settings.py
src/web/components/plotting/settings/axes_settings.py
src/web/components/plotting/settings/colors_settings.py
src/web/components/plotting/settings/data_labels_settings.py
src/web/components/plotting/settings/engine_settings.py
src/web/components/plotting/settings/layout_settings.py
src/web/components/plotting/settings/legend_settings.py
src/web/components/plotting/settings/ordering_settings.py
src/web/components/plotting/settings/reference_line_settings.py
src/web/components/plotting/settings/shapes_settings.py
src/web/components/plotting/settings/typography_settings.py
```

### Tests (for understanding behavior)
```
tests/ui_logic/test_settings_pills.py
tests/ui_logic/test_settings_pills_e2e.py
tests/ui_logic/test_engine_specific_controls.py
```

---

## Questions to Answer

### Settings Pill System:
- [ ] What is the pill navigation pattern?
- [ ] How are pills rendered? (horizontal buttons? tabs? radio?)
- [ ] How does pill selection work? (session state key?)
- [ ] What pills are available? (Layout, Typography, Legend, Axes, Colors, etc.)
- [ ] Are pills dynamic? (different pills for different plot types?)
- [ ] How do pills map to settings panels?
- [ ] What is the rendering flow when a pill is selected?

### Widget Factory:
- [ ] What is the widget factory function/class signature?
- [ ] What widget types does it create? (selectbox, slider, number_input, checkbox, etc.)
- [ ] How does it standardize key generation?
- [ ] How does it handle default values?
- [ ] How does it handle callbacks?
- [ ] How does it integrate with session state?
- [ ] What parameters does it accept?

### For Each Settings Panel:
- [ ] What function signature does it have?
- [ ] What settings/widgets does it render?
- [ ] What config model fields does it correspond to?
- [ ] What values are written to session state?
- [ ] What defaults does it use?
- [ ] Are any settings conditional? (show/hide based on other settings?)
- [ ] Are any settings engine-specific? (Plotly-only? Matplotlib-only?)
- [ ] What validation does it apply?

### Settings → Config Flow:
- [ ] How do widget values in session state become config model fields?
- [ ] What is the mapping from widget key → config field?
- [ ] Who reads the session state values? (config builder? plot type? connector?)
- [ ] Is there a settings aggregation step?

### Engine-Specific Controls:
- [ ] Which settings are engine-specific?
- [ ] How are they shown/hidden based on engine selection?
- [ ] What happens to engine-specific settings when switching engines?

---

## Information to Extract

### Settings Panel Catalog

For each settings panel:
```
### SettingsPanelName
- **File**: src/web/components/plotting/settings/xxx_settings.py:NN
- **Pill Label**: [what the pill says]
- **Function**: function_name(params)
- **Widgets**:
  | Widget | Type | Key | Default | Maps To | Description |
  |--------|------|-----|---------|---------|-------------|
  | Title  | text_input | plot_title | "" | FigureConfig.title | ... |
- **Conditional Widgets**: [widgets that show/hide]
- **Engine-Specific**: [Plotly/Matplotlib only widgets]
- **Config Fields**: [which config model fields this panel sets]
```

### Pill → Panel → Config Mapping
```
Pill: "Layout"
  → Panel: layout_settings()
    → Widgets: [width, height, margin, ...]
      → Config: FigureConfig.width, FigureConfig.height, ...

Pill: "Typography"
  → Panel: typography_settings()
    → Widgets: [title_font_size, axis_font_size, ...]
      → Config: TypographyConfig.title_size, ...
```

---

## Output Template

### 1. Settings Pill System Documentation
```
[To be filled]
```

### 2. Widget Factory Documentation
```
[To be filled]
```

### 3. Settings Panel Catalog (one per panel)
```
[To be filled]
```

### 4. Pill → Panel → Config Mapping
```
[To be filled]
```

### 5. Engine-Specific Settings Documentation
```
[To be filled]
```

### 6. Session State Key Map (settings-related)
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `web/settings-pills.md`
- `USER_GUIDE_PLAN.md` → `webapp/plot-settings.md`
- Step 07 (viz config) — settings produce config values
- Step 11 (rendering) — config builder reads settings
- Step 18 (data flow) — settings are part of the configuration step
