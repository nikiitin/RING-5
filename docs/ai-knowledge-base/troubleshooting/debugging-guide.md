---
title: "Debugging Guide"
parent: Troubleshooting
grand_parent: AI Knowledge Base
nav_order: 2
---

# Debugging Guide

> AI-optimized reference. No prose -- tables, bullets, code blocks only.

---

## Layer-by-Layer Debugging

### Layer A -- Core (`src/core/`)

| Property | Detail |
|----------|--------|
| Dependencies | Pure Python + pandas + numpy. NO Streamlit, NO Plotly, NO matplotlib |
| Test runner | `./python_venv/bin/pytest tests/unit/ -v` |
| Isolation | Can run tests without any UI or rendering stack |
| Key constraint | NEVER imports `streamlit`, `plotly`, or `matplotlib` |

- **Models** (`src/core/models/`): Pydantic-style dataclasses, discriminated unions
- **Services** (`src/core/services/`): Business logic, shaper pipeline, validation
- **State** (`src/core/state/`): `RepositoryStateManager` -- single source of truth

```bash
# Debug a specific core test
./python_venv/bin/pytest tests/unit/test_application_api.py -v -s

# Type-check core in isolation
./python_venv/bin/mypy src/core/ --show-error-codes
```

### Layer A -- Parsing (`src/parsing/`)

| Property | Detail |
|----------|--------|
| Key classes | `Gem5Parser`, `PerlWorkerPool`, `WorkPool` |
| Subprocess | Perl scripts via `PerlWorkerPool` (pool of persistent Perl processes) |
| Parallelism | `WorkPool` singleton: `ProcessPoolExecutor` + `ThreadPoolExecutor` |
| Pool status | `WorkPool.get_instance()` -- check `_process_executor`, `_thread_executor` |

- **Check WorkPool status**:
  ```python
  from src.parsing.framework.work_pool import WorkPool
  pool = WorkPool.get_instance()
  print(pool._process_executor)  # None = not yet created
  print(pool._thread_executor)   # None = not yet created
  ```
- **Check PerlWorkerPool health**:
  ```python
  from src.parsing.gem5.impl.strategies.perl_worker_pool import PerlWorkerPool
  pool = PerlWorkerPool(pool_size=4)
  print(pool.stats())  # worker count, jobs processed, failures
  ```

```bash
# Run parsing tests (uses xdist_group for sequential execution)
./python_venv/bin/pytest tests/unit/test_perl_worker_pool.py -v -s

# Integration: full scan/parse workflow
./python_venv/bin/pytest tests/integration/test_gem5_parsing.py -v -s
```

### Layer C -- Web (`src/web/`)

| Property | Detail |
|----------|--------|
| Framework | Streamlit (entire script re-executes on every interaction) |
| State | `st.session_state` -- persists across reruns, managed via `UIStateManager` |
| Components | Self-contained widgets in `src/web/components/` |
| Controllers | `src/web/controllers/` -- orchestrate components, services, state |
| Rendering | `src/web/rendering/` -- Plotly + matplotlib connectors |

- Streamlit reruns the ENTIRE `app.py` on every widget interaction
- `@st.fragment` isolates partial reruns (see Fragment section below)
- Widget keys must be globally unique across all pages

```bash
# Run with debug logging
streamlit run app.py --logger.level=debug

# Streamlit AppTest-based UI tests
./python_venv/bin/pytest tests/ui/ -v -s
```

---

## ApplicationAPI Debug Entry Points

`src/core/application_api.py` is the single facade between Web and Core.

| Method | Data Flow Stage | What It Does |
|--------|-----------------|--------------|
| `submit_scan_async()` | Scanning | Submit parallel gem5 stats scanning jobs |
| `finalize_scan()` | Scanning | Aggregate scan results into variable list |
| `submit_parse_async()` | Parsing | Submit parallel parsing jobs |
| `finalize_parsing()` | Parsing | Merge parse results, produce CSV |
| `load_data()` | Data load | Load CSV into state, set `raw_data` |
| `load_from_pool()` | Data load | Load from CSV pool service |
| `get_current_view()` | Inspection | Returns `{"raw_data": df, "config": dict}` |
| `apply_shapers()` | Transform | Apply shaper pipeline to data |
| `get_preview()` | Transform | Preview result of a manager operation |
| `get_visualization_config()` | Plotting | Get `FigureConfig` for a plot ID |
| `save_configuration()` | Persistence | Save pipeline config to JSON |
| `load_configuration()` | Persistence | Load pipeline config from JSON |

```python
# Quick debug: inspect current application state
api = st.session_state.api  # ApplicationAPI singleton
view = api.get_current_view()
print(view["raw_data"].shape if view["raw_data"] is not None else "No data loaded")
print(view["config"])
```

---

## Streamlit-Specific Debugging

### Double Reruns from `st.rerun()`

| Location | Trigger | Notes |
|----------|---------|-------|
| `app.py:87` | Navigation button click | Sets `_nav_page`, calls `st.rerun()` |
| `app.py:100` | "Clear Data" button | Calls `api.reset_session()` then `st.rerun()` |
| `app.py:109` | "Reset All" button | Calls `api.reset_session()` then `st.rerun()` |
| Various controllers | After state mutations | Should use `scope="app"` for global changes |

- **Known issue**: 3-4 `st.rerun()` calls missing `scope="app"` parameter
- **Symptom**: Navigation/global state changes cause full-app rerun instead of scoped rerun
- **Debug**: Add `print("RERUN", time.time())` at top of `run_app()` to trace rerun frequency

### Cache Invalidation

| Cache Type | Mechanism | Location |
|------------|-----------|----------|
| `ApplicationAPI` singleton | `@st.cache_resource` | `app.py:54-56` |
| Figure generation | Manual hash cache (`SimpleCache`) | `src/web/controllers/plot/render_controller.py:206` |
| Data fingerprint | MD5 of shape + sample rows + params | `src/core/performance.py:210-243` |
| Global plot cache | `SimpleCache(maxsize=32, ttl=300)` | `src/core/performance.py:97` |

- **`@st.cache_resource`**: Persists across reruns, cleared only on code change or manual `st.cache_resource.clear()`
- **Manual hash cache**: `_compute_figure_cache_key(plot_id, config, data_hash)` in render controller
- **Cache miss debugging**:
  ```python
  from src.core.performance import get_cache_stats
  print(get_cache_stats())  # {"plot_cache": {"hits": N, "misses": M, "size": S, "hit_rate": R}}
  ```

### Fragment Isolation (`@st.fragment`)

| Fragment | File:Line | Scope |
|----------|-----------|-------|
| `_data_preview_fragment()` | `app.py:115-135` | Data metrics display (rows/cols/source) |

- **Purpose**: Fragment reruns independently when its internal widgets change, without triggering full-app rerun
- **Anti-pattern**: NEVER define `@st.fragment` inside a loop or parent render function
- **Rule**: Always define fragments at module level, pass state as arguments
- **More**: see `developer-guide/web/streamlit-best-practices.md` and `/CLAUDE.md`

### Widget State Lifecycle

```
User clicks widget
  --> Streamlit sets widget value in session_state[widget_key]
  --> Full script re-executes from top (or fragment re-executes if inside @st.fragment)
  --> Widget re-renders with new value from session_state
  --> If st.rerun() called: ANOTHER full re-execution
```

- **Widget key collisions**: Keys must be globally unique. Duplicate keys cause `DuplicateWidgetID` error
- **Pre-initialization pattern**: `filtered_selector.py:160` sets widget defaults before rendering (intentional workaround, not anti-pattern)
- **Inspection**:
  ```python
  # Dump all session state keys
  for k, v in sorted(st.session_state.items()):
      print(f"{k}: {type(v).__name__} = {repr(v)[:80]}")
  ```

---

## Common Debugging Commands

### Test Commands

```bash
# Run all tests (parallel, 3 workers)
make test

# Run specific test file
./python_venv/bin/pytest tests/unit/test_application_api.py -v

# Run tests matching keyword
./python_venv/bin/pytest tests/ -k "test_shaper" -v

# Run with output capture disabled (see print statements)
./python_venv/bin/pytest tests/unit/test_shapers_extended.py -v -s

# Run single test class or method
./python_venv/bin/pytest tests/unit/test_plot_factory.py::TestPlotFactory::test_create -v

# Integration tests only
./python_venv/bin/pytest tests/integration/ -v

# UI AppTest tests only
./python_venv/bin/pytest tests/ui/ -v -s
```

### Quality Gate Commands

```bash
# Architecture boundary check (all must return empty)
grep -rn "import streamlit\|from streamlit" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "session_state" src/core/ --include="*.py" | grep -v __pycache__
grep -rn "inplace=True" src/ --include="*.py" | grep -v __pycache__

# Type check
./python_venv/bin/mypy src/ --show-error-codes

# Format check
./python_venv/bin/black --check src/ tests/

# Lint
./python_venv/bin/flake8 src/ tests/

# Security scan
./python_venv/bin/bandit -r src/ -ll
```

### Streamlit Debug Commands

```bash
# Run app with debug logging
streamlit run app.py --logger.level=debug

# Run app on specific port
streamlit run app.py --server.port=8502

# Check for orphaned Perl processes (known issue)
ps aux | grep perl | grep -v grep

# Kill orphaned Perl workers
pkill -f "perl.*ring5"
```

---

## Test Directory Quick Reference

| Directory | Count | Scope | Framework |
|-----------|-------|-------|-----------|
| `tests/unit/` | ~100+ files | Pure unit tests, mocked dependencies | pytest |
| `tests/integration/` | ~35 files | Real `ApplicationAPI`, service-level | pytest |
| `tests/ui/` | ~10 files | Streamlit `AppTest` framework | pytest + AppTest |
| `tests/ui_unit/` | varies | Mocked `st` module | pytest |
| `tests/ui_logic/` | varies | Controller-level `@patch` | pytest |
| `tests/visual/` | varies | Playwright browser tests (excluded from default) | pytest + Playwright |
| `tests/performance/` | varies | Benchmark suite with timing thresholds | pytest |
| `tests/helpers/` | 3 files | NOT test files -- shared utilities | N/A |

- **Excluded from default runs**: `tests_principle_compliance/`, `tests/manual/`, `tests/data/`, `tests/visual/`
- **Parallel execution**: Default `-n 3 --dist loadgroup`
- **Sequential-sensitive tests**: Use `@pytest.mark.xdist_group` marker
