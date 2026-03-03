# E2E Testing Suite Implementation Plan

> Source analysis: Steps 16, 21-30 (testing architecture, Playwright, Serenity BDD,
> and 8 test suite designs).

---

## 1. Testing Framework

### Stack
- **Test runner**: pytest + pytest-playwright
- **Browser automation**: Playwright (Python bindings)
- **BDD layer**: pytest-bdd (Gherkin feature files)
- **Pattern**: Serenity Screenplay (adapted for Python)
- **Assertions**: pytest + custom Streamlit assertions
- **Visual regression**: pixelmatch or playwright built-in
- **CI runner**: GitHub Actions with headless Chromium

### Why Playwright for Streamlit?
- Streamlit renders as a standard web app (React frontend)
- Playwright can interact with Streamlit widgets via CSS selectors
- `data-testid` attributes available on Streamlit elements
- Network interception for controlling async operations

---

## 2. State Snapshot Tier System

Designed in Step 21, used across Steps 23-30.

| Tier | Name | State | Created By |
|------|------|-------|------------|
| 0 | Empty | Fresh app, no data loaded | Default |
| 1 | Parsed | CSV loaded, data in session_state | Load fixture CSV |
| 2 | With Plot | Tier 1 + one bar plot created | Create plot via UI |
| 3 | With Shaper | Tier 2 + shaper pipeline applied | Apply column selector |
| 4 | With Preset | Tier 3 + export preset applied | Apply "single_column" |

### Fixture Implementation
```python
@pytest.fixture
def tier0_app(page):
    """Fresh app with no data."""
    page.goto("http://localhost:8501")
    return page

@pytest.fixture
def tier1_app(tier0_app):
    """App with CSV data loaded."""
    # Navigate to Data Source, load fixture CSV
    ...

@pytest.fixture
def tier2_app(tier1_app):
    """App with a bar plot created."""
    # Navigate to Manage Plots, create bar plot
    ...
```

---

## 3. Page Object Models

### 5 Page Objects (from Step 21)

```python
class DataSourcePage:
    """Page object for Data Source page."""
    URL = "http://localhost:8501"

    def __init__(self, page):
        self.page = page

    def navigate(self):
        self.page.click("text=Data Source")

    def load_csv(self, path):
        ...

    def scan_files(self, path, pattern="stats.txt"):
        ...

    def get_loaded_data_preview(self):
        ...

class DataManagersPage: ...
class ManagePlotsPage: ...
class PortfolioPage: ...
class DocumentationPage: ...
```

---

## 4. Test Suites

### Suite 1: Data Source (Step 23 — 752 lines of design)
```
tests/e2e/test_data_source/
├── features/
│   ├── csv_pool.feature          # CSV pool management
│   ├── file_scanning.feature     # Stats file discovery
│   ├── variable_scanning.feature # Variable discovery
│   ├── variable_editor.feature   # Variable CRUD
│   ├── parsing.feature           # Parse execution
│   └── error_handling.feature    # Error scenarios
├── test_csv_pool.py
├── test_scanning.py
├── test_parsing.py
└── conftest.py                   # Tier 0 fixtures
```

### Suite 2: Data Managers (Step 24 — 1,063 lines of design)
```
tests/e2e/test_data_managers/
├── features/
│   ├── preprocessor.feature      # Arithmetic operations
│   ├── seeds_reducer.feature     # Group + reduce
│   ├── outlier_remover.feature   # IQR removal
│   ├── mixer.feature             # Column merge
│   └── history.feature           # Operation history
├── test_preprocessor.py
├── test_seeds_reducer.py
├── test_outlier_remover.py
├── test_mixer.py
└── conftest.py                   # Tier 1 fixtures
```

### Suite 3: Plot Types (Step 25 — 736 lines of design)
```
tests/e2e/test_plot_types/
├── features/
│   ├── bar_plot.feature
│   ├── line_plot.feature
│   ├── scatter_plot.feature
│   ├── grouped_bar.feature
│   ├── stacked_bar.feature
│   ├── heatmap.feature
│   └── dual_axis.feature
├── test_bar_plot.py
├── test_line_plot.py
├── ...
└── conftest.py                   # Tier 1 fixtures
```

### Suite 4: Settings Pills (Step 26 — 863 lines of design)
```
tests/e2e/test_settings/
├── features/
│   ├── layout.feature
│   ├── typography.feature
│   ├── axes.feature
│   ├── legend.feature
│   ├── colors.feature
│   ├── data_labels.feature
│   ├── ordering.feature
│   └── engine.feature
├── test_layout.py
├── test_typography.py
├── ...
└── conftest.py                   # Tier 2 fixtures
```

### Suite 5: Shaper Pipeline (Step 27 — 629 lines of design)
```
tests/e2e/test_shapers/
├── features/
│   ├── column_selector.feature
│   ├── item_selector.feature
│   ├── sort.feature
│   ├── mean.feature
│   ├── normalize.feature
│   ├── pivot.feature
│   ├── pipeline_management.feature
│   └── pipeline_save_load.feature
├── test_selectors.py
├── test_aggregations.py
├── test_pipeline.py
└── conftest.py                   # Tier 1 fixtures
```

### Suite 6: Engine Comparison (Step 28 — 650 lines of design)
```
tests/e2e/test_engines/
├── features/
│   ├── engine_switching.feature
│   ├── feature_parity.feature
│   ├── visual_regression.feature
│   └── export_formats.feature
├── test_engine_switch.py
├── test_visual_comparison.py
├── test_exports.py
└── conftest.py                   # Tier 2 fixtures
```

### Suite 7: Export Presets (Step 29 — 916 lines of design)
```
tests/e2e/test_export/
├── features/
│   ├── preset_application.feature
│   ├── png_export.feature
│   ├── svg_export.feature
│   ├── pdf_export.feature
│   └── venue_presets.feature
├── test_presets.py
├── test_downloads.py
└── conftest.py                   # Tier 2 fixtures
```

### Suite 8: Portfolio Cross-Page (Step 30 — 648 lines of design)
```
tests/e2e/test_portfolio/
├── features/
│   ├── save.feature
│   ├── load.feature
│   ├── delete.feature
│   ├── round_trip.feature
│   ├── cross_page.feature
│   └── visual_regression.feature
├── test_save_load.py
├── test_cross_page.py
├── test_visual_regression.py
└── conftest.py                   # Tier 3 fixtures
```

---

## 5. Implementation Order

| Phase | Suite | Prerequisites | Est. Tests |
|-------|-------|---------------|------------|
| 1 | Infrastructure setup | None | 0 (config only) |
| 2 | Data Source (Suite 1) | Tier 0 fixtures | ~25 |
| 3 | Data Managers (Suite 2) | Tier 1 fixtures | ~30 |
| 4 | Plot Types (Suite 3) | Tier 1 fixtures | ~35 |
| 5 | Settings Pills (Suite 4) | Tier 2 fixtures | ~40 |
| 6 | Shaper Pipeline (Suite 5) | Tier 1 fixtures | ~25 |
| 7 | Engine Comparison (Suite 6) | Tier 2 fixtures | ~20 |
| 8 | Export Presets (Suite 7) | Tier 2 fixtures | ~20 |
| 9 | Portfolio (Suite 8) | Tier 3 fixtures | ~20 |
| **Total** | | | **~215 tests** |

---

## 6. CI Configuration

```yaml
# .github/workflows/e2e.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev,test]"
      - run: playwright install chromium
      - run: streamlit run app.py &
      - run: sleep 10  # Wait for Streamlit to start
      - run: pytest tests/e2e/ --headed=false -v
```

---

## 7. Visual Regression Strategy

- **Baseline screenshots**: Stored in `tests/e2e/baselines/`
- **Comparison**: Playwright's `expect(page).to_have_screenshot()` with threshold
- **Update flow**: `pytest --update-snapshots` to regenerate baselines
- **Per-engine baselines**: Separate baselines for Plotly and Matplotlib renders

---

## 8. Implementation Log

### Design Decisions (vs. original plan)

1. **Dropped BDD/Gherkin**: `pytest-bdd` is not in project dependencies, existing tests don't use Gherkin. Kept plain pytest + Playwright matching existing codebase patterns.
2. **Dropped Serenity Screenplay**: Overly complex for a Streamlit app; kept Page Object Model pattern (already implemented in `tests/visual/pages/`).
3. **Reused existing POMs**: All tests import from `tests/visual/pages/` (BasePage, DataSourcePage, DataManagersPage, ManagePlotsPage, PortfolioPage) instead of duplicating.
4. **Flat file structure**: One test file per suite instead of nested directories — matches existing codebase convention (`tests/visual/test_*.py`).
5. **Tiers 0-3 only**: Dropped Tier 4 (preset) — preset application is tested within `test_settings.py` and `test_export_presets.py` directly.
6. **CSV upload for base state**: 18-row fixture CSV (3 benchmarks × 3 configs × 2 seeds) instead of real gem5 parsing (~3 min). Fast setup.

### Files Written

| File | Lines | Tests | Content |
|------|-------|-------|---------|
| `tests/e2e/__init__.py` | 1 | — | Package init |
| `tests/e2e/fixtures/__init__.py` | 1 | — | Package init |
| `tests/e2e/fixtures/sample_data.csv` | 19 | — | 18-row fixture (8 columns) |
| `tests/e2e/conftest.py` | 339 | — | Server lifecycle, browser config, tier fixtures (0-3), artifact capture |
| `tests/e2e/test_data_source.py` | 249 | 25 | 3 classes: PageStructure (10), VariableDialog (10), CsvUpload (5) |
| `tests/e2e/test_data_managers.py` | 268 | 25 | 6 classes: Structure (7), OutlierRemover (4), SeedsReducer (4), Mixer (4), Preprocessor (4), History (2) |
| `tests/e2e/test_plot_types.py` | 191 | 10 | 2 classes: PlotCreation (6), PlotControls (4) |
| `tests/e2e/test_settings.py` | 151 | 18 | 2 classes: SettingsPills (15), PresetApplication (3) |
| `tests/e2e/test_shaper_pipeline.py` | 259 | 20 | 3 classes: PipelineOperations (7), ShaperTypes (8), PipelineSaveLoad (5) |
| `tests/e2e/test_engine_comparison.py` | 165 | 6 | 1 class: EngineSwitching (6) |
| `tests/e2e/test_export_presets.py` | 202 | 7 | 1 class: ExportDownload (7) |
| `tests/e2e/test_portfolio.py` | 204 | 10 | 2 classes: PortfolioSaveLoad (6), CrossPageState (4) |
| **Total** | **2,028** | **121** | **11 files + 2 inits + 1 CSV** |

### Tier Fixture Summary

| Tier | Fixture | Scope | State |
|------|---------|-------|-------|
| 0 | `tier0_page` | class | Fresh app, navigated to home |
| 1 | `tier1_page` | class | Tier 0 + CSV data loaded (18 rows) |
| 2 | `tier2_page` | class | Tier 1 + bar plot "E2E Bar" with Sort pipeline |
| 3 | `tier3_page` | class | Tier 2 + second plot "E2E Shaped" with Column Selector + Sort |

### Test Distribution by xdist Group

Each class gets its own `@pytest.mark.xdist_group()` to ensure serial execution within the group while allowing parallel execution across groups:

- `e2e_data_source` (3 classes, 25 tests)
- `e2e_data_managers_structure`, `e2e_data_managers_outlier`, `e2e_data_managers_seeds`, `e2e_data_managers_mixer`, `e2e_data_managers_preproc`, `e2e_data_managers_history` (6 classes, 25 tests)
- `e2e_plot_types`, `e2e_plot_controls` (2 classes, 10 tests)
- `e2e_settings`, `e2e_settings_presets` (2 classes, 18 tests)
- `e2e_shaper_pipeline`, `e2e_shaper_types`, `e2e_pipeline_save_load` (3 classes, 20 tests)
- `e2e_engine` (1 class, 6 tests)
- `e2e_export` (1 class, 7 tests)
- `e2e_portfolio`, `e2e_cross_page` (2 classes, 10 tests)

### Status: COMPLETE
