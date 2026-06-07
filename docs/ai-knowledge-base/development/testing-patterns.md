---
title: "Testing Patterns"
parent: Development
grand_parent: AI Knowledge Base
nav_order: 5
---

# Testing Patterns

> Scope: pytest configuration, directory layout, fixture hierarchy, mock strategies, per-layer guidance.

---

## pytest Configuration

Source: `pyproject.toml` `[tool.pytest.ini_options]`

```toml
testpaths = ["tests"]
norecursedirs = [
    "tests/tests_principle_compliance",
    "tests/manual",
    "tests/data",
    "tests/visual",
]
pythonpath = ["."]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --tb=short --strict-markers -n 3 --dist loadgroup"
xfail_strict = true
```

| Setting | Value | Why |
|---------|-------|-----|
| `-n 3` | 3 xdist workers | Parallel execution, balanced speed vs resources |
| `--dist loadgroup` | Load-based + grouping | Tests with `xdist_group` marker run on same worker |
| `--strict-markers` | Enabled | Typos in marker names cause errors |
| `xfail_strict` | `true` | Unexpectedly passing `xfail` tests fail the suite |

### Registered Markers

| Marker | Purpose |
|--------|---------|
| `requires_latex` | Skip if XeLaTeX not installed |
| `requires_browser` | Skip if no browser/server |
| `benchmark` | Performance benchmark test |
| `smoke` | Quick smoke test subset |
| `slow` | Long-running test |
| `xdist_group` | Group tests on one worker (shared state) |

### Plugins

| Plugin | Version | Purpose |
|--------|---------|---------|
| `pytest` | >= 9.0.2 | Core framework |
| `pytest-cov` | >= 7.0.0 | Coverage reporting |
| `pytest-xdist` | >= 3.6.1 | Parallel execution |
| `pytest-randomly` | >= 3.16.0 | Random ordering (detects order dependence) |
| `pytest-timeout` | >= 2.2.0 | CI timeout protection |
| `pytest-playwright` | >= 0.7.0 | Browser E2E (optional `e2e` extra) |

---

## Test Directory Structure

```
tests/
+-- conftest.py                    # Root: shared fixtures, pytest_plugins
+-- helpers/
|   +-- benchmark.py               # BenchmarkSuite, timer()
|   +-- gem5_fixtures.py           # Synthetic data path fixtures
|   +-- sample_figures.py          # Plotly figure factories
+-- data/                          # Test data (excluded from discovery)
|   +-- synthetic/                 # Synthetic gem5 stats files
|   +-- mock/                      # Config files, expected CSV outputs
+-- unit/           (~100 files)   # Pure unit tests, mocked deps
+-- integration/    (~35 files)    # Real services, real data
+-- ui/             (~10 files)    # Streamlit AppTest E2E
+-- ui_unit/        (~14 files)    # UI components with mocked st
+-- ui_logic/       (~12 files)    # Controllers with @patch
+-- visual/         (~15 files)    # Playwright browser tests (excluded)
+-- performance/    (2 files)      # Timing threshold benchmarks
```

| Directory | Scope | Dependencies Mocked? |
|-----------|-------|---------------------|
| `unit/` | Single class/function | Yes -- all external deps mocked |
| `integration/` | Multi-component chains | No -- real ApplicationAPI, StateManager |
| `ui/` | Full Streamlit runtime | No -- uses `AppTest.from_file()` |
| `ui_unit/` | Single UI component | Yes -- `st` module fully patched |
| `ui_logic/` | Controller orchestration | Partially -- `st` + Component.render patched |
| `visual/` | Browser visual tests | No -- real server + Playwright |
| `performance/` | Timing regressions | No -- real services with benchmarks |

---

## Key Fixtures

### Root `tests/conftest.py`

| Fixture | Scope | Returns | Used By |
|---------|-------|---------|---------|
| `mock_api` | function | `MagicMock` with `.state_manager` | ~90% of UI tests |
| `sample_data` | function | 6-row DataFrame (benchmark, config, metrics) | Unit + UI |
| `sample_data_extended` | function | 6-row + extra numeric columns | Unit |
| `mock_state_manager` | function | `MagicMock` RepositoryStateManager | Unit |
| `e2e_sample_data` | function | 18-row x 8-col rich DataFrame | UI E2E |
| `_cleanup_perl_worker_pool` | session (autouse) | -- | All (prevents ResourceWarning) |

### Plugin-registered: `tests/helpers/gem5_fixtures.py`

Registered via `pytest_plugins = ["tests.helpers.gem5_fixtures"]`

| Fixture | Returns |
|---------|---------|
| `synthetic_stats_root` | Path to `tests/data/synthetic/` |
| `synthetic_single_stats` | Single-benchmark stats dir |
| `synthetic_multi_cpu_stats` | Multi-CPU pattern stats dir |
| `synthetic_histogram_stats` | Histogram data with bins |
| `synthetic_benchmarks_dir` | Multi-benchmark dir tree |

### Integration `tests/integration/conftest.py`

| Fixture | Scope | Returns |
|---------|-------|---------|
| `_reset_service_caches` | function (autouse) | Resets PathService, CsvPoolService, ConfigService |
| `facade` | function | Real `ApplicationAPI()` |
| `state_manager` | function | Real `RepositoryStateManager()` with `clear_all()` |
| `loaded_facade` | function | `ApplicationAPI` with data pre-loaded |
| `bar_config` / `line_config` / etc. | function | Minimal plot config dicts |

### UI Logic `tests/ui_logic/conftest.py`

| Fixture | Returns |
|---------|---------|
| `StubPlotHandle` | Lightweight concrete class satisfying PlotHandle protocol |
| `mock_lifecycle` | Mock `PlotLifecycleService` |
| `mock_registry` | Mock `PlotTypeRegistry` (8 types) |
| `mock_pipeline_executor` | Mock `PipelineExecutor` returning sample_data |

---

## Mock Patterns

### Three-Tier Streamlit Mocking

```
+-------------------+   +----------------------+   +-------------------+
| Tier 1: ui_unit/  |   | Tier 2: ui_logic/    |   | Tier 3: ui/       |
| Full st patch     |   | Controller-level     |   | Real AppTest      |
| patch("...mod.st")|   | @patch("...ctrl.st") |   | AppTest.from_file |
| Highest isolation |   | Mid isolation        |   | Highest fidelity  |
| Fastest           |   | Medium speed         |   | Slowest           |
+-------------------+   +----------------------+   +-------------------+
```

### Tier 1 -- Full Module Patch (ui_unit)

```python
# tests/ui_unit/test_data_manager_logic.py
@pytest.fixture
def mock_streamlit() -> Generator:
    with (
        patch("src.web.components.data_managers.seeds_reducer.st") as mock_st,
        patch("src.web.components.data_managers.seeds_reducer.UIStateManager") as mock_ui,
    ):
        mock_st.session_state = {}
        mock_st.columns.side_effect = columns_side_effect  # from root conftest
        yield mock_st
```

### Tier 2 -- Controller Patch (ui_logic)

```python
# tests/ui_logic/test_creation_controller.py
@patch("src.web.controllers.plot.creation_controller.st")
@patch("src.web.controllers.plot.creation_controller.PlotCreationComponent.render")
def test_create_delegates(self, mock_render, mock_st):
    mock_render.return_value = {
        "name": "My Plot", "plot_type": "bar", "create_clicked": True,
    }
    ctrl = _make_controller(lifecycle=mock_lifecycle)
    ctrl.render_create_section()
    mock_lifecycle.create_plot.assert_called_once()
```

### Tier 3 -- Real AppTest Runtime (ui)

```python
# tests/ui/helpers.py
def create_app_with_data(df=None) -> AppTest:
    at = AppTest.from_file("app.py", default_timeout=10)
    at.run()
    api = at.session_state["api"]
    api.reset_session()
    api.state_manager.set_data(df or make_e2e_sample_data())
    api.state_manager.set_processed_data(df.copy() if df else make_e2e_sample_data())
    return at
```

### ApplicationAPI Mock Patterns

| Strategy | Where | Code |
|----------|-------|------|
| Full mock | Root conftest | `mock_api = MagicMock(); mock_api.state_manager = MagicMock()` |
| Partial mock | Unit tests | `patch("src.core.application_api.RepositoryStateManager")` + `patch("...DefaultServicesAPI")`, real `ApplicationAPI()` |
| Real instance | Integration | `facade = ApplicationAPI()` -- no patches |

### session_state Mock

```python
# For ui_unit tests -- dict-backed session_state
mock_st.session_state = {}

# For button simulation -- side_effect by key
apply_key = WidgetKeyBuilder.manager_key("seeds_reducer", "apply")
mock_st.button.side_effect = lambda label, key=None, **kw: key == apply_key
```

---

## What to Test Per Layer

### Core Layer (src/core/)

- **Pattern**: Pure functions, no Streamlit imports
- **Strategy**: Direct function calls, no mocks needed for logic
- **Mock**: Only StateManager when testing ApplicationAPI orchestration

| What | Example |
|------|---------|
| Shaper transforms | `Sort(params)(dataframe)` returns correctly sorted DataFrame |
| Model validation | `FigureConfig` rejects invalid sentinel values |
| Service delegation | `ApplicationAPI.load_data()` calls `data_services.load_csv_file()` |

### Parsing Layer (src/parsing/)

- **Pattern**: File I/O + parallel workers
- **Strategy**: Use `tmp_path` fixture with synthetic stats files

| What | Example |
|------|---------|
| Variable scanning | `submit_scan_async()` discovers expected variables |
| Stats parsing | `submit_parse_async()` + `finalize_parsing()` produces valid CSV |
| Edge cases | Empty file, missing fields, malformed lines |

### Web Layer (src/web/)

- **Pattern**: Streamlit widgets + controller orchestration
- **Strategy**: Three-tier mock approach (see above)

| What | Example |
|------|---------|
| Widget rendering | Component `.render()` returns correct config dict |
| Controller flow | `PlotCreationController` calls lifecycle on create click |
| Engine switching | `EngineManager.set_engine("matplotlib")` updates state |
| Style pipeline | `FigureSpecToPlotly.apply()` produces valid figure |

---

## Coverage Configuration

Source: `pyproject.toml` `[tool.coverage.run]`

```toml
[tool.coverage.run]
omit = [
    "src/web/pages/ui/plotting/types/dual_axis_bar_dot_plot.py",
]
```

- Only 1 omission: WIP `dual_axis_bar_dot_plot.py`
- Also filtered at runtime: `-k "not dual_axis and not dual"`
- ~20 dedicated `*_coverage.py` test files target branch gaps

### Performance Thresholds

Source: `tests/performance/test_performance_regression.py`

| Operation | Threshold | Iterations |
|-----------|-----------|------------|
| Bar plot generation | < 500ms | 5 |
| Grouped bar plot | < 800ms | 3 |
| Normalize shaper (2000 rows) | < 200ms | 5 |
| Full pipeline | < 1000ms | 1 |
| CSV metadata caching speedup | >= 5x | -- |
| CSV loading cache speedup | >= 2x | -- |

---

## Test File Naming Conventions

| Pattern | Purpose | Example |
|---------|---------|---------|
| `test_<module>.py` | Standard test file | `test_application_api.py` |
| `test_<module>_coverage.py` | Branch coverage gaps | `test_mixer_coverage.py` |
| `test_<module>_branches.py` | Specific branch paths | `test_normalize_branches.py` |
| `test_<module>_comprehensive.py` | Full module coverage | `test_scanner_comprehensive.py` |
| `test_e2e_<workflow>.py` | End-to-end flow | `test_e2e_full_chain.py` |

---

## Common Test Patterns

### Arrange-Act-Assert

```python
def test_load_data_success(self, application_api):
    # Arrange
    df = pd.DataFrame({"col": [1, 2]})
    mock_data = cast(Any, application_api)._mock_services.data_services
    mock_data.load_csv_file.return_value = df
    # Act
    application_api.load_data("/test/data.csv")
    # Assert
    mock_data.load_csv_file.assert_called_once_with("/test/data.csv")
```

### Registry Cleanup (global state isolation)

```python
def test_register_custom_type(self):
    try:
        PlotFactory.register_plot_type("test_custom", BarPlot, metadata=meta)
        assert "test_custom" in PlotFactory.get_plot_metadata()
    finally:
        PlotFactory._plot_classes.pop("test_custom", None)
        PlotFactory._plot_metadata.pop("test_custom", None)
```

### Integration Cache Reset (autouse)

```python
# tests/integration/conftest.py
@pytest.fixture(autouse=True)
def _reset_service_caches():
    PathService.reset_caches()
    CsvPoolService.clear_caches()
    ConfigService.reset_caches()
    yield
    PathService.reset_caches()
    CsvPoolService.clear_caches()
    ConfigService.reset_caches()
```

### DataFrame Assertions

```python
pd.testing.assert_frame_equal(result, expected)      # Exact equality
assert "value.sd" in reduced.columns                  # Column exists
assert len(cleaned) == 9                              # Row count
assert 1000 not in cleaned["value"].values            # Value absent
assert np.isclose(result["col"].iloc[0], expected)    # Float tolerance
```
