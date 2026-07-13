---
title: "RING-5 Session State Keys Reference"
parent: Reference
grand_parent: Engineering Reference
nav_order: 5
---

# RING-5 Session State Keys Reference

## Architecture Overview

- **Two-tier state**: Domain state (7 in-memory repositories) + UI state (`st.session_state`)
- **Singleton**: `ApplicationAPI` created once via `@st.cache_resource`, stored at `st.session_state.api`
- **Domain state** survives reruns without serialization (same Python objects reused)
- **UI state** managed through `UIStateManager` (namespaced) + direct `st.session_state` access (~45 locations)

---

## 1. Application Bootstrap Keys

| Key | Type | Default | Set By | Read By | Purpose |
|-----|------|---------|--------|---------|---------|
| `api` | `ApplicationAPI` | `get_api()` return | `app.py` | All pages/controllers | Global API singleton reference |
| `_nav_page` | `str` | `"Data Source"` | `app.py` | `app.py` sidebar | Current navigation page |

**Source**: `app.py`

---

## 2. UIStateManager -- Plot UI State

Namespace prefix: `plot.{plot_id}.`

Accessed via: `UIStateManager().plot.*`

| Key | Type | Default | Set By | Read By | Purpose |
|-----|------|---------|--------|---------|---------|
| `plot.{id}.auto_refresh` | `bool` | `True` | `PlotRenderController` | `PlotRenderController` | Auto-refresh toggle per plot |
| `plot.{id}.dialog.save` | `bool` | `False` | `_PlotUIState` | `_PlotUIState` | Save dialog visibility |
| `plot.{id}.dialog.load` | `bool` | `False` | `_PlotUIState` | `_PlotUIState` | Load dialog visibility |
| `plot.{id}.order.{type}` | `list[Any] \| None` | `None` | Ordering components | Ordering components | Custom dimension ordering (xaxis, group, legend) |
| `plot.{id}.edit_shapes` | `bool` | `False` | `_PlotUIState` | `ShapesSettingsComponent` | Shape editing mode toggle |
| `plot.pending_updates` | `dict[str, Any] \| None` | `None` | `PlotRenderController` | `manage_plots.py` | Pending widget updates from relayout events |

**Source**: `src/web/state/ui_state_manager.py` (`_PlotUIState` class)

### Plot cleanup on deletion

`_PlotUIState.cleanup(plot_id)` removes all keys matching:
- `plot.{plot_id}.*` (new namespaced keys)
- `auto_{plot_id}` (legacy)
- `show_save_for_plot_{plot_id}` (legacy)
- `show_load_for_plot_{plot_id}` (legacy)
- `edit_shapes_{plot_id}` (legacy)
- `auto_t_{plot_id}` (legacy)

---

## 3. UIStateManager -- Manager UI State

Namespace prefix: `manager.{name}.`

Accessed via: `UIStateManager().manager.*`

| Key | Type | Default | Set By | Read By | Purpose |
|-----|------|---------|--------|---------|---------|
| `manager.{name}.load_trigger` | `dict[str, Any] \| None` | `None` | `HistoryComponents` (on_click) | Each DataManager `render()` | Load-from-history trigger |
| `manager.{name}.form.{field}` | `Any` | `None` | `_ManagerUIState` | `_ManagerUIState` | Form field values |

**Source**: `src/web/state/ui_state_manager.py` (`_ManagerUIState` class)

---

## 4. UIStateManager -- Navigation UI State

Namespace prefix: `nav.`

Accessed via: `UIStateManager().nav.*`

| Key | Type | Default | Set By | Read By | Purpose |
|-----|------|---------|--------|---------|---------|
| `nav.current_page` | `str \| None` | `None` | `_NavUIState` | `_NavUIState` | Current page name |
| `nav.current_tab` | `str \| None` | `None` | `_NavUIState` | `_NavUIState` | Current tab within page |

**Source**: `src/web/state/ui_state_manager.py` (`_NavUIState` class)

---

## 5. UIStateManager -- Export UI State

Namespace prefix: `export.`

Accessed via: `UIStateManager().export.*`

| Key | Type | Default | Set By | Read By | Purpose |
|-----|------|---------|--------|---------|---------|
| `export.last_path` | `str` | `""` | `_ExportUIState` | `_ExportUIState` | Last used export path |

**Source**: `src/web/state/ui_state_manager.py` (`_ExportUIState` class)

---

## 6. Engine Manager Key

| Key | Type | Default | Set By | Read By | Purpose |
|-----|------|---------|--------|---------|---------|
| `ring5_engine_mode` | `Literal["plotly", "matplotlib"]` | `"plotly"` | `EngineManager.set_engine()` | `EngineManager.get_engine()`, `PlotRenderController` | Active visualization engine |

**Source**: `src/web/rendering/engine_manager.py`

---

## 7. Chart Display / Rendering Keys

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `plot.{id}.mpl_fig` | `matplotlib.Figure \| None` | `ChartDisplayComponent.render_matplotlib_chart()` | `download_section._render_mpl_download()` | Cached matplotlib figure for download |
| `plot.{id}.last_relayout` | `dict[str, Any]` | `PlotRenderController._render_visualization()` | `PlotRenderController._render_visualization()` | Last relayout event for deduplication |

**Source**: `src/web/components/common/chart_display.py`, `src/web/controllers/plot/render_controller.py`

---

## 8. Data Manager Widget Keys (via WidgetKeyBuilder)

### 8.1 Preprocessor

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `manager.preprocessor.op` | `str` | `PreprocessorManager.render()` | Selectbox widget | Selected operation |
| `manager.preprocessor.src1` | `str` | `PreprocessorManager.render()` | Selectbox widget | Source column 1 |
| `manager.preprocessor.src2` | `str` | `PreprocessorManager.render()` | Selectbox widget | Source column 2 |
| `manager.preprocessor.name` | `str` | `PreprocessorManager.render()` | Text input widget | New column name |
| `manager.preprocessor.preview` | (button key) | Streamlit | `PreprocessorManager` | Preview button state |
| `manager.preprocessor.confirm` | (button key) | Streamlit | `PreprocessorManager` | Confirm button state |
| `manager.preprocessor.load_trigger` | `dict \| None` | `HistoryComponents` | `PreprocessorManager` | History load trigger |

**Source**: `src/web/components/data_managers/preprocessor.py`

### 8.2 Seeds Reducer

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `manager.seeds_reducer.target_column` | `str` | `SeedsReducerManager.render()` | Selectbox widget | Column to reduce over |
| `manager.seeds_reducer.categorical` | `list[str]` | `SeedsReducerManager.render()` | Multiselect widget | Group-by columns |
| `manager.seeds_reducer.numeric` | `list[str]` | `SeedsReducerManager.render()` | Multiselect widget | Numeric columns for stats |
| `manager.seeds_reducer.apply` | (button key) | Streamlit | `SeedsReducerManager` | Apply button state |
| `manager.seeds_reducer.confirm` | (button key) | Streamlit | `SeedsReducerManager` | Confirm button state |
| `manager.seeds_reducer.load_trigger` | `dict \| None` | `HistoryComponents` | `SeedsReducerManager` | History load trigger |

**Source**: `src/web/components/data_managers/seeds_reducer.py`

### 8.3 Outlier Remover

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `manager.outlier_remover.col` | `str` | `OutlierRemoverManager.render()` | Selectbox widget | Outlier target column |
| `manager.outlier_remover.groupby` | `list[str]` | `OutlierRemoverManager.render()` | Multiselect widget | Group-by columns |
| `manager.outlier_remover.apply` | (button key) | Streamlit | `OutlierRemoverManager` | Apply button state |
| `manager.outlier_remover.confirm` | (button key) | Streamlit | `OutlierRemoverManager` | Confirm button state |
| `manager.outlier_remover.load_trigger` | `dict \| None` | `HistoryComponents` | `OutlierRemoverManager` | History load trigger |

**Source**: `src/web/components/data_managers/outlier_remover.py`

### 8.4 Mixer

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `manager.mixer.mode` | `str` | `MixerManager.render()` | Segmented control widget | Mixer mode selection |
| `manager.mixer.select_cols` | `list[str]` | `MixerManager.render()` | Multiselect widget | Columns to merge |
| `manager.mixer.op` | `str` | `MixerManager.render()` | Selectbox widget | Selected operation |
| `manager.mixer.new_name` | `str` | `MixerManager.render()` | Text input widget | New column name |
| `manager.mixer.sep` | `str` | `MixerManager.render()` | Text input widget | Concatenation separator |
| `manager.mixer.preview` | (button key) | Streamlit | `MixerManager` | Preview button state |
| `manager.mixer.confirm` | (button key) | Streamlit | `MixerManager` | Confirm button state |
| `manager.mixer.load_trigger` | `dict \| None` | `HistoryComponents` | `MixerManager` | History load trigger |

**Source**: `src/web/components/data_managers/mixer.py`

---

## 9. Plot Config Widget Keys (Sanitized Multiselects)

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `x_filter_{plot_id}` | `list[str]` | `PlotConfigComponents.render_filter_multiselects()` | Same (sanitization) | X-axis filter multiselect |
| `group_filter_{plot_id}` | `list[str]` | `PlotConfigComponents.render_filter_multiselects()` | Same (sanitization) | Group filter multiselect |
| `y_multiselect_{plot_id}` | `list[str]` | `PlotConfigComponents.render_statistics_multiselect()` | Same (sanitization) | Y-columns multiselect |
| `hm_metrics_{plot_id}` | `list[str]` | `heatmap_config.render()` | Same (sanitization) | Heatmap metrics multiselect |

**Sanitization pattern**: Before rendering, invalid options are filtered from `st.session_state[key]` to prevent `StreamlitInvalidOptionError` (Streamlit >= 1.53).

**Source**: `src/web/components/plotting/config/plot_config_components.py`, `src/web/components/plotting/config/heatmap_config.py`

---

## 10. Color/Shape Editing Widget Keys

| Key Pattern | Type | Set By | Read By | Purpose |
|-------------|------|--------|---------|---------|
| `{prefix}color_{plot_id}_{hash}_{palette}` | `str` (hex color) | `ColorsSettingsComponent._render_series_item()`, `BaseStyleUI._render_series_item()` | Same | Custom color picker |
| `{prefix}use_col_{plot_id}_{hash}` | `bool` | Same as above | Same | Color override toggle |
| `{prefix}orig_col_{plot_id}_{hash}_{palette}` | `str` (hex color) | Same as above | Same | Original palette color (disabled) |
| `{prefix}rst_{plot_id}_{hash}` | (button key) | Same as above | Same | Reset-to-palette button |
| `edit_shapes_{plot_id}` | `bool` | `ShapesSettingsComponent.render()` | `ShapesSettingsComponent.render()` | Legacy shape editing flag |

- `{prefix}` is typically `"theme_"` from the colors settings or empty string
- `{hash}` is an MD5 hash of the series value string (first 8 chars)
- `{palette}` is the palette name string (e.g., `"wong"`)

**Source**: `src/web/components/plotting/settings/colors_settings.py`, `src/web/pages/ui/plotting/styles/base_ui.py`, `src/web/components/plotting/settings/shapes_settings.py`

---

## 11. Reorderable List Keys

| Key Pattern | Type | Set By | Read By | Purpose |
|-------------|------|--------|---------|---------|
| `{prefix}_order_{plot_id}` | `list[str]` | `render_reorderable_list()` | Same | Item ordering state |
| `{prefix}_rename_{item_key}_{plot_id}` | `str` | Same | Same | Per-item rename text input |
| `{prefix}_up_{i}_{plot_id}` | (button key) | Same | Same | Move-up button |
| `{prefix}_down_{i}_{plot_id}` | (button key) | Same | Same | Move-down button |

**Source**: `src/web/components/common/reorderable_list.py`

---

## 12. Filtered Selector Keys

| Key Pattern | Type | Set By | Read By | Purpose |
|-------------|------|--------|---------|---------|
| `{key}__selections` | `set[str]` | `filtered_multiselect()` | Same | Persistent multiselect selections (survives filter changes) |
| `{key}__search` | `str` | Streamlit text_input widget | `filtered_multiselect()`, `filtered_selectbox()` | Search filter text |
| `{key}__sel_all` | (button key) | Streamlit | `filtered_multiselect()` | Select-all-matching button |
| `{key}__clear` | (button key) | Streamlit | `filtered_multiselect()` | Clear-all button |

Thresholds:
- `filtered_selectbox`: falls back to standard widget when `len(options) <= 200`
- `filtered_multiselect`: falls back to standard widget when `len(options) <= 100`

**Source**: `src/web/components/common/filtered_selector.py`

---

## 13. Data Source Widget Keys

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `stats_path_input` | `str` | Streamlit text_input | `DataSourceComponents.render_parser_config()` | Stats directory path |
| `stats_pattern_input` | `str` | Streamlit text_input | `DataSourceComponents.render_parser_config()` | Stats filename pattern |
| `simulator_selector` | `str` | Streamlit pills | `DataSourceComponents.render_parser_config()` | Active simulator backend |
| `parser_strategy_selector` | `str` | Streamlit segmented_control | `DataSourceComponents.render_parser_config()` | Parsing strategy |

**Source**: `src/web/components/data_source/data_source_components.py`

---

## 14. Variable Editor Keys

| Key Pattern | Type | Set By | Read By | Purpose |
|-------------|------|--------|---------|---------|
| `dist_range_result_{var_id}` | `dict` (`{minimum, maximum}`) | `VariableEditor._show_scan_dialog()` | `VariableEditor.render_distribution_config()` | Deep-scan range result for distributions |
| `var_name_{var_id}` | `str` | Streamlit text_input | `VariableEditor._render_common_fields()` | Variable name |
| `var_alias_{var_id}` | `str` | Streamlit text_input | `VariableEditor._render_common_fields()` | Variable alias |
| `var_type_{var_id}` | `str` | Streamlit selectbox | `VariableEditor._render_common_fields()` | Variable type |
| `delete_var_{var_id}` | (button key) | Streamlit | `VariableEditor._render_common_fields()` | Delete variable button |
| `vector_entries_select_{var_id}` | `list[str]` | `filtered_multiselect()` | `VariableEditor` | Selected vector entries |
| `vector_entries_{var_id}` | `str` | Streamlit text_input | `VariableEditor` | Manual vector entries |
| `entry_mode_{var_id}` | `str` | Streamlit pills | `VariableEditor` | Entry input mode |
| `vec_parse_mode_{var_id}` | `str` | Streamlit segmented_control | `VariableEditor` | Vector parsing mode |
| `dist_parse_mode_{var_id}` | `str` | Streamlit segmented_control | `VariableEditor` | Distribution parsing mode |
| `hist_parse_mode_{var_id}` | `str` | Streamlit segmented_control | `VariableEditor` | Histogram parsing mode |
| `dist_min_{var_id}` | `float` | Streamlit number_input | `VariableEditor` | Distribution minimum |
| `dist_max_{var_id}` | `float` | Streamlit number_input | `VariableEditor` | Distribution maximum |
| `stat_total_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Extract total statistic |
| `stat_mean_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Extract mean statistic |
| `stat_gmean_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Extract geometric mean |
| `stat_samples_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Extract samples count |
| `stat_stdev_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Extract standard deviation |
| `dist_stat_mean_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Distribution: extract mean |
| `dist_stat_stdev_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Distribution: extract stdev |
| `dist_stat_samples_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Distribution: extract samples |
| `dist_stat_total_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Distribution: extract total |
| `dist_stat_gmean_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Distribution: extract gmean |
| `dist_stat_underflows_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Distribution: extract underflows |
| `dist_stat_overflows_{var_id}` | `bool` | Streamlit checkbox | `VariableEditor` | Distribution: extract overflows |
| `deep_scan_{var_id}` | (button key) | Streamlit | `VariableEditor` | Deep scan button |

**Source**: `src/web/components/data_source/variable_editor.py`

---

## 15. Data Visualization / Table Keys

| Key | Type | Default | Set By | Read By | Purpose |
|-----|------|---------|--------|---------|---------|
| `page_num` | `int` | `1` | Streamlit number_input | `DataManagerComponents.render_visualization_tab()` | Current page number for pagination |
| `search_col` | `str` | `"All Columns"` | Streamlit selectbox | `DataManagerComponents.render_visualization_tab()` | Search-in-column selection |
| `search_term` | `str` | `""` | Streamlit text_input | `DataManagerComponents.render_visualization_tab()` | Search text |
| `display_cols` | `list[str]` | `[]` | Streamlit multiselect | `DataManagerComponents.render_visualization_tab()` | Selected display columns |
| `rows_per_page` | `int \| str` | `100` | Streamlit selectbox | `DataManagerComponents.render_visualization_tab()` | Rows per page (20, 50, 100, 500, "All") |

**Source**: `src/web/components/data_managers/data_manager_components.py`

---

## 16. Split-Apply Config Keys

| Key Pattern | Type | Set By | Read By | Purpose |
|-------------|------|--------|---------|---------|
| `{key_base}_step_count` | `int` | `SplitApplyConfig._render_sub_pipeline()` | Same | Number of shaper sub-steps per group |
| `{key_prefix}sa_join_{shaper_id}` | `list[str]` | Streamlit multiselect | `SplitApplyConfig.render()` | Join columns |
| `{key_prefix}sa_ngroups_{shaper_id}` | `int` | Streamlit slider | `SplitApplyConfig.render()` | Number of column groups |
| `{key_prefix}sa_g{idx}_{shaper_id}_cols` | `list[str]` | Streamlit multiselect | `SplitApplyConfig._render_group()` | Group column selection |

**Source**: `src/web/components/shapers/split_apply_config.py`

---

## 17. Plot Render Controller Widget Keys

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `plot_type_sel_{plot_id}` | `str` | Streamlit selectbox | `PlotRenderController.render()` | Plot type selector |
| `show_advanced_{plot_id}` | `bool` | Streamlit toggle | `PlotRenderController.render()` | Show/hide advanced settings |
| `auto_t_{plot_id}` | `bool` | Streamlit toggle | `ChartDisplayComponent.render_refresh_controls()` | Auto-refresh toggle |
| `refresh_{plot_id}` | (button key) | Streamlit | `ChartDisplayComponent.render_refresh_controls()` | Manual refresh button |
| `engine_selector_{plot_id}` | `str` | Streamlit pills | `ChartDisplayComponent.render_engine_selector()` | Engine selection (plotly/matplotlib) |
| `chart_{plot_id}` | (widget key) | `interactive_plotly_chart()` | `ChartDisplayComponent` | Interactive Plotly chart |

**Source**: `src/web/controllers/plot/render_controller.py`, `src/web/components/common/chart_display.py`

---

## 18. Download Section Keys

| Key | Type | Set By | Read By | Purpose |
|-----|------|--------|---------|---------|
| `dl_fmt_{plot_id}` | `str` | Streamlit pills | `download_section` | Selected download format |
| `dl_btn_{plot_id}` | (button key) | Streamlit | `download_section` | Download button |

**Source**: `src/web/pages/ui/plotting/download_section.py`

---

## Domain Repository State (In-Memory, Not in session_state)

These are **not** `st.session_state` keys. They are private attributes on singleton repository objects held via `@st.cache_resource`.

### DataRepository (`src/core/state/repositories/data_repository.py`)

| Field | Type | Default |
|-------|------|---------|
| `_data` | `pd.DataFrame \| None` | `None` |
| `_processed_data` | `pd.DataFrame \| None` | `None` |

### PlotRepository (`src/core/state/repositories/plot_repository.py`)

| Field | Type | Default |
|-------|------|---------|
| `_plots` | `list[PlotProtocol]` | `[]` |
| `_plot_counter` | `int` | `0` |
| `_current_plot_id` | `int \| None` | `None` |

### ConfigRepository (`src/core/state/repositories/config_repository.py`)

| Field | Type | Default |
|-------|------|---------|
| `_config` | `dict[str, Any]` | `{}` |
| `_temp_dir` | `str \| None` | `None` |
| `_csv_path` | `str \| None` | `None` |
| `_csv_pool` | `list[CsvPoolEntry]` | `[]` |
| `_saved_configs` | `list[SavedConfigEntry]` | `[]` |

### ParserStateRepository (`src/core/state/repositories/parser_state_repository.py`)

| Field | Type | Default |
|-------|------|---------|
| `_parse_variables` | `list[ParseVariableConfig]` | 3 default vars |
| `_stats_path` | `str` | `"/path/to/stats"` |
| `_stats_pattern` | `str` | `"stats.txt"` |
| `_scanned_variables` | `list[ScannedVariableDict]` | `[]` |
| `_use_parser` | `bool` | `False` |
| `_parser_strategy` | `str` | `"simple"` |
| `_simulator` | `str` | `"gem5"` |

### PreviewRepository (`src/core/state/repositories/preview_repository.py`)

| Field | Type | Default |
|-------|------|---------|
| `_previews` | `dict[str, DataFrame]` | `{}` |

Known operation keys: `"preprocessor"`, `"seeds_reduction"`, `"outlier_removal"`, `"mixer"`

### HistoryRepository (`src/core/state/repositories/history_repository.py`)

| Field | Type | Default | Cap |
|-------|------|---------|-----|
| `_manager_history` | `list[OperationRecord]` | `[]` | 10 (FIFO) |
| `_portfolio_history` | `list[OperationRecord]` | `[]` | Unbounded |

### VisualizationRepository (`src/core/state/repositories/visualization_repository.py`)

| Field | Type | Default |
|-------|------|---------|
| `_configs` | `dict[int, FigureConfig]` | `{}` |

---

## Key Naming Conventions

```
UIStateManager keys:
  plot.{plot_id}.{suffix}          # Plot UI state
  manager.{manager_name}.{suffix}  # Data manager UI state
  nav.{suffix}                     # Navigation state
  export.{suffix}                  # Export state

WidgetKeyBuilder:
  WidgetKeyBuilder.plot_key(1, "auto_refresh")    -> "plot.1.auto_refresh"
  WidgetKeyBuilder.manager_key("mixer", "mode")   -> "manager.mixer.mode"
  WidgetKeyBuilder.global_key("theme")            -> "g.theme"

Direct widget keys (outside UIStateManager):
  {feature}_{plot_id}              # e.g., x_filter_1, hm_metrics_2
  {prefix}_{detail}_{plot_id}      # e.g., theme_bg_plot_1
  {component}_{var_id}             # e.g., var_name_abc123
```

---

## State Lifecycle Summary

```
Bootstrap:
  app.py -> @st.cache_resource get_api() -> ApplicationAPI (singleton)
         -> st.session_state.api = api
         -> st.session_state["_nav_page"] = "Data Source"

Data loaded:
  data_repo._data = DataFrame
  config_repo._csv_path = "/path/to/file.csv"

Plot created:
  plot_repo._plots.append(plot)
  plot_repo._current_plot_id = new_id
  st.session_state["plot.{id}.auto_refresh"] = True

Preview workflow:
  preview_repo._previews["preprocessor"] = df  (preview)
  data_repo._data = confirmed_df               (confirm)
  preview_repo._previews.pop("preprocessor")   (clear)

Plot deleted:
  plot_repo._plots.remove(plot)
  visualization_repo._configs.pop(plot_id)
  UIStateManager.plot.cleanup(plot_id)          (removes all plot.{id}.* keys)

Session clear:
  SessionRepository.clear_all()                 (all repos reset)
  UIStateManager.cleanup_all()                  (all UI keys removed)

Portfolio restore:
  SessionRepository.restore_from_portfolio()    (repos populated from JSON)
  st.rerun(scope="app")                         (full re-render)
```

---

## Not Serialized to Portfolio

- All `st.session_state` UI keys (transient)
- `preview_repo._previews` (temporary)
- `visualization_repo._configs` (rebuilt on render)
- `data_repo._processed_data` (rebuilt by pipeline)
- Matplotlib figure objects (`plot.{id}.mpl_fig`)
- Plot figure cache (`SimpleCache`, 32 entries, 5 min TTL)
