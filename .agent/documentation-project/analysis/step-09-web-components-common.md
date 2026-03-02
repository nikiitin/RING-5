# Step 09 — Web Components (Common & Reusable) Analysis

> **Objective**: Catalog every reusable UI component — its purpose, parameters, rendering
> behavior, state interactions, and reuse patterns across the application.

---

## Scope

This step documents the **component library** — all shared UI building blocks used across
multiple pages. This is critical for the "Adding a New Component" guide.

---

## Files to Analyze

### Common Components
```
src/web/components/common/__init__.py
src/web/components/common/card_components.py        (card layouts)
src/web/components/common/chart_display.py          (chart rendering display)
src/web/components/common/data_components.py        (data display widgets)
src/web/components/common/filtered_selector.py      (filtered dropdown/multiselect)
src/web/components/common/history_components.py     (history tracking UI)
src/web/components/common/layout_components.py      (layout helpers)
src/web/components/common/pipeline.py               (pipeline visualization)
src/web/components/common/pipeline_step.py          (pipeline step component)
src/web/components/common/plot_controls.py          (plot control buttons)
src/web/components/common/plot_creation.py          (plot creation wizard)
src/web/components/common/plot_selector.py          (plot type selector)
src/web/components/common/reorderable_list.py       (drag-and-drop reorderable list)
```

### Data Source Components
```
src/web/components/data_source/__init__.py
src/web/components/data_source/data_source_components.py
src/web/components/data_source/pattern_index_selector.py
src/web/components/data_source/variable_editor.py
```

### Data Manager Components
```
src/web/components/data_managers/__init__.py
src/web/components/data_managers/data_manager_components.py
src/web/components/data_managers/data_manager.py
src/web/components/data_managers/mixer.py
src/web/components/data_managers/outlier_remover.py
src/web/components/data_managers/preprocessor.py
src/web/components/data_managers/seeds_reducer.py
```

### Shaper Configuration Components
```
src/web/components/shapers/__init__.py
src/web/components/shapers/mean_config.py
src/web/components/shapers/normalize_config.py
src/web/components/shapers/pivot_config.py
src/web/components/shapers/selector_transformer_configs.py
src/web/components/shapers/sort_config.py
src/web/components/shapers/split_apply_config.py
```

### Plotting Components
```
src/web/components/plotting/interactive_plot.py
src/web/components/plotting/custom_plotly/         (all files)
```

### Plotting Config Components
```
src/web/components/plotting/config/__init__.py
src/web/components/plotting/config/base_plot_config.py
src/web/components/plotting/config/dual_axis_config.py
src/web/components/plotting/config/dual_axis_settings.py
src/web/components/plotting/config/grouped_bar_config.py
src/web/components/plotting/config/grouped_stacked_bar_config.py
src/web/components/plotting/config/grouped_stacked_bar_theme.py
src/web/components/plotting/config/heatmap_config.py
src/web/components/plotting/config/histogram_config.py
src/web/components/plotting/config/plot_config_components.py
src/web/components/plotting/config/stacked_bar_config.py
```

### Settings Components
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
src/web/components/plotting/settings/widget_factory.py
```

---

## Questions to Answer

### For Each Component:
- [ ] What is its function signature? (parameters, return type)
- [ ] What Streamlit widgets does it render?
- [ ] What state does it read?
- [ ] What state does it write/modify?
- [ ] What callbacks does it register?
- [ ] Is it a fragment? (@st.fragment)
- [ ] Where is it used? (which pages call it?)
- [ ] What is its key management strategy? (Streamlit widget keys)
- [ ] Does it have any dependencies on other components?

### Component Architecture Patterns:
- [ ] Is there a base component pattern?
- [ ] How do components receive data? (parameters vs session_state?)
- [ ] How do components communicate changes? (callbacks vs state mutation?)
- [ ] Are there any component composition patterns?
- [ ] How is the component-based architecture enforced? (no presenters)

### Reuse Patterns:
- [ ] Which components are used on multiple pages?
- [ ] Are there any wrapper/adapter components?
- [ ] How are components organized by feature vs. by type?

### Widget Factory:
- [ ] What is the widget factory pattern?
- [ ] What widgets does it create?
- [ ] How does it standardize widget creation?
- [ ] What configuration does it accept?

---

## Information to Extract

### Component Catalog

For each component:
```
### ComponentName
- **File**: src/web/components/xxx/yyy.py:NN
- **Function**: function_name(params)
- **Purpose**: [what it renders]
- **Parameters**:
  | Parameter | Type | Description |
  |-----------|------|-------------|
  | ...       | ...  | ...         |
- **Widgets Rendered**: [st.selectbox, st.slider, etc.]
- **State Read**: [session_state keys or repository calls]
- **State Written**: [mutations]
- **Used By**: [list of pages/components that use it]
- **Is Fragment**: yes/no
- **Key Pattern**: [how widget keys are generated]
```

### Component Dependency Graph
```
[Which components use which other components]
```

### Common Patterns
```
[Documented patterns for component creation]
```

---

## Output Template

### 1. Common Components Catalog
```
[To be filled]
```

### 2. Data Source Components Catalog
```
[To be filled]
```

### 3. Data Manager Components Catalog
```
[To be filled]
```

### 4. Shaper Config Components Catalog
```
[To be filled]
```

### 5. Plotting Config Components Catalog
```
[To be filled]
```

### 6. Settings Components Catalog
```
[To be filled]
```

### 7. Widget Factory Documentation
```
[To be filled]
```

### 8. Component Architecture Patterns
```
[To be filled]
```

### 9. Component Dependency Graph
```
[To be filled]
```

---

## Downstream Dependencies

This analysis feeds into:
- `DEVELOPER_GUIDE_PLAN.md` → `web/components.md`, `web/adding-a-new-component.md`
- `AI_KNOWLEDGE_BASE_PLAN.md` → `reference/components-catalog.md`
- Step 12 (settings pills) — settings components are a subset
- Step 19 (extension points) — component patterns for new components
