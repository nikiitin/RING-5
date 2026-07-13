---
title: "Error Handling Patterns -- Quick Reference"
parent: Quick Reference
grand_parent: Engineering Reference
nav_order: 4
---

# Error Handling Patterns -- Quick Reference

## Guiding rules

- **NEVER** use bare `except:` -- catch specific exceptions
- **NEVER** guess data values -- if regex fails to match, raise or log, never fabricate
- UI layer catches and shows `st.error()` with friendly messages
- Log full stack traces to console via `logging.getLogger(__name__)`

---

## Layer 1: Core Services

### Exception Types Used

| Exception | Raised By | Trigger |
|---|---|---|
| `ValueError` | `ArithmeticService` | Unknown operation in `apply_operation` / `apply_mixer` |
| `ValueError` | `ShaperFactory` | Unknown shaper type (includes available types in message) |
| `ValueError` | `Shaper` base | Non-dict params, None params, None DataFrame, empty DataFrame |
| `ValueError` | `UniDfShaper` | Input is not a `pd.DataFrame` instance |
| `ValueError` | `Mean` shaper | Invalid algorithm, missing columns, non-numeric columns |
| `ValueError` | `Selector` shaper | Missing/empty `column` param, column not in DataFrame |
| `ValueError` | `PipelineService` | Empty pipeline name; wraps per-shaper errors |
| `ValueError` | `PortfolioService` | Empty portfolio name |
| `ValueError` | `CsvPoolService` | Empty/whitespace CSV path |
| `ValueError` | `CsvContract` | Empty CSV file, empty header row |
| `ValueError` | `PatternIndexService` | Mismatched `\d+` placeholder count |
| `FileNotFoundError` | `CsvPoolService` | Resolved path does not exist |
| `FileNotFoundError` | `PipelineService` | Pipeline JSON file not found |
| `FileNotFoundError` | `PortfolioService` | Portfolio file not found |
| `FileNotFoundError` | `CsvContract` | CSV file does not exist |
| `IsADirectoryError` | `CsvPoolService` | Path points to directory, not file |
| `IndexError` | `VariableService` | Out-of-bounds index on `update_variable` / `delete_variable` |
| `TypeError` | `Mean` shaper | `meanVars` not a list |

### Validation Pattern (list[str])

All manager services return error lists -- empty means valid.

```python
# ArithmeticService, OutlierService, ReductionService
errors: list[str] = service.validate_inputs(df, ...)
if errors:
    for e in errors:
        st.error(e)  # web layer responsibility
    return
```

### Shaper Validation Pattern (tuple)

```python
# src/core/services/shapers/validation.py
is_valid, missing_fields = validate_shaper_config(shaper_type, config)
# Returns (True, None) or (False, ["field1", "field2"])
```

### Graceful Degradation Patterns

| Pattern | Where | Behavior |
|---|---|---|
| Early return on empty | `OutlierService.remove_outliers` | Returns `df` unchanged if empty or column missing |
| Return `False` on failure | `CsvPoolService.delete_from_pool` | Catches `OSError`/`ValueError`, logs warning |
| Return `False` on failure | `ConfigService.delete_configuration` | Catches `OSError`, logs warning |
| Fallback value | `palette_service.resolve_palette` | Invalid input falls back to `"wong"` palette |
| Return `[]` on missing path | `ApplicationAPI.find_stats_files` | Returns empty list if path doesn't exist |
| Null safety | `ApplicationAPI.get_column_info(None)` | Returns zero-count `ColumnInfoResult` |
| Safe regex | `VariableService._compile_safe_pattern` | Returns `None` on failure, triggers exact-match fallback |

---

## Layer 2: Parsing

### File I/O Errors

```python
# src/parsing/gem5/impl/gem5_parser.py
if not search_path.exists():
    raise FileNotFoundError(f"Stats path does not exist: {stats_path}")

# src/parsing/gem5/impl/gem5_parser.py
if not stats_path.exists():
    raise FileNotFoundError(f"Stats path does not exist: {stats_path}")
if not stats_files:
    raise FileNotFoundError("No stats files found.")
```

### Regex Failures

```python
# gem5_parser.py -- invalid regex in variable name
except re.error:
    logger.warning(f"PARSER: Invalid regex in variable: {config.name}")
    # Falls through to append unexpanded config
```

### Registry Errors

| Exception | Raised By | Trigger |
|---|---|---|
| `KeyError` | `SimulatorRegistry.get_parser` | Unknown simulator name |
| `KeyError` | `SimulatorRegistry.get_info` | Unknown simulator name |
| `ValueError` | `SimulatorRegistry.register` | Duplicate simulator name |
| `ValueError` | `SimulatorInfo.__post_init__` | No parsing strategies defined |
| `ValueError` | `StrategyFactory.create` | Unknown strategy type |

### Distribution Type Errors

| Exception | File | Trigger |
|---|---|---|
| `ValueError` | `distribution.py` | Mismatched bucket/value lengths |
| `TypeError` | `distribution.py` | Content not dict; unexpected value type |
| `RuntimeError` | `distribution.py` | Unit extraction failure; sum validation failure |

---

## Layer 3: Web (Presentation)

### Pattern: st.error() + logger

```python
# src/web/pages/ui/shaper_config.py (canonical example)
try:
    shaper = ShaperFactory.create_shaper(shaper_type, shaper_cfg)
    result = shaper(result)
except ValueError as e:
    st.error(f"Pipeline step {idx + 1} ({shaper_type}): Configuration error - {e}")
    logger.error(f"PIPELINE: Config validation failed for {shaper_type}: {e}")
    raise ValueError(error_msg) from e
except KeyError as e:
    st.error(f"Pipeline step {idx + 1} ({shaper_type}): Missing column - {e}")
    logger.error(f"PIPELINE: Data validation failed for {shaper_type}: {e}")
    raise KeyError(error_msg) from e
except Exception as e:
    st.exception(e)  # shows full traceback in UI
    logger.error(f"PIPELINE: Transformation failed: {e}", exc_info=True)
    raise
```

### Pattern: render_controller.py catch-and-flag

```python
# src/web/controllers/plot/render_controller.py
try:
    ui_config = plot.render_config_ui(data, saved_config)
except Exception as e:
    st.exception(e)
    logger.error("RENDER: Type config failed for plot %r: %s", plot.name, e, exc_info=True)
    config_error = True  # flag prevents downstream rendering
```

### Common st.error() Messages

| Message | File | Trigger |
|---|---|---|
| `"No data available. Please load data first."` | `seeds_reducer.py`, `preprocessor.py`, `outlier_remover.py` | `data is None` |
| `"No data loaded."` | `mixer.py` | `data is None` |
| `"File no longer exists: ..."` | `data_source_components.py` | Pool file deleted externally |
| `"Please specify a stats directory path."` | `data_source_components.py` | Empty path field |
| `"Variable name is required."` | `data_source_components.py` | Empty variable name |
| `"Invalid Regex Pattern"` | `pivot_config.py` | Bad regex in pivot filter |

---

## Layer 4: Service Layer (ApplicationAPI)

### Try-Catch + Re-Raise

```python
# src/core/application_api.py
def load_data(self, csv_path: str) -> None:
    try:
        df = self._services.data_services.load_csv_file(csv_path)
        self.state_manager.set_data(df)
    except Exception as e:
        logger.error(f"Failed to load data from {csv_path}: {e}")
        raise  # re-raise to caller (web layer)
```

---

## Common Error Scenarios

| Scenario | Layer | Handling | Key File |
|---|---|---|---|
| CSV file not found | Core | `FileNotFoundError` raised | `csv_pool_service.py` |
| CSV path is directory | Core | `IsADirectoryError` raised | `csv_pool_service.py` |
| Empty DataFrame to shaper | Core | `ValueError("empty dataframe")` | `shaper.py` |
| Unknown shaper type | Core | `ValueError` with available types list | `factory.py` |
| Missing shaper params | Core | `(False, missing_fields)` tuple | `validation.py` |
| Division by zero | Core | Silent replace: `s2.replace(0, np.nan)` | `arithmetic_service.py` |
| Invalid regex pattern | Parsing | `logger.warning`, skip expansion | `gem5_parser.py` |
| Stats path not found | Parsing | `FileNotFoundError` raised | `gem5_parser.py` |
| No stats files found | Parsing | `FileNotFoundError` raised | `gem5_parser.py` |
| Unknown simulator name | Parsing | `KeyError` with available list | `registry.py` |
| Path traversal attempt | Core | `ValueError` from `validate_path_within` | `utils.py` |
| Portfolio not found | Core | `FileNotFoundError` raised | `portfolio_service.py` |
| Plot render crash | Web | `st.exception(e)` + `config_error` flag | `render_controller.py` |
| No data loaded (UI) | Web | `st.error("No data available...")` + early return | Multiple components |
| Pipeline step failure | Web | `st.error()` per step + re-raise | `shaper_config.py` |
| Corrupt config JSON | Core | Skip file, `logger.debug` | `config_service.py` |

---

## Security-Related Error Handling

| Function | File | Protection |
|---|---|---|
| `validate_path_within(path, base)` | `src/core/common/utils.py` | Raises `ValueError` on path traversal |
| `sanitize_filename(name)` | `src/core/common/utils.py` | Strips `/`, `\`, `..`; returns `"unnamed"` for empty |
| `sanitize_glob_pattern(pattern)` | `src/core/common/utils.py` | Allowlist `[a-zA-Z0-9_.*?]`; falls back to `"stats.txt"` |
| `_compile_safe_pattern()` | `variable_service.py` | Max 500 chars, character allowlist, `None` on failure |

---

## Known Gotchas and Warnings

| Issue | Severity | Location | Details |
|---|---|---|---|
| Outlier bug: removes top 25% | CRITICAL | `outlier_service.py:23-24` | Q3 threshold used instead of IQR bounds when IQR=0 (uniform data) |
| SimpleCache lacks thread locks | CRITICAL | `src/core/performance.py` | Docstring says "Thread-safe" but no locks exist |
| CsvPoolService `_pool_index` no lock | CRITICAL | `csv_pool_service.py` | Dict mutation without synchronization |
| WorkPool no `shutdown()` | CRITICAL | `perl_worker_pool.py` | N hot-reloads = N orphaned process pools |
| Zero `plt.close()` calls | HIGH | `matplotlib_connector.py` | matplotlib Figure memory leak |
| matplotlib Figure in session_state | HIGH | `matplotlib_connector.py` | Not serializable, Streamlit warning |
| mixer.py missing None check | HIGH | `mixer.py` | `operation` can be None -> `AttributeError` |
| Mean NaN inconsistency | HIGH | `mean.py:218-226` | `geomean`/`hmean` propagate NaN; `arithmean` skips NaN |
