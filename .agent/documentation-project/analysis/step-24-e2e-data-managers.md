# Step 24 -- E2E Data Managers Page Tests

> **Objective**: Define an exhaustive end-to-end test plan for the Data Managers page,
> covering every tab (Summary, Data Visualization, Seeds Reducer, Outlier Remover,
> Preprocessor, Mixer, Operations History), every service-layer transformation, the
> two-step preview-then-confirm workflow, operation history recording, and all
> validation/error paths.

---

## 1. Executive Summary

The **Data Managers** page (`src/web/pages/data_managers.py`) is the primary data
transformation hub of the RING-5 Unified Engine v2. It exposes **seven tabs** within a
single Streamlit page, each implemented as an `@st.fragment` for independent rerun
isolation:

| Tab | Component | Core Service | Preview Key |
|-----|-----------|-------------|-------------|
| Summary | `DataManagerComponents.render_summary_tab` | -- | -- |
| Data Visualization | `DataManagerComponents.render_visualization_tab` | -- | -- |
| Seeds Reducer | `SeedsReducerManager` | `ReductionService.reduce_seeds` | `seeds_reduction` |
| Outlier Remover | `OutlierRemoverManager` | `OutlierService.remove_outliers` | `outlier_removal` |
| Preprocessor | `PreprocessorManager` | `ArithmeticService.apply_operation` | `preprocessor` |
| Mixer | `MixerManager` | `ArithmeticService.apply_mixer` | `mixer` |
| Operations History | `HistoryComponents.render_portfolio_history` | -- | -- |

**Architectural invariant**: Every data transformation follows a strict **Preview then
Confirm** two-step protocol:

```
User configures inputs
  -> clicks "Preview" / "Apply" button
  -> service computes result, stored in PreviewRepository
  -> UI displays result preview (dataframe, metrics)
  -> "Confirm" button appears (type="primary")
  -> user clicks Confirm
  -> StateManager.set_data() updates the active DataFrame
  -> OperationRecord written to history
  -> preview cleared, page reruns
```

The E2E tests validate this entire flow from widget interaction through to data mutation
and history recording. The test suite uses **pytest-playwright** with the Streamlit
Testing Framework (`st.testing.v1`) or direct browser automation against a running
Streamlit server.

### Key File References

| File | Role |
|------|------|
| `src/web/pages/data_managers.py` | Page orchestrator -- tab layout, fragment wiring |
| `src/web/components/data_managers/data_manager.py` | ABC with `get_data()` / `set_data()` helpers |
| `src/web/components/data_managers/preprocessor.py` | Arithmetic column creation UI |
| `src/web/components/data_managers/seeds_reducer.py` | Multi-seed aggregation UI |
| `src/web/components/data_managers/outlier_remover.py` | IQR-based outlier removal UI |
| `src/web/components/data_managers/mixer.py` | Multi-column merge/concatenate UI |
| `src/web/components/data_managers/data_manager_components.py` | Summary + Visualization tabs |
| `src/web/components/common/history_components.py` | History table rendering with Load/Delete |
| `src/core/services/managers/arithmetic_service.py` | Division, Sum, Subtraction, Multiplication, Mixer |
| `src/core/services/managers/outlier_service.py` | IQR outlier removal (global + grouped) |
| `src/core/services/managers/reduction_service.py` | Seeds groupby mean+std aggregation |
| `src/core/services/managers/managers_impl.py` | `DefaultManagersAPI` facade delegating to services |
| `src/core/services/managers/managers_api.py` | `ManagersAPI` protocol contract |
| `src/core/models/history_models.py` | `OperationRecord` TypedDict |
| `src/web/state/ui_state_manager.py` | `WidgetKeyBuilder`, `UIStateManager`, `_ManagerUIState` |

### Supported Operations Summary

| Manager | Operations | Validation Service | History Operation String |
|---------|-----------|-------------------|--------------------------|
| Preprocessor | Division, Sum, Subtraction, Multiplication | None (inline in `ArithmeticService`) | `"Preprocessor: {op}"` |
| Seeds Reducer | mean + stdev groupby | `ReductionService.validate_seeds_reducer_inputs` | `"Seeds Reduction (mean + stdev)"` |
| Outlier Remover | IQR-based Q1/Q3 filtering | `OutlierService.validate_outlier_inputs` | `"Outlier Removal (Q3)"` |
| Mixer | Sum, Mean (Average), Concatenate | `ArithmeticService.validate_merge_inputs` | `"Mixer: {op}"` |

---

## 2. Page Under Test: Data Managers Overview

### 2.1 Tab Structure and Rendering Flow

```
show_data_managers_page(api)
  |
  +-- st.tabs(["Summary", "Data Visualization", "Seeds Reducer",
  |             "Outlier Remover", "Preprocessor", "Mixer",
  |             "Operations History"])
  |
  +-- Guard: api.state_manager.has_data() == False
  |     -> st.warning("No data loaded...")
  |     -> return (only Summary tab rendered with warning)
  |
  +-- Guard: api.state_manager.get_data() is None
  |     -> st.error("Failed to retrieve data.")
  |     -> return
  |
  +-- tab1: DataManagerComponents.render_summary_tab(data)
  |     -> 4 metrics: Rows, Columns, Memory, Missing Values
  |     -> Quick Preview (first 20 rows)
  |     -> Column Details (from DataComponents)
  |     -> Numeric + Categorical summaries
  |
  +-- tab2: DataManagerComponents.render_visualization_tab(data)
  |     -> Search & Filter (column selector + search term)
  |     -> Display Options (column multiselect + rows per page)
  |     -> Paginated data table
  |     -> Download CSV button
  |
  +-- tab3: SeedsReducerManager(api).render()       [@st.fragment]
  +-- tab4: OutlierRemoverManager(api).render()      [@st.fragment]
  +-- tab5: PreprocessorManager(api).render()        [@st.fragment]
  +-- tab6: MixerManager(api).render()               [@st.fragment]
  +-- tab7: HistoryComponents.render_portfolio_history(api.get_portfolio_history())
```

### 2.2 Widget Key Namespace Convention

All manager widgets use `WidgetKeyBuilder.manager_key(manager_name, suffix)` which
produces keys following the pattern `manager.{name}.{suffix}`:

| Manager | Key Examples |
|---------|-------------|
| Preprocessor | `manager.preprocessor.src1`, `manager.preprocessor.op`, `manager.preprocessor.src2`, `manager.preprocessor.name`, `manager.preprocessor.preview`, `manager.preprocessor.confirm` |
| Seeds Reducer | `manager.seeds_reducer.target_column`, `manager.seeds_reducer.categorical`, `manager.seeds_reducer.numeric`, `manager.seeds_reducer.apply`, `manager.seeds_reducer.confirm` |
| Outlier Remover | `manager.outlier_remover.col`, `manager.outlier_remover.groupby`, `manager.outlier_remover.apply`, `manager.outlier_remover.confirm` |
| Mixer | `manager.mixer.mode`, `manager.mixer.select_cols`, `manager.mixer.op`, `manager.mixer.sep`, `manager.mixer.new_name`, `manager.mixer.preview`, `manager.mixer.confirm` |

### 2.3 Preview Repository Protocol

Each manager stores computed results via the ApplicationAPI preview methods:

```python
api.set_preview(key, df)    # stores DataFrame in PreviewRepository
api.has_preview(key)         # returns bool -- controls Confirm button visibility
api.get_preview(key)         # retrieves stored DataFrame (or None)
api.clear_preview(key)       # removes preview after confirmation
```

Preview keys per manager: `"preprocessor"`, `"seeds_reduction"`, `"outlier_removal"`,
`"mixer"`.

### 2.4 History Recording Protocol

After confirmation, each manager writes an `OperationRecord` TypedDict:

```python
class OperationRecord(TypedDict):
    source_columns: list[str]   # Input columns used
    dest_columns: list[str]     # Output columns produced
    operation: str              # Human-readable operation name
    timestamp: str              # ISO-8601 UTC timestamp
```

Records are appended via `api.add_manager_history_record(record)` and displayed
both in per-manager history expanders and the global Operations History tab.

---

## 3. Test Fixtures (Tier 1 Data Required)

### 3.1 Base Simulation DataFrame

All Data Managers tests require a loaded DataFrame before the page can render any
transformation UI. The fixture must include categorical columns (for grouping),
numeric columns (for arithmetic and statistics), and a seed-like column (for reduction).

```python
# tests/e2e/conftest.py

import pandas as pd
import numpy as np
import pytest
from playwright.sync_api import Page


@pytest.fixture
def simulation_dataframe() -> pd.DataFrame:
    """Tier-1 fixture: A realistic simulation DataFrame with multiple seeds,
    categorical grouping columns, and numeric metric columns.

    Structure:
        - config_name (str): Simulation configuration identifier
        - benchmark (str): Benchmark program name
        - random_seed (int): Simulation seed (3 seeds per config)
        - cpu_cycles (float): Total CPU cycles measured
        - instructions (float): Total instructions executed
        - cache_misses (float): L1 cache misses
        - memory_bandwidth (float): Memory bandwidth in GB/s
        - execution_time (float): Wall-clock time in seconds

    Properties:
        - 2 configs x 3 benchmarks x 3 seeds = 18 rows
        - All numeric columns are positive floats
        - random_seed has exactly 3 unique values (good candidate for reduction)
        - config_name and benchmark are categorical (object dtype)
    """
    np.random.seed(42)
    configs = ["baseline", "optimized"]
    benchmarks = ["matmul", "fft", "sort"]
    seeds = [100, 200, 300]

    rows = []
    for config in configs:
        for bench in benchmarks:
            for seed in seeds:
                rows.append({
                    "config_name": config,
                    "benchmark": bench,
                    "random_seed": seed,
                    "cpu_cycles": np.random.uniform(1e6, 5e6),
                    "instructions": np.random.uniform(5e5, 2e6),
                    "cache_misses": np.random.uniform(1e3, 1e5),
                    "memory_bandwidth": np.random.uniform(10.0, 50.0),
                    "execution_time": np.random.uniform(0.5, 5.0),
                })
    return pd.DataFrame(rows)


@pytest.fixture
def dataframe_with_outliers(simulation_dataframe: pd.DataFrame) -> pd.DataFrame:
    """Tier-1 fixture: Simulation data with injected extreme outliers.

    Adds 3 rows with execution_time values 100x the normal range to
    verify outlier removal behavior. The extreme values ensure they lie
    well beyond the IQR * 1.5 fence.
    """
    df = simulation_dataframe.copy()
    outlier_rows = pd.DataFrame([
        {"config_name": "baseline", "benchmark": "matmul", "random_seed": 100,
         "cpu_cycles": 9e9, "instructions": 9e9, "cache_misses": 9e9,
         "memory_bandwidth": 999.0, "execution_time": 500.0},
        {"config_name": "optimized", "benchmark": "fft", "random_seed": 200,
         "cpu_cycles": 8e9, "instructions": 8e9, "cache_misses": 8e9,
         "memory_bandwidth": 888.0, "execution_time": 450.0},
        {"config_name": "baseline", "benchmark": "sort", "random_seed": 300,
         "cpu_cycles": 7e9, "instructions": 7e9, "cache_misses": 7e9,
         "memory_bandwidth": 777.0, "execution_time": 400.0},
    ])
    return pd.concat([df, outlier_rows], ignore_index=True)


@pytest.fixture
def dataframe_with_sd_columns(simulation_dataframe: pd.DataFrame) -> pd.DataFrame:
    """Tier-1 fixture: Pre-reduced data with .sd columns for Mixer SD propagation tests.

    Simulates output from Seeds Reducer -- mean values with corresponding
    .sd (standard deviation) columns. Required for testing Mixer's automatic
    error propagation feature (sqrt(sd1^2 + sd2^2 + ...)).
    """
    np.random.seed(42)
    df = simulation_dataframe.copy()
    df["cpu_cycles.sd"] = np.random.uniform(1e4, 5e4, len(df))
    df["instructions.sd"] = np.random.uniform(1e3, 1e4, len(df))
    df["execution_time.sd"] = np.random.uniform(0.01, 0.5, len(df))
    return df


@pytest.fixture
def dataframe_no_numeric() -> pd.DataFrame:
    """Tier-1 fixture: DataFrame with only categorical columns.

    Used to test edge cases where numeric operations are unavailable.
    """
    return pd.DataFrame({
        "config_name": ["a", "b", "c"],
        "benchmark": ["x", "y", "z"],
        "description": ["desc1", "desc2", "desc3"],
    })


@pytest.fixture
def data_managers_page(page: Page, simulation_dataframe: pd.DataFrame) -> Page:
    """Navigate to the Data Managers page with pre-loaded simulation data.

    Loads the simulation_dataframe into the application state via the
    data source page or direct API injection, then navigates to the
    Data Managers page. Returns the Playwright Page object ready for
    tab interaction.
    """
    # Load data via the data source mechanism (implementation-specific)
    # Option A: Direct session state injection if running embedded
    # Option B: Upload CSV via Data Source page
    page.goto("http://localhost:8501/Data_Managers")
    page.wait_for_selector("text=Data Managers & Transformations", timeout=10000)
    return page
```

### 3.2 Streamlit Widget Locator Helpers

```python
# tests/e2e/helpers/streamlit_locators.py

from playwright.sync_api import Page, Locator


def get_tab(page: Page, tab_name: str) -> Locator:
    """Click a Streamlit tab by its label text and return the locator."""
    tab = page.get_by_role("tab", name=tab_name)
    tab.click()
    return tab


def get_selectbox(page: Page, label: str) -> Locator:
    """Locate a Streamlit selectbox by its label."""
    return page.locator(f"[data-testid='stSelectbox']:has-text('{label}')")


def get_multiselect(page: Page, label: str) -> Locator:
    """Locate a Streamlit multiselect by its label."""
    return page.locator(f"[data-testid='stMultiSelect']:has-text('{label}')")


def get_text_input(page: Page, label: str) -> Locator:
    """Locate a Streamlit text input by its label."""
    return page.locator(f"[data-testid='stTextInput']:has-text('{label}')")


def get_button(page: Page, label: str) -> Locator:
    """Locate a Streamlit button by its label text."""
    return page.get_by_role("button", name=label)


def get_metric_value(page: Page, label: str) -> str:
    """Read the value from a Streamlit metric widget by its label."""
    metric = page.locator(f"[data-testid='stMetric']:has-text('{label}')")
    return metric.locator("[data-testid='stMetricValue']").inner_text()


def get_dataframe(page: Page, index: int = 0) -> Locator:
    """Locate a Streamlit dataframe widget by index (0-based)."""
    return page.locator("[data-testid='stDataFrame']").nth(index)


def wait_for_toast(page: Page, text: str, timeout: int = 5000) -> None:
    """Wait for a Streamlit toast notification containing the given text."""
    page.wait_for_selector(
        f"[data-testid='stToast']:has-text('{text}')", timeout=timeout
    )


def get_alert(page: Page, level: str = "error") -> Locator:
    """Locate a Streamlit alert (error, warning, info, success) element."""
    return page.locator(f"[data-testid='stAlert'][data-baseweb='{level}']")


def clear_multiselect(page: Page, label: str) -> None:
    """Clear all selections from a Streamlit multiselect widget."""
    ms = get_multiselect(page, label)
    clear_btn = ms.locator("button[aria-label='Clear all']")
    if clear_btn.is_visible():
        clear_btn.click()
```

---

## 4. Preprocessor Tests (Arithmetic Operations)

The Preprocessor tab (`PreprocessorManager`) creates new columns by applying binary
arithmetic between two existing numeric columns. It supports four operations via
`ArithmeticService.apply_operation`:

| Operation | Formula | Default Name Pattern | Service Alias Match |
|-----------|---------|---------------------|---------------------|
| Division | `s1 / s2.replace(0, nan)` | `{src1}_per_{src2}` | `division`, `divide`, `/` |
| Sum | `s1 + s2` | `{src1}_plus_{src2}` | `sum`, `add`, `+` |
| Subtraction | `s1 - s2` | `{src1}_minus_{src2}` | `subtraction`, `subtract`, `minus`, `-` |
| Multiplication | `s1 * s2` | `{src1}_prod_{src2}` | `multiplication`, `multiply`, `*` |

### 4.1 Gherkin Scenarios

```gherkin
Feature: Preprocessor -- Create new columns via arithmetic operations

  Background:
    Given the application has loaded the simulation_dataframe
    And I navigate to the "Data Managers" page
    And I click the "Preprocessor" tab
    And the Preprocessor tab displays "Preprocessor (Basic)"

  # -------------------------------------------------------------------
  # Division
  # -------------------------------------------------------------------
  Scenario: DM-PRE-001 -- Division creates IPC ratio column
    When I select "instructions" as "Source Column 1"
    And I select "Division" as "Operation"
    And I select "cpu_cycles" as "Source Column 2"
    Then the "New column name" field auto-populates with "instructions_per_cpu_cycles"
    When I click "Preview Result"
    Then I see a success message "Created column `instructions_per_cpu_cycles`!"
    And I see a preview dataframe showing columns [instructions, cpu_cycles, instructions_per_cpu_cycles]
    And I see a statistics summary (describe) for the new column
    When I click "Confirm and Add Column to Dataset"
    Then I see a toast notification containing "Column added to dataset"
    And the active dataset now contains the column "instructions_per_cpu_cycles"
    And an OperationRecord is appended with operation "Preprocessor: Division"
    And the OperationRecord has source_columns ["instructions", "cpu_cycles"]
    And the OperationRecord has dest_columns ["instructions_per_cpu_cycles"]

  Scenario: DM-PRE-002 -- Division by zero produces NaN, not crash
    Given the dataset includes a column "zero_col" where all values are 0
    When I select "cpu_cycles" as "Source Column 1"
    And I select "Division" as "Operation"
    And I select "zero_col" as "Source Column 2"
    And I click "Preview Result"
    Then the new column contains NaN values (from s2.replace(0, np.nan))
    And no st.exception is displayed on the page
    And the statistics summary shows count=0 or all-NaN statistics

  # -------------------------------------------------------------------
  # Sum
  # -------------------------------------------------------------------
  Scenario: DM-PRE-003 -- Sum adds two numeric columns
    When I select "cpu_cycles" as "Source Column 1"
    And I select "Sum" as "Operation"
    And I select "instructions" as "Source Column 2"
    Then the "New column name" field auto-populates with "cpu_cycles_plus_instructions"
    When I click "Preview Result"
    Then each row in the preview satisfies: new_col = cpu_cycles + instructions
    When I click "Confirm and Add Column to Dataset"
    Then the column "cpu_cycles_plus_instructions" is in the active dataset

  # -------------------------------------------------------------------
  # Subtraction
  # -------------------------------------------------------------------
  Scenario: DM-PRE-004 -- Subtraction creates difference column
    When I select "cpu_cycles" as "Source Column 1"
    And I select "Subtraction" as "Operation"
    And I select "instructions" as "Source Column 2"
    Then the "New column name" field auto-populates with "cpu_cycles_minus_instructions"
    When I click "Preview Result"
    Then each row in the preview satisfies: new_col = cpu_cycles - instructions

  # -------------------------------------------------------------------
  # Multiplication
  # -------------------------------------------------------------------
  Scenario: DM-PRE-005 -- Multiplication creates product column
    When I select "memory_bandwidth" as "Source Column 1"
    And I select "Multiplication" as "Operation"
    And I select "execution_time" as "Source Column 2"
    Then the "New column name" field auto-populates with "memory_bandwidth_prod_execution_time"
    When I click "Preview Result"
    Then each row satisfies: new_col = memory_bandwidth * execution_time

  # -------------------------------------------------------------------
  # Custom Column Name
  # -------------------------------------------------------------------
  Scenario: DM-PRE-006 -- User overrides auto-generated column name
    When I select "instructions" as "Source Column 1"
    And I select "Division" as "Operation"
    And I select "cpu_cycles" as "Source Column 2"
    And I clear and type "IPC" into the "New column name" field
    And I click "Preview Result"
    Then the preview dataframe contains a column named "IPC"
    When I click "Confirm and Add Column to Dataset"
    Then the active dataset contains column "IPC"
    And the OperationRecord has dest_columns ["IPC"]

  # -------------------------------------------------------------------
  # Preview without Confirm
  # -------------------------------------------------------------------
  Scenario: DM-PRE-007 -- Preview does not mutate the active dataset
    When I configure a valid Division operation
    And I click "Preview Result"
    Then the "Confirm and Add Column to Dataset" button is visible
    When I navigate to the "Summary" tab
    Then the column count metric still shows the original count (no new column)
    When I navigate back to the "Preprocessor" tab
    Then the Confirm button may still be visible (if preview persists in repository)

  Scenario: DM-PRE-008 -- Only numeric columns appear in selectboxes
    Given the dataset has categorical columns "config_name" and "benchmark"
    Then "config_name" does NOT appear in the "Source Column 1" selectbox
    And "benchmark" does NOT appear in the "Source Column 2" selectbox
    And only columns with numeric dtype are shown as options

  # -------------------------------------------------------------------
  # History Load
  # -------------------------------------------------------------------
  Scenario: DM-PRE-009 -- Load operation from history pre-fills widgets
    Given I have previously confirmed a "Preprocessor: Division" operation
      with source_columns=["instructions","cpu_cycles"] dest_columns=["IPC"]
    When I expand the "History" expander in the Preprocessor tab
    Then the history shows one entry with Operation="Division"
    When I click the Load (reload) button for that record
    Then the "Source Column 1" selectbox is set to "instructions"
    And the "Operation" selectbox is set to "Division"
    And the "Source Column 2" selectbox is set to "cpu_cycles"
    And the "New column name" field is pre-filled with "IPC"

  Scenario: DM-PRE-010 -- History load with missing columns shows warning
    Given I previously confirmed an operation using column "old_metric"
    And "old_metric" no longer exists in the current dataset
    When I load that record from history
    Then I see a warning "Columns removed (not in current data): old_metric"

  # -------------------------------------------------------------------
  # No Numeric Columns Edge Case
  # -------------------------------------------------------------------
  Scenario: DM-PRE-011 -- No numeric columns shows warning
    Given the dataset has only categorical columns (no numeric)
    When I navigate to the Preprocessor tab
    Then I see a warning "No numeric columns found for preprocessing"
    And no operation widgets are displayed
```

### 4.2 Pytest-Playwright Test Stubs

```python
# tests/e2e/test_data_managers_preprocessor.py

import pytest
from playwright.sync_api import Page, expect


class TestPreprocessorDivision:
    """DM-PRE-001, DM-PRE-002: Division arithmetic operations."""

    def test_division_creates_ratio_column(self, data_managers_page: Page) -> None:
        """DM-PRE-001: End-to-end division with preview, confirm, and history."""
        page = data_managers_page

        # Navigate to Preprocessor tab
        page.get_by_role("tab", name="Preprocessor").click()
        page.wait_for_selector("text=Preprocessor (Basic)")

        # Select source columns and operation
        src1_box = page.locator(
            "[data-testid='stSelectbox']:has-text('Source Column 1')"
        )
        src1_box.locator("select").select_option("instructions")

        op_box = page.locator(
            "[data-testid='stSelectbox']:has-text('Operation')"
        )
        op_box.locator("select").select_option("Division")

        src2_box = page.locator(
            "[data-testid='stSelectbox']:has-text('Source Column 2')"
        )
        src2_box.locator("select").select_option("cpu_cycles")

        # Verify auto-generated name follows "{src1}_per_{src2}" pattern
        name_input = page.locator(
            "[data-testid='stTextInput']:has-text('New column name') input"
        )
        expect(name_input).to_have_value("instructions_per_cpu_cycles")

        # Click Preview
        page.get_by_role("button", name="Preview Result").click()
        page.wait_for_selector("text=Created column")

        # Verify preview dataframe is visible with correct columns
        dataframe = page.locator("[data-testid='stDataFrame']").first
        expect(dataframe).to_be_visible()

        # Verify statistics section is present
        expect(page.locator("text=Statistics")).to_be_visible()

        # Confirm to commit to dataset
        page.get_by_role("button", name="Confirm and Add Column to Dataset").click()
        page.wait_for_selector("[data-testid='stToast']", timeout=5000)

    def test_division_by_zero_produces_nan(self, data_managers_page: Page) -> None:
        """DM-PRE-002: Division by a zero-valued column yields NaN, not exception."""
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        # Requires a zero column injected into the fixture
        # ArithmeticService does: s1 / s2.replace(0, np.nan)
        # So result is NaN where s2 == 0
        page.get_by_role("button", name="Preview Result").click()

        # Must NOT see an exception banner
        expect(page.locator("[data-testid='stException']")).to_have_count(0)


class TestPreprocessorSum:
    """DM-PRE-003: Sum arithmetic operation."""

    def test_sum_adds_two_columns(self, data_managers_page: Page) -> None:
        """DM-PRE-003: Sum creates column with correct additive values."""
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        # Configure: src1="cpu_cycles", op="Sum", src2="instructions"
        # ... (selectbox interactions)

        name_input = page.locator(
            "[data-testid='stTextInput']:has-text('New column name') input"
        )
        expect(name_input).to_have_value("cpu_cycles_plus_instructions")

        page.get_by_role("button", name="Preview Result").click()
        page.wait_for_selector("text=Created column")

        page.get_by_role("button", name="Confirm and Add Column to Dataset").click()
        page.wait_for_selector("[data-testid='stToast']", timeout=5000)


class TestPreprocessorSubtraction:
    """DM-PRE-004: Subtraction arithmetic operation."""

    def test_subtraction_creates_difference(self, data_managers_page: Page) -> None:
        """DM-PRE-004: Subtraction produces col1 - col2 in new column."""
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        # Configure: src1="cpu_cycles", op="Subtraction", src2="instructions"
        # Verify auto-name: "cpu_cycles_minus_instructions"
        # Preview and confirm flow
        pass  # Stub -- widget interaction identical to Division pattern


class TestPreprocessorMultiplication:
    """DM-PRE-005: Multiplication arithmetic operation."""

    def test_multiplication_creates_product(self, data_managers_page: Page) -> None:
        """DM-PRE-005: Multiplication produces col1 * col2 in new column."""
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        # Configure: src1="memory_bandwidth", op="Multiplication", src2="execution_time"
        # Verify auto-name: "memory_bandwidth_prod_execution_time"
        pass  # Stub


class TestPreprocessorCustomName:
    """DM-PRE-006: User-defined column name override."""

    def test_custom_column_name_override(self, data_managers_page: Page) -> None:
        """DM-PRE-006: User clears auto-name and types custom name 'IPC'."""
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        # Configure division first, then override name
        name_input = page.locator(
            "[data-testid='stTextInput']:has-text('New column name') input"
        )
        name_input.fill("")
        name_input.type("IPC")

        page.get_by_role("button", name="Preview Result").click()
        page.wait_for_selector("text=Created column `IPC`")


class TestPreprocessorPreviewIsolation:
    """DM-PRE-007: Preview does not mutate active dataset."""

    def test_preview_does_not_mutate_dataset(self, data_managers_page: Page) -> None:
        """DM-PRE-007: After preview but before confirm, dataset unchanged."""
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        # Configure and preview
        page.get_by_role("button", name="Preview Result").click()
        page.wait_for_selector("text=Created column")

        # Navigate to Summary tab to check column count
        page.get_by_role("tab", name="Summary").click()
        columns_metric = page.locator(
            "[data-testid='stMetric']:has-text('Columns')"
        )
        # Original dataset has 8 columns -- no new column yet
        expect(columns_metric).to_contain_text("8")


class TestPreprocessorNumericOnly:
    """DM-PRE-008: Only numeric columns appear in source selectboxes."""

    def test_only_numeric_columns_shown(self, data_managers_page: Page) -> None:
        """DM-PRE-008: Categorical columns excluded from source selectors."""
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        src1_box = page.locator(
            "[data-testid='stSelectbox']:has-text('Source Column 1')"
        )
        # "config_name" is categorical -- should NOT be an option
        expect(src1_box).not_to_contain_text("config_name")
        expect(src1_box).not_to_contain_text("benchmark")


class TestPreprocessorHistoryLoad:
    """DM-PRE-009, DM-PRE-010: History load pre-fills manager widgets."""

    def test_history_load_prefills_widgets(self, data_managers_page: Page) -> None:
        """DM-PRE-009: Clicking Load on a history record restores widget state."""
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        # Step 1: Perform a complete Division operation to create history
        # ... (configure, preview, confirm -- omitted for brevity)

        # Step 2: Expand history and click the Load button
        page.locator("details:has-text('History')").click()
        load_buttons = page.locator("button:has-text('reload')")
        load_buttons.first.click()

        # Step 3: Verify widget values match the loaded record
        # The consume_load_trigger mechanism restores session_state keys
        pass  # Stub -- assert selectbox values

    def test_history_load_warns_on_missing_columns(
        self, data_managers_page: Page
    ) -> None:
        """DM-PRE-010: Loading a record with missing columns shows warning."""
        # Requires a record referencing a column that was removed
        # (e.g., after a Seeds Reducer operation changed the column set)
        pass  # Stub


class TestPreprocessorNoNumericCols:
    """DM-PRE-011: No numeric columns edge case."""

    def test_no_numeric_columns_warning(self, data_managers_page: Page) -> None:
        """DM-PRE-011: Dataset with only categoricals shows warning."""
        # Requires dataframe_no_numeric fixture
        page = data_managers_page
        page.get_by_role("tab", name="Preprocessor").click()

        expect(
            page.locator("text=No numeric columns found for preprocessing")
        ).to_be_visible()
```

---

## 5. Seeds Reducer Tests

The Seeds Reducer tab (`SeedsReducerManager`) groups data by categorical columns
and computes mean + standard deviation for selected numeric columns via
`ReductionService.reduce_seeds`. The `.sd` suffix columns are critical for
downstream error bar rendering and Mixer SD propagation.

### 5.1 Service Layer Behavior

```python
# ReductionService.reduce_seeds:
grouped = df.groupby(categorical_cols)[statistic_cols]
mean_df = grouped.mean().reset_index()
std_df = grouped.std().reset_index()
std_df = std_df.rename(columns=lambda x: f"{x}.sd" if x in statistic_cols else x)
result_df = pd.merge(mean_df, std_df, on=categorical_cols)
```

Key behaviors to validate:
1. Output row count = number of unique groups (not number of input rows)
2. Each numeric column `X` produces both `X` (mean) and `X.sd` (std)
3. Column ordering: categoricals first, then interleaved mean/sd columns

### 5.2 Candidate Column Filtering

The UI filters candidate columns for reduction:
```python
candidate_cols = [c for c in all_columns if data[c].nunique() <= 50 or data[c].dtype == "object"]
```
And auto-selects `random_seed` as default when present.

### 5.3 Gherkin Scenarios

```gherkin
Feature: Seeds Reducer -- Aggregate data across random seeds

  Background:
    Given the application has loaded the simulation_dataframe
    And the dataset contains column "random_seed" with values [100, 200, 300]
    And the dataset has 18 rows (2 configs x 3 benchmarks x 3 seeds)
    And I navigate to the "Data Managers" page
    And I click the "Seeds Reducer" tab

  # -------------------------------------------------------------------
  # Basic Reduction
  # -------------------------------------------------------------------
  Scenario: DM-SR-001 -- Default reduction over random_seed
    Then the "Column to reduce over" selectbox defaults to "random_seed"
    And the "Group by columns" multiselect defaults to ["config_name", "benchmark"]
    And the "Calculate stats for" multiselect defaults to all numeric columns
    When I click "Apply Seeds Reducer"
    Then I see a success message "Reduced from 18 to 6 rows!"
    And I see metrics: Original Rows = 18, Reduced Rows = 6
    And I see a "Result Preview" dataframe with up to 20 rows
    When I click "Confirm and Apply Seeds Reducer"
    Then I see a toast "Seeds-reduced data is now active!"
    And the active dataset has 6 rows
    And the dataset contains columns: config_name, benchmark,
        cpu_cycles, cpu_cycles.sd, instructions, instructions.sd,
        cache_misses, cache_misses.sd, memory_bandwidth, memory_bandwidth.sd,
        execution_time, execution_time.sd
    And an OperationRecord "Seeds Reduction (mean + stdev)" is appended

  Scenario: DM-SR-002 -- Reduction produces correct mean and std values
    When I apply Seeds Reducer with default settings and confirm
    Then for the group (config_name="baseline", benchmark="matmul"),
         the cpu_cycles value equals mean([seed100_val, seed200_val, seed300_val])
    And the cpu_cycles.sd value equals std([seed100_val, seed200_val, seed300_val])

  Scenario: DM-SR-003 -- Partial numeric column selection
    When I deselect "cache_misses" and "memory_bandwidth" from "Calculate stats for"
    And I click "Apply Seeds Reducer"
    Then the result does NOT contain columns: cache_misses, memory_bandwidth,
         cache_misses.sd, memory_bandwidth.sd
    But it contains: cpu_cycles, cpu_cycles.sd, instructions, instructions.sd,
         execution_time, execution_time.sd
    And I see "Reduced from 18 to 6 rows!"

  Scenario: DM-SR-004 -- Partial categorical column selection changes group count
    When I deselect "benchmark" from "Group by columns"
    And I click "Apply Seeds Reducer"
    Then the result groups only by "config_name"
    And I see "Reduced from 18 to 2 rows!"
    And the reduced dataset has exactly 2 rows

  Scenario: DM-SR-005 -- Reduce over a different column (not random_seed)
    When I change "Column to reduce over" to "benchmark"
    And I click "Apply Seeds Reducer"
    Then the grouping columns should adjust (benchmark removed from categorical)
    And the result aggregates across benchmark values

  # -------------------------------------------------------------------
  # Validation Errors
  # -------------------------------------------------------------------
  Scenario: DM-SR-006 -- No categorical columns selected triggers error
    When I deselect all options from "Group by columns"
    And I click "Apply Seeds Reducer"
    Then I see an error "At least one categorical column must be selected"
    And no preview is shown

  Scenario: DM-SR-007 -- No statistic columns selected triggers error
    When I deselect all options from "Calculate stats for"
    And I click "Apply Seeds Reducer"
    Then I see an error "At least one statistic column must be selected"

  # -------------------------------------------------------------------
  # Edge Cases
  # -------------------------------------------------------------------
  Scenario: DM-SR-008 -- Candidate columns filtered by uniqueness threshold
    Given column "random_seed" has 3 unique values (<= 50 threshold)
    Then "random_seed" appears in "Column to reduce over" options
    And a hypothetical numeric column with > 50 unique non-object values is excluded

  Scenario: DM-SR-009 -- Auto-select random_seed when present
    Given the dataset contains "random_seed"
    Then the default index for "Column to reduce over" points to "random_seed"

  Scenario: DM-SR-010 -- No categorical columns in data shows warning
    Given the dataset has no object/string-dtype columns
    When I navigate to Seeds Reducer
    Then I see "No categorical columns found for grouping"

  Scenario: DM-SR-011 -- No numeric columns in data shows warning
    Given the dataset has no numeric-dtype columns (excluding reduce target)
    When I navigate to Seeds Reducer
    Then I see "No numeric columns found to calculate statistics"

  # -------------------------------------------------------------------
  # History Load
  # -------------------------------------------------------------------
  Scenario: DM-SR-012 -- Load Seeds Reducer record from history
    Given I have previously applied Seeds Reducer
    When I expand the "History" section in the Seeds Reducer tab
    And I click the Load button for the "Seeds" record
    Then the "Group by columns" multiselect is restored to the loaded categorical cols
    And the "Calculate stats for" multiselect is restored to the loaded numeric cols

  Scenario: DM-SR-013 -- History load with missing columns shows warning
    Given I previously applied Seeds Reducer with all columns
    And the dataset has since been modified (some columns removed)
    When I load that record from history
    Then I see a warning "Columns removed (not in current data): ..."
    And only valid columns are pre-selected
```

### 5.4 Pytest-Playwright Test Stubs

```python
# tests/e2e/test_data_managers_seeds_reducer.py

import pytest
from playwright.sync_api import Page, expect


class TestSeedsReducerBasicFlow:
    """DM-SR-001 through DM-SR-005: Core reduction flows."""

    def test_default_reduction_over_random_seed(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-001: Full reduction flow with default settings."""
        page = data_managers_page
        page.get_by_role("tab", name="Seeds Reducer").click()
        page.wait_for_selector("text=Seeds Reducer")

        # Verify default column is "random_seed"
        reduce_col = page.locator(
            "[data-testid='stSelectbox']:has-text('Column to reduce over')"
        )
        expect(reduce_col).to_contain_text("random_seed")

        # Click Apply
        page.get_by_role("button", name="Apply Seeds Reducer").click()
        page.wait_for_selector("text=Reduced from")

        # Verify metrics
        expect(page.locator("text=Reduced from 18 to 6 rows!")).to_be_visible()

        orig_metric = page.locator(
            "[data-testid='stMetric']:has-text('Original Rows')"
        )
        expect(orig_metric).to_contain_text("18")

        reduced_metric = page.locator(
            "[data-testid='stMetric']:has-text('Reduced Rows')"
        )
        expect(reduced_metric).to_contain_text("6")

        # Confirm
        page.get_by_role("button", name="Confirm and Apply Seeds Reducer").click()
        page.wait_for_selector("[data-testid='stToast']", timeout=5000)

    def test_partial_numeric_column_selection(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-003: Deselecting numeric columns excludes them from output."""
        page = data_managers_page
        page.get_by_role("tab", name="Seeds Reducer").click()

        # Remove "cache_misses" chip from multiselect
        stats_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Calculate stats for')"
        )
        stats_ms.locator("span:has-text('cache_misses')").locator("..").locator(
            "button"
        ).click()

        page.get_by_role("button", name="Apply Seeds Reducer").click()
        page.wait_for_selector("text=Reduced from")

        # Verify preview does not include deselected columns
        preview_df = page.locator("[data-testid='stDataFrame']").first
        expect(preview_df).not_to_contain_text("cache_misses")

    def test_partial_categorical_changes_group_count(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-004: Removing a grouping column widens aggregation."""
        page = data_managers_page
        page.get_by_role("tab", name="Seeds Reducer").click()

        # Remove "benchmark" from Group by columns
        group_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Group by columns')"
        )
        group_ms.locator("span:has-text('benchmark')").locator("..").locator(
            "button"
        ).click()

        page.get_by_role("button", name="Apply Seeds Reducer").click()
        page.wait_for_selector("text=Reduced from")

        # 2 configs only -> 2 rows
        expect(page.locator("text=Reduced from 18 to 2 rows!")).to_be_visible()


class TestSeedsReducerValidation:
    """DM-SR-006, DM-SR-007: Input validation error paths."""

    def test_no_categorical_columns_error(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-006: Empty categorical selection shows validation error."""
        page = data_managers_page
        page.get_by_role("tab", name="Seeds Reducer").click()

        # Clear all categorical columns
        group_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Group by columns')"
        )
        clear_btn = group_ms.locator("button[aria-label='Clear all']")
        if clear_btn.is_visible():
            clear_btn.click()

        page.get_by_role("button", name="Apply Seeds Reducer").click()

        expect(
            page.locator("[data-testid='stAlert']:has-text('categorical column')")
        ).to_be_visible()

    def test_no_statistic_columns_error(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-007: Empty statistic selection shows validation error."""
        page = data_managers_page
        page.get_by_role("tab", name="Seeds Reducer").click()

        stats_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Calculate stats for')"
        )
        clear_btn = stats_ms.locator("button[aria-label='Clear all']")
        if clear_btn.is_visible():
            clear_btn.click()

        page.get_by_role("button", name="Apply Seeds Reducer").click()

        expect(
            page.locator("[data-testid='stAlert']:has-text('statistic column')")
        ).to_be_visible()


class TestSeedsReducerEdgeCases:
    """DM-SR-008 through DM-SR-011: Edge cases and warnings."""

    def test_auto_selects_random_seed_default(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-009: random_seed column is auto-selected as default."""
        page = data_managers_page
        page.get_by_role("tab", name="Seeds Reducer").click()

        reduce_col = page.locator(
            "[data-testid='stSelectbox']:has-text('Column to reduce over')"
        )
        expect(reduce_col).to_contain_text("random_seed")

    def test_no_categorical_columns_warning(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-010: Dataset without categoricals shows warning."""
        # Requires all-numeric fixture
        pass  # Stub

    def test_no_numeric_columns_warning(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-011: Dataset without numerics shows warning."""
        # Requires all-categorical fixture
        pass  # Stub


class TestSeedsReducerHistoryLoad:
    """DM-SR-012, DM-SR-013: History load restores widget state."""

    def test_load_from_history_restores_selections(
        self, data_managers_page: Page
    ) -> None:
        """DM-SR-012: Load button restores multiselect values."""
        page = data_managers_page
        page.get_by_role("tab", name="Seeds Reducer").click()

        # Step 1: Apply seeds reducer with default settings, confirm
        page.get_by_role("button", name="Apply Seeds Reducer").click()
        page.wait_for_selector("text=Reduced from")
        page.get_by_role("button", name="Confirm and Apply Seeds Reducer").click()
        page.wait_for_selector("[data-testid='stToast']", timeout=5000)

        # Step 2: Expand history, click Load
        history_expander = page.locator("details:has-text('History')")
        history_expander.click()
        page.locator("button:has-text('reload')").first.click()

        # Step 3: Verify widgets restored (assertion depends on DOM state)
        pass  # Stub
```

---

## 6. Outlier Remover Tests

The Outlier Remover tab (`OutlierRemoverManager`) filters rows using the IQR
(Interquartile Range) method implemented in `OutlierService.remove_outliers`. It
supports both **global** removal (no grouping) and **grouped** removal (per-group Q1/Q3
thresholds). The IQR multiplier is hardcoded at `1.5` (standard mild-outlier threshold).

### 6.1 Service Layer Behavior

```python
# OutlierService.remove_outliers (default multiplier=1.5):
# Global (no group_by_cols):
q1 = df[outlier_col].quantile(0.25)
q3 = df[outlier_col].quantile(0.75)
iqr = q3 - q1
lower = q1 - 1.5 * iqr
upper = q3 + 1.5 * iqr
return df[(df[outlier_col] >= lower) & (df[outlier_col] <= upper)]

# Grouped (with group_by_cols):
mask = df.groupby(group_by_cols)[outlier_col].transform(_iqr_mask).astype(bool)
return df[mask]
```

### 6.2 UI-Specific Behavior: Intelligent Default Grouping

The Outlier Remover excludes seed-like columns from default grouping to prevent
trivially small groups (1 item per group = no outlier detection):

```python
seed_patterns = ("seed", "iteration", "run_id")
default_cols = [c for c in categorical_cols if not any(p in c.lower() for p in seed_patterns)]
```

### 6.3 Gherkin Scenarios

```gherkin
Feature: Outlier Remover -- IQR-based outlier filtering

  Background:
    Given the application has loaded the dataframe_with_outliers fixture
    And the dataset has 21 rows (18 normal + 3 extreme outliers)
    And I navigate to the "Data Managers" page
    And I click the "Outlier Remover" tab

  # -------------------------------------------------------------------
  # Grouped Outlier Removal
  # -------------------------------------------------------------------
  Scenario: DM-OR-001 -- Grouped outlier removal with default settings
    Then the "Column to check for outliers" selectbox shows numeric columns
    And the "Group by columns" multiselect excludes seed-like columns by default
    And the current distribution metrics (Min, Q3, Max, Mean) are displayed
    When I select "execution_time" as "Column to check for outliers"
    And I keep default group-by columns (excluding seed-like columns)
    And I click "Apply Outlier Remover"
    Then I see a success message "Removed N outlier rows (N%)"
    And I see metrics: Original Rows, Filtered Rows, Removed
    And I see a "Filtered Data Preview" dataframe
    And the 3 extreme outlier rows (execution_time >= 400) are removed
    When I click "Confirm and Apply Outlier Remover"
    Then I see a toast "Outlier-filtered data is now active!"
    And the active dataset has fewer rows than the original
    And an OperationRecord "Outlier Removal (Q3)" is appended

  Scenario: DM-OR-002 -- Distribution metrics update for selected column
    When I select "execution_time" as "Column to check for outliers"
    Then I see Min, Q3, Max, Mean metrics for execution_time
    When I change the column to "cpu_cycles"
    Then the Min, Q3, Max, Mean metrics update to reflect cpu_cycles distribution

  # -------------------------------------------------------------------
  # Global Outlier Removal (No Grouping)
  # -------------------------------------------------------------------
  Scenario: DM-OR-003 -- Global outlier removal without group-by columns
    When I select "execution_time" as "Column to check for outliers"
    And I remove all columns from "Group by columns" multiselect
    And I click "Apply Outlier Remover"
    Then the IQR is calculated globally on the entire execution_time column
    And rows outside [Q1 - 1.5*IQR, Q3 + 1.5*IQR] are removed
    And I see the removed count in the success message

  Scenario: DM-OR-004 -- No categorical columns in data uses global Q3
    Given the dataset has NO object/string-dtype columns
    When I navigate to the Outlier Remover tab
    Then I see "No categorical columns for grouping. Will use global Q3."
    And the "Group by columns" multiselect is NOT displayed
    When I click "Apply Outlier Remover"
    Then global IQR filtering is applied without grouping

  # -------------------------------------------------------------------
  # Seed-Exclusion Default Behavior
  # -------------------------------------------------------------------
  Scenario: DM-OR-005 -- Default group-by excludes seed-like columns
    Given the dataset has categorical columns ["config_name", "benchmark"]
    And "random_seed" is a numeric column (not in categorical defaults)
    Then the default "Group by columns" selection does NOT include columns
         matching patterns "seed", "iteration", or "run_id"
    And "config_name" and "benchmark" are included in defaults

  # -------------------------------------------------------------------
  # No Outliers Edge Case
  # -------------------------------------------------------------------
  Scenario: DM-OR-006 -- No outliers found shows zero-removal message
    Given the dataset has no extreme values in "execution_time"
    When I apply Outlier Remover on "execution_time"
    Then I see "Removed 0 outlier rows (0.0%)"
    And Original Rows equals Filtered Rows

  # -------------------------------------------------------------------
  # Validation Errors
  # -------------------------------------------------------------------
  Scenario: DM-OR-007 -- Empty outlier column triggers validation error
    Given the outlier_col selection is somehow empty
    When I click "Apply Outlier Remover"
    Then I see an error "Outlier column must be specified"

  Scenario: DM-OR-008 -- Non-numeric outlier column triggers error
    Given a non-numeric column is forced as outlier_col
    When I click "Apply Outlier Remover"
    Then I see an error containing "must be numeric"

  Scenario: DM-OR-009 -- Missing group-by column triggers error
    Given a group-by column no longer exists in the dataset
    When I click "Apply Outlier Remover"
    Then I see an error "Group by columns not found: ..."

  # -------------------------------------------------------------------
  # History Load
  # -------------------------------------------------------------------
  Scenario: DM-OR-010 -- Load Outlier Remover record from history
    Given I have previously applied Outlier Removal
    When I expand the History section
    And I click the Load button for the "Outlier" record
    Then the outlier column selectbox is set to the loaded column
    And the group-by multiselect is set to the loaded group columns

  Scenario: DM-OR-011 -- History load with missing columns shows warning
    Given a previously-saved outlier record references a deleted column
    When I load that record from history
    Then I see "Columns removed (not in current data): ..."
    And valid columns are still pre-selected
```

### 6.4 Pytest-Playwright Test Stubs

```python
# tests/e2e/test_data_managers_outlier_remover.py

import pytest
from playwright.sync_api import Page, expect


class TestOutlierRemoverGrouped:
    """DM-OR-001, DM-OR-002: Grouped outlier removal flows."""

    def test_grouped_outlier_removal_default(
        self, data_managers_page: Page
    ) -> None:
        """DM-OR-001: Full grouped outlier removal with preview and confirm."""
        page = data_managers_page
        page.get_by_role("tab", name="Outlier Remover").click()
        page.wait_for_selector("text=Outlier Remover")

        # Select execution_time as the outlier column
        col_select = page.locator(
            "[data-testid='stSelectbox']:has-text('Column to check for outliers')"
        )
        col_select.locator("select").select_option("execution_time")

        # Verify distribution metrics are visible
        expect(page.locator("[data-testid='stMetric']:has-text('Min')")).to_be_visible()
        expect(page.locator("[data-testid='stMetric']:has-text('Q3')")).to_be_visible()
        expect(page.locator("[data-testid='stMetric']:has-text('Max')")).to_be_visible()
        expect(page.locator("[data-testid='stMetric']:has-text('Mean')")).to_be_visible()

        # Apply
        page.get_by_role("button", name="Apply Outlier Remover").click()
        page.wait_for_selector("text=Removed")

        # Verify metrics
        expect(
            page.locator("[data-testid='stMetric']:has-text('Original Rows')")
        ).to_be_visible()
        expect(
            page.locator("[data-testid='stMetric']:has-text('Filtered Rows')")
        ).to_be_visible()
        expect(
            page.locator("[data-testid='stMetric']:has-text('Removed')")
        ).to_be_visible()

        # Confirm
        page.get_by_role("button", name="Confirm and Apply Outlier Remover").click()
        page.wait_for_selector("[data-testid='stToast']", timeout=5000)

    def test_distribution_metrics_update_on_column_change(
        self, data_managers_page: Page
    ) -> None:
        """DM-OR-002: Switching outlier column updates Min/Q3/Max/Mean."""
        page = data_managers_page
        page.get_by_role("tab", name="Outlier Remover").click()

        # Select execution_time first
        col_select = page.locator(
            "[data-testid='stSelectbox']:has-text('Column to check for outliers')"
        )
        col_select.locator("select").select_option("execution_time")

        # Read Max metric value
        max_metric_1 = page.locator(
            "[data-testid='stMetric']:has-text('Max')"
        ).locator("[data-testid='stMetricValue']").inner_text()

        # Switch to cpu_cycles
        col_select.locator("select").select_option("cpu_cycles")
        page.wait_for_timeout(1000)  # Wait for rerun

        max_metric_2 = page.locator(
            "[data-testid='stMetric']:has-text('Max')"
        ).locator("[data-testid='stMetricValue']").inner_text()

        # Values should differ (different columns)
        assert max_metric_1 != max_metric_2


class TestOutlierRemoverGlobal:
    """DM-OR-003, DM-OR-004: Global (no grouping) outlier removal."""

    def test_global_outlier_removal_no_grouping(
        self, data_managers_page: Page
    ) -> None:
        """DM-OR-003: IQR on entire column without grouping."""
        page = data_managers_page
        page.get_by_role("tab", name="Outlier Remover").click()

        # Select column
        col_select = page.locator(
            "[data-testid='stSelectbox']:has-text('Column to check for outliers')"
        )
        col_select.locator("select").select_option("execution_time")

        # Clear all group-by columns
        group_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Group by columns')"
        )
        clear_btn = group_ms.locator("button[aria-label='Clear all']")
        if clear_btn.is_visible():
            clear_btn.click()

        page.get_by_role("button", name="Apply Outlier Remover").click()
        page.wait_for_selector("text=Removed")

        # Should show removal count
        expect(page.locator("text=outlier rows")).to_be_visible()


class TestOutlierRemoverSeedExclusion:
    """DM-OR-005: Default grouping excludes seed-like columns."""

    def test_default_groupby_excludes_seed_columns(
        self, data_managers_page: Page
    ) -> None:
        """DM-OR-005: random_seed not in default group-by selection."""
        page = data_managers_page
        page.get_by_role("tab", name="Outlier Remover").click()

        group_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Group by columns')"
        )
        # random_seed matches the "seed" pattern, so should be excluded
        # Check that chips do not include "random_seed"
        expect(group_ms).not_to_contain_text("random_seed")
        # But config_name and benchmark should be present
        expect(group_ms).to_contain_text("config_name")
        expect(group_ms).to_contain_text("benchmark")


class TestOutlierRemoverValidation:
    """DM-OR-007 through DM-OR-009: Validation error paths."""

    def test_non_numeric_column_error(self, data_managers_page: Page) -> None:
        """DM-OR-008: Non-numeric outlier column shows validation error."""
        # This scenario requires special fixture setup
        # The UI only shows numeric columns in the selectbox,
        # so this tests the service-layer validation
        pass  # Stub

    def test_missing_groupby_column_error(self, data_managers_page: Page) -> None:
        """DM-OR-009: Reference to missing group-by column shows error."""
        # This scenario occurs when data changes between operations
        pass  # Stub


class TestOutlierRemoverHistoryLoad:
    """DM-OR-010, DM-OR-011: History load restores widget state."""

    def test_load_from_history_restores_config(
        self, data_managers_page: Page
    ) -> None:
        """DM-OR-010: Load restores outlier column and group-by selections."""
        page = data_managers_page
        page.get_by_role("tab", name="Outlier Remover").click()

        # Step 1: Perform an outlier removal, confirm
        page.get_by_role("button", name="Apply Outlier Remover").click()
        page.wait_for_selector("text=Removed")
        page.get_by_role("button", name="Confirm and Apply Outlier Remover").click()
        page.wait_for_selector("[data-testid='stToast']", timeout=5000)

        # Step 2: Expand history, click Load
        page.locator("details:has-text('History')").click()
        page.locator("button:has-text('reload')").first.click()

        # Step 3: Verify widget values restored
        pass  # Stub

    def test_history_load_warns_on_missing_columns(
        self, data_managers_page: Page
    ) -> None:
        """DM-OR-011: Loading record with deleted column shows warning."""
        pass  # Stub
```

---

## 7. Mixer Tests

The Mixer tab (`MixerManager`) merges multiple columns into a single new column.
It operates in two modes controlled by a `st.segmented_control`:

| Mode | Available Operations | Column Source |
|------|---------------------|---------------|
| Numerical Operations | Sum, Mean (Average) | Numeric columns (excluding `.sd`/`_stdev`) |
| Configuration Merge | Concatenate | All columns (including string) |

### 7.1 SD Propagation Logic

For numeric operations (Sum, Mean), the `ArithmeticService.apply_mixer` automatically
propagates standard deviation columns:

```python
# For each source_col, check for "{col}.sd" or "{col}_stdev"
# Sum:  new_sd = sqrt(sd1^2 + sd2^2 + ...)
# Mean: new_sd = sqrt(sd1^2 + sd2^2 + ...) / N
```

### 7.2 Gherkin Scenarios

```gherkin
Feature: Mixer -- Merge multiple columns into one

  Background:
    Given the application has loaded the simulation_dataframe
    And I navigate to the "Data Managers" page
    And I click the "Mixer" tab

  # -------------------------------------------------------------------
  # Numerical Sum
  # -------------------------------------------------------------------
  Scenario: DM-MIX-001 -- Sum two numeric columns
    When I select "Numerical Operations" mode
    And I select columns ["cpu_cycles", "instructions"] in "Select columns to merge"
    And I select "Sum" as the operation
    Then the "New Column Name" auto-populates with "sum_cpu_cycles_instructions"
    When I click "Preview Merge"
    Then I see "Created merged column `sum_cpu_cycles_instructions`"
    And the preview shows the merged column values
    When I click "Confirm and Merge"
    Then the active dataset contains "sum_cpu_cycles_instructions"
    And an OperationRecord "Mixer: Sum" is appended

  Scenario: DM-MIX-002 -- Sum three or more numeric columns
    When I select "Numerical Operations" mode
    And I select columns ["cpu_cycles", "instructions", "cache_misses"]
    And I select "Sum" as the operation
    And I click "Preview Merge"
    Then each row satisfies: new_col = cpu_cycles + instructions + cache_misses

  # -------------------------------------------------------------------
  # Numerical Mean
  # -------------------------------------------------------------------
  Scenario: DM-MIX-003 -- Mean (Average) of multiple columns
    When I select "Numerical Operations" mode
    And I select columns ["memory_bandwidth", "execution_time"]
    And I select "Mean (Average)" as the operation
    Then the auto-name is "mean (average)_memory_bandwidth_execution_time"
    When I click "Preview Merge"
    Then each row: new_col = (memory_bandwidth + execution_time) / 2

  # -------------------------------------------------------------------
  # SD Propagation
  # -------------------------------------------------------------------
  Scenario: DM-MIX-004 -- Sum with SD propagation
    Given the dataset has been pre-processed with Seeds Reducer
    And columns "cpu_cycles.sd" and "instructions.sd" exist
    When I select "Numerical Operations" mode
    And I select ["cpu_cycles", "instructions"] to merge
    And I select "Sum"
    And I click "Preview Merge"
    Then I see "Propagated standard deviation to `sum_cpu_cycles_instructions.sd`"
    And the .sd column values equal sqrt(cpu_cycles.sd^2 + instructions.sd^2)

  Scenario: DM-MIX-005 -- Mean with SD propagation
    Given the dataset has .sd columns
    When I select Mean (Average) and merge 2 columns
    And I click "Preview Merge"
    Then the new .sd column equals sqrt(sd1^2 + sd2^2) / N  (where N=2)

  # -------------------------------------------------------------------
  # Configuration Merge (Concatenate)
  # -------------------------------------------------------------------
  Scenario: DM-MIX-006 -- Concatenate string columns with default separator
    When I select "Configuration Merge" mode
    And I select columns ["config_name", "benchmark"]
    Then the operation is locked to "Concatenate"
    And a "Separator" text input appears with default value "_"
    And the auto-name is "concat_config_name_benchmark"
    When I click "Preview Merge"
    Then each row: new_col = config_name + "_" + benchmark
    When I click "Confirm and Merge"
    Then the active dataset contains "concat_config_name_benchmark"
    And the OperationRecord has operation "Mixer: Concatenate"

  Scenario: DM-MIX-007 -- Concatenate with custom separator
    When I select "Configuration Merge" mode
    And I select columns ["config_name", "benchmark"]
    And I change the "Separator" to " -- "
    And I click "Preview Merge"
    Then each row: new_col = config_name + " -- " + benchmark

  Scenario: DM-MIX-008 -- Concatenate mixed types (numeric + string)
    When I select "Configuration Merge" mode
    And I select columns ["config_name", "cpu_cycles"]
    And I click "Preview Merge"
    Then each row: new_col = str(config_name) + "_" + str(cpu_cycles)

  # -------------------------------------------------------------------
  # Mode Switching
  # -------------------------------------------------------------------
  Scenario: DM-MIX-009 -- Switching mode changes available columns and operations
    When I select "Numerical Operations" mode
    Then the column list excludes ".sd" and "_stdev" columns
    And operations are ["Sum", "Mean (Average)"]
    When I switch to "Configuration Merge" mode
    Then the column list includes ALL columns (including string)
    And the only operation is "Concatenate"
    And a "Separator" input appears

  Scenario: DM-MIX-010 -- No mode selected shows info message
    Given the segmented control has no selection
    Then I see "Select a mode to continue."
    And no column selectors or operation widgets are displayed

  # -------------------------------------------------------------------
  # Validation Errors
  # -------------------------------------------------------------------
  Scenario: DM-MIX-011 -- No columns selected shows error
    When I select "Numerical Operations" mode
    And I do not select any columns
    And I click "Preview Merge"
    Then I see an error "At least one column must be selected"

  Scenario: DM-MIX-012 -- Only one column selected shows error
    When I select only one column ["cpu_cycles"]
    And I click "Preview Merge"
    Then I see an error "At least two columns must be selected for merging"

  Scenario: DM-MIX-013 -- Empty column name shows error
    When I select valid columns and operation
    And I clear the "New Column Name" field
    And I click "Preview Merge"
    Then I see an error "New column name cannot be empty"

  Scenario: DM-MIX-014 -- Duplicate column name shows error
    When I enter "cpu_cycles" as the new column name (already exists)
    And I click "Preview Merge"
    Then I see "Column 'cpu_cycles' already exists in DataFrame"

  # -------------------------------------------------------------------
  # History Load
  # -------------------------------------------------------------------
  Scenario: DM-MIX-015 -- Load Mixer Sum record from history
    Given I have previously confirmed a "Mixer: Sum" operation
    When I expand the History section
    And I click the Load button
    Then the mode is set to "Numerical Operations"
    And the source columns are pre-selected
    And the operation is "Sum"
    And the new column name is pre-filled

  Scenario: DM-MIX-016 -- Load Mixer Concatenate record from history
    Given I have previously confirmed a "Mixer: Concatenate" operation
    When I load that record from history
    Then the mode is set to "Configuration Merge"
    And the operation is locked to "Concatenate"
    And source columns and dest name are pre-filled
```

### 7.3 Pytest-Playwright Test Stubs

```python
# tests/e2e/test_data_managers_mixer.py

import pytest
from playwright.sync_api import Page, expect


class TestMixerNumericalSum:
    """DM-MIX-001, DM-MIX-002: Sum operations on numeric columns."""

    def test_sum_two_columns(self, data_managers_page: Page) -> None:
        """DM-MIX-001: Full sum merge flow with preview and confirm."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()
        page.wait_for_selector("text=Mixer (Merge Columns)")

        # Select Numerical Operations mode via segmented control
        page.locator("text=Numerical Operations").click()

        # Select columns to merge
        cols_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Select columns to merge')"
        )
        cols_ms.locator("input").click()
        page.locator("[role='option']:has-text('cpu_cycles')").click()
        page.locator("[role='option']:has-text('instructions')").click()

        # Select Sum operation
        op_select = page.locator(
            "[data-testid='stSelectbox']:has-text('Operation')"
        )
        op_select.locator("select").select_option("Sum")

        # Preview
        page.get_by_role("button", name="Preview Merge").click()
        page.wait_for_selector("text=Created merged column")

        # Confirm
        page.get_by_role("button", name="Confirm and Merge").click()
        page.wait_for_selector("[data-testid='stToast']", timeout=5000)

    def test_sum_multiple_columns(self, data_managers_page: Page) -> None:
        """DM-MIX-002: Sum three columns."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()

        page.locator("text=Numerical Operations").click()

        # Select 3 columns
        cols_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Select columns to merge')"
        )
        cols_ms.locator("input").click()
        for col_name in ["cpu_cycles", "instructions", "cache_misses"]:
            page.locator(f"[role='option']:has-text('{col_name}')").click()

        page.get_by_role("button", name="Preview Merge").click()
        page.wait_for_selector("text=Created merged column")


class TestMixerNumericalMean:
    """DM-MIX-003: Mean (Average) operation."""

    def test_mean_of_two_columns(self, data_managers_page: Page) -> None:
        """DM-MIX-003: Mean creates average of selected columns."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()
        page.locator("text=Numerical Operations").click()

        # Select columns and Mean operation
        # ... (multiselect and selectbox interactions)

        page.get_by_role("button", name="Preview Merge").click()
        page.wait_for_selector("text=Created merged column")


class TestMixerSDPropagation:
    """DM-MIX-004, DM-MIX-005: SD propagation for Sum and Mean."""

    def test_sum_propagates_sd(self, data_managers_page: Page) -> None:
        """DM-MIX-004: Sum creates .sd column via sqrt(sum of variances)."""
        # Requires dataframe_with_sd_columns fixture
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()
        page.locator("text=Numerical Operations").click()

        # Select columns that have .sd counterparts
        # ... (multiselect interactions for cpu_cycles and instructions)

        page.get_by_role("button", name="Preview Merge").click()

        # Should show SD propagation message
        expect(page.locator("text=Propagated standard deviation")).to_be_visible()

    def test_mean_propagates_sd_divided_by_n(
        self, data_managers_page: Page
    ) -> None:
        """DM-MIX-005: Mean SD = sqrt(sum of variances) / N."""
        # Similar to Sum test but with Mean operation
        pass  # Stub


class TestMixerConcatenate:
    """DM-MIX-006, DM-MIX-007, DM-MIX-008: Concatenate operations."""

    def test_concatenate_with_default_separator(
        self, data_managers_page: Page
    ) -> None:
        """DM-MIX-006: Concatenate string columns with '_' separator."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()

        # Switch to Configuration Merge mode
        page.locator("text=Configuration Merge").click()

        # Select string columns
        cols_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Select columns to merge')"
        )
        cols_ms.locator("input").click()
        page.locator("[role='option']:has-text('config_name')").click()
        page.locator("[role='option']:has-text('benchmark')").click()

        # Verify separator input is visible with default "_"
        sep_input = page.locator(
            "[data-testid='stTextInput']:has-text('Separator') input"
        )
        expect(sep_input).to_have_value("_")

        # Preview
        page.get_by_role("button", name="Preview Merge").click()
        page.wait_for_selector("text=Created merged column")

        # Confirm
        page.get_by_role("button", name="Confirm and Merge").click()
        page.wait_for_selector("[data-testid='stToast']", timeout=5000)

    def test_concatenate_with_custom_separator(
        self, data_managers_page: Page
    ) -> None:
        """DM-MIX-007: Custom separator produces correct joined values."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()
        page.locator("text=Configuration Merge").click()

        # Select columns and change separator
        sep_input = page.locator(
            "[data-testid='stTextInput']:has-text('Separator') input"
        )
        sep_input.fill(" -- ")

        page.get_by_role("button", name="Preview Merge").click()
        page.wait_for_selector("text=Created merged column")


class TestMixerModeSwitch:
    """DM-MIX-009, DM-MIX-010: Mode switching behavior."""

    def test_mode_switch_changes_available_operations(
        self, data_managers_page: Page
    ) -> None:
        """DM-MIX-009: Switching mode updates column list and operations."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()

        # Start in Numerical Operations
        page.locator("text=Numerical Operations").click()
        op_select = page.locator(
            "[data-testid='stSelectbox']:has-text('Operation')"
        )
        expect(op_select).to_contain_text("Sum")

        # Switch to Configuration Merge
        page.locator("text=Configuration Merge").click()
        op_select = page.locator(
            "[data-testid='stSelectbox']:has-text('Operation')"
        )
        expect(op_select).to_contain_text("Concatenate")

        # Separator input should appear
        expect(
            page.locator("[data-testid='stTextInput']:has-text('Separator')")
        ).to_be_visible()


class TestMixerValidation:
    """DM-MIX-011 through DM-MIX-014: Validation error paths."""

    def test_no_columns_selected_error(self, data_managers_page: Page) -> None:
        """DM-MIX-011: Empty column selection shows validation error."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()
        page.locator("text=Numerical Operations").click()

        # Do not select any columns, click Preview
        page.get_by_role("button", name="Preview Merge").click()

        expect(
            page.locator("[data-testid='stAlert']:has-text('At least one column')")
        ).to_be_visible()

    def test_single_column_selected_error(self, data_managers_page: Page) -> None:
        """DM-MIX-012: Only one column selected shows error."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()
        page.locator("text=Numerical Operations").click()

        # Select only one column
        cols_ms = page.locator(
            "[data-testid='stMultiSelect']:has-text('Select columns to merge')"
        )
        cols_ms.locator("input").click()
        page.locator("[role='option']:has-text('cpu_cycles')").click()

        page.get_by_role("button", name="Preview Merge").click()

        expect(
            page.locator("[data-testid='stAlert']:has-text('At least two columns')")
        ).to_be_visible()

    def test_empty_column_name_error(self, data_managers_page: Page) -> None:
        """DM-MIX-013: Empty new column name shows error."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()
        page.locator("text=Numerical Operations").click()

        # Select valid columns
        # ... (multiselect interactions)

        # Clear the name field
        name_input = page.locator(
            "[data-testid='stTextInput']:has-text('New Column Name') input"
        )
        name_input.fill("")

        page.get_by_role("button", name="Preview Merge").click()

        expect(
            page.locator("[data-testid='stAlert']:has-text('cannot be empty')")
        ).to_be_visible()

    def test_duplicate_column_name_error(self, data_managers_page: Page) -> None:
        """DM-MIX-014: Existing column name shows error."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()
        page.locator("text=Numerical Operations").click()

        # Select valid columns, then set name to existing column
        name_input = page.locator(
            "[data-testid='stTextInput']:has-text('New Column Name') input"
        )
        name_input.fill("cpu_cycles")

        page.get_by_role("button", name="Preview Merge").click()

        expect(
            page.locator("[data-testid='stAlert']:has-text('already exists')")
        ).to_be_visible()


class TestMixerHistoryLoad:
    """DM-MIX-015, DM-MIX-016: History load behavior."""

    def test_load_sum_record_from_history(self, data_managers_page: Page) -> None:
        """DM-MIX-015: Load restores Numerical mode, columns, operation, name."""
        page = data_managers_page
        page.get_by_role("tab", name="Mixer").click()

        # Step 1: Perform sum operation and confirm
        # ... (full flow)

        # Step 2: Expand history and load
        page.locator("details:has-text('History')").click()
        page.locator("button:has-text('reload')").first.click()

        # Step 3: Verify mode is "Numerical Operations" and values restored
        pass  # Stub

    def test_load_concatenate_record_from_history(
        self, data_managers_page: Page
    ) -> None:
        """DM-MIX-016: Load restores Configuration Merge mode and Concatenate."""
        pass  # Stub
```

---

## 8. Operation History Tests

The Operations History tab (`tab7`) renders the full portfolio history via
`HistoryComponents.render_portfolio_history`. It shows a read-only table of all
operations across all managers, with a total count metric.

### 8.1 Gherkin Scenarios

```gherkin
Feature: Operations History -- Full portfolio operation log

  Background:
    Given the application has loaded the simulation_dataframe
    And I navigate to the "Data Managers" page

  # -------------------------------------------------------------------
  # Empty History
  # -------------------------------------------------------------------
  Scenario: DM-HIST-001 -- Empty history shows warning
    Given no data transformations have been performed
    When I click the "Operations History" tab
    Then I see "No operations have been performed yet."
    And the "Total Operations" metric is absent or shows 0

  # -------------------------------------------------------------------
  # Single Operation
  # -------------------------------------------------------------------
  Scenario: DM-HIST-002 -- Single operation appears in history
    Given I perform a Preprocessor Division operation and confirm
    When I click the "Operations History" tab
    Then the "Total Operations" metric shows 1
    And the history table shows one row with:
      - Operation: "Preprocessor: Division"
      - Source Columns: "instructions, cpu_cycles"
      - Dest Columns: "instructions_per_cpu_cycles"

  # -------------------------------------------------------------------
  # Multiple Operations Across Managers
  # -------------------------------------------------------------------
  Scenario: DM-HIST-003 -- Multiple operations from different managers
    Given I perform (in order):
      1. Preprocessor Division -> confirm
      2. Outlier Remover on execution_time -> confirm
      3. Seeds Reducer -> confirm
    When I click the "Operations History" tab
    Then the "Total Operations" metric shows 3
    And the history table shows 3 rows in reverse chronological order
    And the operations include "Preprocessor: Division",
        "Outlier Removal (Q3)", "Seeds Reduction (mean + stdev)"

  # -------------------------------------------------------------------
  # Per-Manager History
  # -------------------------------------------------------------------
  Scenario: DM-HIST-004 -- Per-manager history shows only filtered records
    Given I perform a Preprocessor Division and a Mixer Sum
    When I navigate to the "Preprocessor" tab
    And I expand the "History" expander
    Then I see only the Preprocessor record (not the Mixer record)
    When I navigate to the "Mixer" tab
    And I expand the "History" expander
    Then I see only the Mixer record (not the Preprocessor record)

  # -------------------------------------------------------------------
  # History Delete
  # -------------------------------------------------------------------
  Scenario: DM-HIST-005 -- Delete history record removes it from list
    Given I have 2 operations in history
    When I navigate to a manager tab
    And I expand the History expander
    And I click the Delete button for the first record
    Then the record is removed
    And the Operations History tab shows 1 operation

  # -------------------------------------------------------------------
  # History Table Formatting
  # -------------------------------------------------------------------
  Scenario: DM-HIST-006 -- History table displays formatted timestamps
    Given I have confirmed an operation
    When I view the Operations History tab
    Then the Timestamp column shows "YYYY-MM-DD HH:MM:SS" format
    And the timestamp is truncated from the ISO-8601 string (first 19 chars)
```

### 8.2 Pytest-Playwright Test Stubs

```python
# tests/e2e/test_data_managers_history.py

import pytest
from playwright.sync_api import Page, expect


class TestOperationsHistoryEmpty:
    """DM-HIST-001: Empty history behavior."""

    def test_empty_history_shows_warning(self, data_managers_page: Page) -> None:
        """DM-HIST-001: No operations yet shows warning message."""
        page = data_managers_page
        page.get_by_role("tab", name="Operations History").click()

        expect(
            page.locator("text=No operations have been performed yet")
        ).to_be_visible()


class TestOperationsHistorySingle:
    """DM-HIST-002: Single operation in history."""

    def test_single_operation_in_history(self, data_managers_page: Page) -> None:
        """DM-HIST-002: After one operation, history shows one row."""
        page = data_managers_page

        # Perform a Preprocessor operation first
        page.get_by_role("tab", name="Preprocessor").click()
        # ... (configure, preview, confirm)

        # Check Operations History
        page.get_by_role("tab", name="Operations History").click()

        # Verify total operations metric
        expect(
            page.locator("[data-testid='stMetric']:has-text('Total Operations')")
        ).to_contain_text("1")

        # Verify table has the operation
        expect(page.locator("[data-testid='stDataFrame']")).to_be_visible()


class TestOperationsHistoryMultiple:
    """DM-HIST-003: Multiple operations across managers."""

    def test_multiple_operations_appear_in_order(
        self, data_managers_page: Page
    ) -> None:
        """DM-HIST-003: Operations from multiple managers all appear."""
        page = data_managers_page

        # Perform multiple operations across different tabs
        # ... (Preprocessor, Outlier Remover, Seeds Reducer -- each configured)

        page.get_by_role("tab", name="Operations History").click()

        # Verify count
        expect(
            page.locator("[data-testid='stMetric']:has-text('Total Operations')")
        ).to_contain_text("3")


class TestPerManagerHistory:
    """DM-HIST-004: Per-manager history filtering."""

    def test_per_manager_history_filtered(self, data_managers_page: Page) -> None:
        """DM-HIST-004: Each manager tab shows only its own history."""
        page = data_managers_page

        # Perform Preprocessor and Mixer operations
        # ...

        # Preprocessor tab should only show Preprocessor records
        page.get_by_role("tab", name="Preprocessor").click()
        page.locator("details:has-text('History')").click()
        expect(page.locator("text=Division")).to_be_visible()
        expect(page.locator("text=Sum")).to_have_count(0)  # Mixer Sum not shown


class TestHistoryDelete:
    """DM-HIST-005: Delete removes record from history."""

    def test_delete_history_record(self, data_managers_page: Page) -> None:
        """DM-HIST-005: Delete button removes the record."""
        page = data_managers_page

        # Create 2 operations, then delete one from per-manager history
        # ... (configure, preview, confirm twice)

        page.locator("details:has-text('History')").click()
        delete_buttons = page.locator("button:has-text('delete')")
        initial_count = delete_buttons.count()

        delete_buttons.first.click()
        page.wait_for_timeout(1000)

        # One fewer record in history
        assert page.locator("button:has-text('delete')").count() < initial_count
```

---

## 9. Preview & Validation Tests

### 9.1 Cross-Cutting Preview Protocol Tests

These tests verify the two-step Preview-then-Confirm protocol that is shared across
all four data transformation managers.

```gherkin
Feature: Preview & Confirm Protocol -- Cross-cutting behavior

  Scenario: DM-PV-001 -- Confirm button only appears after successful preview
    Given I am in any manager tab (Preprocessor, Seeds Reducer, Outlier, Mixer)
    Then no "Confirm" button is visible initially
    When I click the Preview/Apply button with valid inputs
    Then the "Confirm" button appears with type="primary" styling
    When I click "Confirm"
    Then the dataset is updated
    And the preview is cleared (Confirm button disappears)

  Scenario: DM-PV-002 -- Preview is stored in PreviewRepository, not dataset
    When I click Preview in Preprocessor
    And I navigate to Summary tab
    Then the column count is unchanged
    And the row count is unchanged
    When I return to Preprocessor and click Confirm
    Then the dataset is updated

  Scenario: DM-PV-003 -- Failed preview shows exception, no Confirm button
    Given I force an exception in the service layer (e.g., incompatible types)
    When I click Preview
    Then st.exception displays the error
    And the Confirm button does NOT appear

  Scenario: DM-PV-004 -- Preview dataframe shows head(10) or head(20) rows
    When I preview in Preprocessor
    Then the preview table shows at most 10 rows
    When I preview in Seeds Reducer
    Then the result preview shows at most 20 rows

  Scenario: DM-PV-005 -- Each preview key is independent (no cross-pollution)
    When I preview in Preprocessor (key: "preprocessor")
    And I preview in Mixer (key: "mixer")
    Then both Confirm buttons are visible in their respective tabs
    When I confirm in Preprocessor
    Then only the Preprocessor preview is cleared
    And the Mixer Confirm button remains visible
```

### 9.2 Validation Error Compilation

| Manager | Validation Method | Error Conditions |
|---------|------------------|-----------------|
| Preprocessor | (inline) | No numeric columns in dataset |
| Seeds Reducer | `validate_seeds_reducer_inputs` | No categorical cols selected; no statistic cols selected; missing columns; non-numeric statistic col |
| Outlier Remover | `validate_outlier_inputs` | Empty outlier col; missing outlier col; non-numeric outlier col; missing group-by cols |
| Mixer | `validate_merge_inputs` | No columns selected; < 2 columns; missing columns; invalid operation; empty name; duplicate name |

---

## 10. Error Handling Scenarios

### 10.1 No Data Loaded Guard

```gherkin
Feature: Data Managers -- No data loaded guard

  Scenario: DM-ERR-001 -- Page with no data shows warning
    Given no data has been loaded into the application
    When I navigate to the Data Managers page
    Then I see "No data loaded. Please load data from the **Data Source** page."
    And only the Summary tab content is rendered (with warning)
    And the other tabs are empty or not rendered

  Scenario: DM-ERR-002 -- Data retrieval failure shows error
    Given has_data() returns True but get_data() returns None
    When I navigate to the Data Managers page
    Then I see "Failed to retrieve data."
    And no manager tabs are rendered
```

### 10.2 Service-Level Exception Handling

```gherkin
Feature: Data Managers -- Service exception is caught

  Scenario: DM-ERR-003 -- ArithmeticService unknown operation raises ValueError
    Given an unknown operation string is passed to apply_operation
    When the preview is attempted
    Then st.exception displays "Unknown operation: ..."

  Scenario: DM-ERR-004 -- Mixer unknown operation raises ValueError
    Given an invalid mixer operation (not Sum/Mean/Concatenate)
    When apply_mixer is called
    Then st.exception displays "Unknown mixer operation: ..."

  Scenario: DM-ERR-005 -- Empty DataFrame passed to reduce_seeds
    Given the DataFrame is empty
    When Seeds Reducer applies reduction
    Then the service returns the empty DataFrame without error
    And no crash occurs
```

### 10.3 Pytest-Playwright Stubs for Error Scenarios

```python
# tests/e2e/test_data_managers_errors.py

import pytest
from playwright.sync_api import Page, expect


class TestNoDataGuard:
    """DM-ERR-001, DM-ERR-002: Page guard when no data loaded."""

    def test_no_data_shows_warning(self, page: Page) -> None:
        """DM-ERR-001: Without data, page shows warning."""
        page.goto("http://localhost:8501/Data_Managers")
        page.wait_for_selector("text=Data Managers & Transformations")

        expect(page.locator("text=No data loaded")).to_be_visible()
        expect(page.locator("text=Data Source")).to_be_visible()

    def test_data_retrieval_failure_shows_error(self, page: Page) -> None:
        """DM-ERR-002: has_data()=True but get_data()=None shows error."""
        # This requires mocking the state_manager or injecting a broken state
        pass  # Stub


class TestServiceExceptions:
    """DM-ERR-003 through DM-ERR-005: Service-level errors caught by UI."""

    def test_unknown_operation_shows_exception(
        self, data_managers_page: Page
    ) -> None:
        """DM-ERR-003: Invalid operation string causes st.exception display."""
        # This scenario is hard to trigger via UI since the selectbox
        # constrains options. Would require mocking or direct API test.
        pass  # Stub
```

---

## 11. Page Object Model for DataManagersPage

### 11.1 Complete POM Class

```python
# tests/e2e/pages/data_managers_page.py

from __future__ import annotations

from dataclasses import dataclass
from playwright.sync_api import Page, Locator, expect


@dataclass
class ManagerHistoryEntry:
    """Parsed representation of a single history record in the UI."""
    timestamp: str
    operation: str
    source_columns: str
    dest_columns: str


class DataManagersPage:
    """Page Object Model for the Data Managers page.

    Encapsulates all tab navigation, widget interaction, and assertion
    helpers for the Data Managers page (/Data_Managers).

    Usage:
        dm_page = DataManagersPage(page)
        dm_page.navigate()
        dm_page.go_to_tab("Preprocessor")
        dm_page.preprocessor.set_source_column_1("instructions")
        dm_page.preprocessor.set_operation("Division")
        dm_page.preprocessor.set_source_column_2("cpu_cycles")
        dm_page.preprocessor.click_preview()
        dm_page.preprocessor.click_confirm()
    """

    URL = "http://localhost:8501/Data_Managers"

    def __init__(self, page: Page) -> None:
        self.page = page
        self.preprocessor = PreprocessorSection(page)
        self.seeds_reducer = SeedsReducerSection(page)
        self.outlier_remover = OutlierRemoverSection(page)
        self.mixer = MixerSection(page)
        self.summary = SummarySection(page)
        self.history = HistorySection(page)

    # ── Navigation ────────────────────────────────────────────────

    def navigate(self) -> None:
        """Navigate to the Data Managers page and wait for load."""
        self.page.goto(self.URL)
        self.page.wait_for_selector(
            "text=Data Managers & Transformations", timeout=10000
        )

    def go_to_tab(self, tab_name: str) -> None:
        """Click a tab by its visible label."""
        self.page.get_by_role("tab", name=tab_name).click()

    def get_visible_tabs(self) -> list[str]:
        """Return the text of all visible tab labels."""
        tabs = self.page.get_by_role("tab").all()
        return [tab.inner_text() for tab in tabs]

    # ── Assertions ────────────────────────────────────────────────

    def assert_no_data_warning(self) -> None:
        """Assert that the 'No data loaded' warning is visible."""
        expect(self.page.locator("text=No data loaded")).to_be_visible()

    def assert_no_exceptions(self) -> None:
        """Assert no st.exception is displayed anywhere on the page."""
        expect(self.page.locator("[data-testid='stException']")).to_have_count(0)

    def wait_for_toast(self, text: str, timeout: int = 5000) -> None:
        """Wait for a toast notification containing the given text."""
        self.page.wait_for_selector(
            f"[data-testid='stToast']:has-text('{text}')", timeout=timeout
        )


class SummarySection:
    """POM for the Summary tab."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def get_row_count(self) -> str:
        return self._get_metric_value("Rows")

    def get_column_count(self) -> str:
        return self._get_metric_value("Columns")

    def get_memory_usage(self) -> str:
        return self._get_metric_value("Memory")

    def get_missing_values(self) -> str:
        return self._get_metric_value("Missing Values")

    def _get_metric_value(self, label: str) -> str:
        metric = self.page.locator(
            f"[data-testid='stMetric']:has-text('{label}')"
        )
        return metric.locator("[data-testid='stMetricValue']").inner_text()


class PreprocessorSection:
    """POM for the Preprocessor tab."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def set_source_column_1(self, col: str) -> None:
        box = self.page.locator(
            "[data-testid='stSelectbox']:has-text('Source Column 1')"
        )
        box.locator("select").select_option(col)

    def set_operation(self, op: str) -> None:
        box = self.page.locator(
            "[data-testid='stSelectbox']:has-text('Operation')"
        )
        box.locator("select").select_option(op)

    def set_source_column_2(self, col: str) -> None:
        box = self.page.locator(
            "[data-testid='stSelectbox']:has-text('Source Column 2')"
        )
        box.locator("select").select_option(col)

    def get_new_column_name(self) -> str:
        inp = self.page.locator(
            "[data-testid='stTextInput']:has-text('New column name') input"
        )
        return inp.input_value()

    def set_new_column_name(self, name: str) -> None:
        inp = self.page.locator(
            "[data-testid='stTextInput']:has-text('New column name') input"
        )
        inp.fill(name)

    def click_preview(self) -> None:
        self.page.get_by_role("button", name="Preview Result").click()
        self.page.wait_for_selector("text=Created column", timeout=5000)

    def click_confirm(self) -> None:
        self.page.get_by_role(
            "button", name="Confirm and Add Column to Dataset"
        ).click()

    def is_confirm_visible(self) -> bool:
        return self.page.get_by_role(
            "button", name="Confirm and Add Column to Dataset"
        ).is_visible()

    def assert_preview_visible(self) -> None:
        expect(
            self.page.locator("[data-testid='stDataFrame']").first
        ).to_be_visible()

    def assert_statistics_visible(self) -> None:
        expect(self.page.locator("text=Statistics")).to_be_visible()


class SeedsReducerSection:
    """POM for the Seeds Reducer tab."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def get_reduce_column(self) -> str:
        box = self.page.locator(
            "[data-testid='stSelectbox']:has-text('Column to reduce over')"
        )
        return box.locator("select").input_value()

    def set_reduce_column(self, col: str) -> None:
        box = self.page.locator(
            "[data-testid='stSelectbox']:has-text('Column to reduce over')"
        )
        box.locator("select").select_option(col)

    def clear_categorical_columns(self) -> None:
        ms = self.page.locator(
            "[data-testid='stMultiSelect']:has-text('Group by columns')"
        )
        clear_btn = ms.locator("button[aria-label='Clear all']")
        if clear_btn.is_visible():
            clear_btn.click()

    def clear_statistic_columns(self) -> None:
        ms = self.page.locator(
            "[data-testid='stMultiSelect']:has-text('Calculate stats for')"
        )
        clear_btn = ms.locator("button[aria-label='Clear all']")
        if clear_btn.is_visible():
            clear_btn.click()

    def click_apply(self) -> None:
        self.page.get_by_role("button", name="Apply Seeds Reducer").click()

    def click_confirm(self) -> None:
        self.page.get_by_role(
            "button", name="Confirm and Apply Seeds Reducer"
        ).click()

    def get_original_rows(self) -> str:
        return self.page.locator(
            "[data-testid='stMetric']:has-text('Original Rows')"
        ).locator("[data-testid='stMetricValue']").inner_text()

    def get_reduced_rows(self) -> str:
        return self.page.locator(
            "[data-testid='stMetric']:has-text('Reduced Rows')"
        ).locator("[data-testid='stMetricValue']").inner_text()


class OutlierRemoverSection:
    """POM for the Outlier Remover tab."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def set_outlier_column(self, col: str) -> None:
        box = self.page.locator(
            "[data-testid='stSelectbox']:has-text('Column to check for outliers')"
        )
        box.locator("select").select_option(col)

    def clear_group_by_columns(self) -> None:
        ms = self.page.locator(
            "[data-testid='stMultiSelect']:has-text('Group by columns')"
        )
        clear_btn = ms.locator("button[aria-label='Clear all']")
        if clear_btn.is_visible():
            clear_btn.click()

    def click_apply(self) -> None:
        self.page.get_by_role("button", name="Apply Outlier Remover").click()

    def click_confirm(self) -> None:
        self.page.get_by_role(
            "button", name="Confirm and Apply Outlier Remover"
        ).click()

    def get_removed_count(self) -> str:
        return self.page.locator(
            "[data-testid='stMetric']:has-text('Removed')"
        ).locator("[data-testid='stMetricValue']").inner_text()

    def get_distribution_metric(self, label: str) -> str:
        metric = self.page.locator(
            f"[data-testid='stMetric']:has-text('{label}')"
        )
        return metric.locator("[data-testid='stMetricValue']").inner_text()


class MixerSection:
    """POM for the Mixer tab."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def set_mode(self, mode: str) -> None:
        """Select mixer mode via segmented control."""
        self.page.locator(f"text={mode}").click()

    def add_column(self, col_name: str) -> None:
        """Add a column to the multiselect."""
        ms = self.page.locator(
            "[data-testid='stMultiSelect']:has-text('Select columns to merge')"
        )
        ms.locator("input").click()
        self.page.locator(f"[role='option']:has-text('{col_name}')").click()

    def set_operation(self, op: str) -> None:
        box = self.page.locator(
            "[data-testid='stSelectbox']:has-text('Operation')"
        )
        box.locator("select").select_option(op)

    def set_separator(self, sep: str) -> None:
        inp = self.page.locator(
            "[data-testid='stTextInput']:has-text('Separator') input"
        )
        inp.fill(sep)

    def set_new_column_name(self, name: str) -> None:
        inp = self.page.locator(
            "[data-testid='stTextInput']:has-text('New Column Name') input"
        )
        inp.fill(name)

    def click_preview(self) -> None:
        self.page.get_by_role("button", name="Preview Merge").click()

    def click_confirm(self) -> None:
        self.page.get_by_role("button", name="Confirm and Merge").click()


class HistorySection:
    """POM for the Operations History tab and per-manager history expanders."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def get_total_operations_count(self) -> str:
        return self.page.locator(
            "[data-testid='stMetric']:has-text('Total Operations')"
        ).locator("[data-testid='stMetricValue']").inner_text()

    def assert_empty_history_warning(self) -> None:
        expect(
            self.page.locator("text=No operations have been performed yet")
        ).to_be_visible()

    def expand_manager_history(self) -> None:
        """Expand the per-manager history expander (within a manager tab)."""
        self.page.locator("details:has-text('History')").click()

    def get_history_entries(self) -> list[Locator]:
        """Return all history entry rows in the current expander."""
        return self.page.locator(
            "details:has-text('History') [data-testid='column']"
        ).all()

    def click_load_button(self, index: int = 0) -> None:
        """Click the Load (reload) button for a history entry."""
        buttons = self.page.locator(
            "details:has-text('History') button:has-text('reload')"
        )
        buttons.nth(index).click()

    def click_delete_button(self, index: int = 0) -> None:
        """Click the Delete button for a history entry."""
        buttons = self.page.locator(
            "details:has-text('History') button:has-text('delete')"
        )
        buttons.nth(index).click()
```

### 11.2 Complete POM Usage Example

```python
# tests/e2e/test_data_managers_full_flow.py

from tests.e2e.pages.data_managers_page import DataManagersPage


class TestFullDataTransformationPipeline:
    """Integration test: Full data pipeline through all managers."""

    def test_complete_pipeline(self, page) -> None:
        """DM-INT-001: Data flows through Preprocessor -> Seeds Reducer -> Outlier."""
        dm = DataManagersPage(page)
        dm.navigate()

        # Step 1: Create IPC column via Preprocessor
        dm.go_to_tab("Preprocessor")
        dm.preprocessor.set_source_column_1("instructions")
        dm.preprocessor.set_operation("Division")
        dm.preprocessor.set_source_column_2("cpu_cycles")
        dm.preprocessor.set_new_column_name("IPC")
        dm.preprocessor.click_preview()
        dm.preprocessor.click_confirm()
        dm.wait_for_toast("Column added")

        # Step 2: Reduce seeds
        dm.go_to_tab("Seeds Reducer")
        dm.seeds_reducer.click_apply()
        dm.seeds_reducer.click_confirm()
        dm.wait_for_toast("Seeds-reduced")

        # Step 3: Remove outliers from IPC
        dm.go_to_tab("Outlier Remover")
        dm.outlier_remover.set_outlier_column("IPC")
        dm.outlier_remover.click_apply()
        dm.outlier_remover.click_confirm()
        dm.wait_for_toast("Outlier-filtered")

        # Step 4: Verify final state via Summary
        dm.go_to_tab("Summary")
        # Dataset should have fewer rows (seeds reduced, outliers removed)
        # and additional columns (IPC, IPC.sd)

        # Step 5: Verify Operations History
        dm.go_to_tab("Operations History")
        assert dm.history.get_total_operations_count() == "3"
        dm.assert_no_exceptions()
```

---

## Test ID Summary

| ID | Section | Description |
|----|---------|-------------|
| DM-PRE-001 | Preprocessor | Division creates ratio column |
| DM-PRE-002 | Preprocessor | Division by zero produces NaN |
| DM-PRE-003 | Preprocessor | Sum adds two numeric columns |
| DM-PRE-004 | Preprocessor | Subtraction creates difference |
| DM-PRE-005 | Preprocessor | Multiplication creates product |
| DM-PRE-006 | Preprocessor | Custom column name override |
| DM-PRE-007 | Preprocessor | Preview does not mutate dataset |
| DM-PRE-008 | Preprocessor | Only numeric columns in selectboxes |
| DM-PRE-009 | Preprocessor | History load pre-fills widgets |
| DM-PRE-010 | Preprocessor | History load warns on missing columns |
| DM-PRE-011 | Preprocessor | No numeric columns warning |
| DM-SR-001 | Seeds Reducer | Default reduction over random_seed |
| DM-SR-002 | Seeds Reducer | Correct mean and std values |
| DM-SR-003 | Seeds Reducer | Partial numeric column selection |
| DM-SR-004 | Seeds Reducer | Partial categorical changes group count |
| DM-SR-005 | Seeds Reducer | Reduce over a different column |
| DM-SR-006 | Seeds Reducer | No categorical columns error |
| DM-SR-007 | Seeds Reducer | No statistic columns error |
| DM-SR-008 | Seeds Reducer | Candidate filtering by uniqueness |
| DM-SR-009 | Seeds Reducer | Auto-select random_seed as default |
| DM-SR-010 | Seeds Reducer | No categorical columns warning |
| DM-SR-011 | Seeds Reducer | No numeric columns warning |
| DM-SR-012 | Seeds Reducer | History load restores selections |
| DM-SR-013 | Seeds Reducer | History load warns on missing columns |
| DM-OR-001 | Outlier Remover | Grouped outlier removal default |
| DM-OR-002 | Outlier Remover | Distribution metrics update on column |
| DM-OR-003 | Outlier Remover | Global outlier removal (no grouping) |
| DM-OR-004 | Outlier Remover | No categorical uses global Q3 |
| DM-OR-005 | Outlier Remover | Default excludes seed-like columns |
| DM-OR-006 | Outlier Remover | No outliers found zero-removal |
| DM-OR-007 | Outlier Remover | Empty outlier column validation |
| DM-OR-008 | Outlier Remover | Non-numeric outlier column error |
| DM-OR-009 | Outlier Remover | Missing group-by column error |
| DM-OR-010 | Outlier Remover | History load restores config |
| DM-OR-011 | Outlier Remover | History load warns on missing columns |
| DM-MIX-001 | Mixer | Sum two numeric columns |
| DM-MIX-002 | Mixer | Sum three or more columns |
| DM-MIX-003 | Mixer | Mean (Average) of multiple columns |
| DM-MIX-004 | Mixer | Sum with SD propagation |
| DM-MIX-005 | Mixer | Mean with SD propagation (/ N) |
| DM-MIX-006 | Mixer | Concatenate with default separator |
| DM-MIX-007 | Mixer | Concatenate with custom separator |
| DM-MIX-008 | Mixer | Concatenate mixed types |
| DM-MIX-009 | Mixer | Mode switch changes operations |
| DM-MIX-010 | Mixer | No mode selected shows info |
| DM-MIX-011 | Mixer | No columns selected error |
| DM-MIX-012 | Mixer | Single column selected error |
| DM-MIX-013 | Mixer | Empty column name error |
| DM-MIX-014 | Mixer | Duplicate column name error |
| DM-MIX-015 | Mixer | History load Sum record |
| DM-MIX-016 | Mixer | History load Concatenate record |
| DM-HIST-001 | History | Empty history warning |
| DM-HIST-002 | History | Single operation in history |
| DM-HIST-003 | History | Multiple operations across managers |
| DM-HIST-004 | History | Per-manager history filtering |
| DM-HIST-005 | History | Delete removes record |
| DM-HIST-006 | History | Timestamp formatting |
| DM-PV-001 | Preview | Confirm appears after successful preview |
| DM-PV-002 | Preview | Preview stored in repository, not dataset |
| DM-PV-003 | Preview | Failed preview shows exception, no confirm |
| DM-PV-004 | Preview | Preview dataframe row limits |
| DM-PV-005 | Preview | Independent preview keys per manager |
| DM-ERR-001 | Error | No data loaded guard |
| DM-ERR-002 | Error | Data retrieval failure |
| DM-ERR-003 | Error | Unknown arithmetic operation |
| DM-ERR-004 | Error | Unknown mixer operation |
| DM-ERR-005 | Error | Empty DataFrame to reduce_seeds |
| DM-INT-001 | Integration | Full pipeline: Preprocessor -> Seeds -> Outlier |

**Total: 56 test scenarios** across 11 sections covering all 4 data managers,
history, preview protocol, validation, and error handling.
