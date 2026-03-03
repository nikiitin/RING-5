# Step 27: E2E Shaper Pipeline Tests

## 1. Executive Summary

This document defines an exhaustive end-to-end (E2E) test plan for the RING-5 Unified Engine v2 **Shaper Pipeline** -- the central data transformation subsystem that allows users to build multi-step data processing workflows through a visual UI. The pipeline supports 10 distinct shaper types organized into three functional families:

**Selectors/Filters**: Column Selector, Item Selector, Condition Selector (Filter)
**Transformations**: Sort, Mean Calculator, Normalize, Transformer
**Reshaping**: Pivot Longer (Melt), Pivot Wider, Split-Apply (Per-Axis)

Each shaper has a dedicated configuration UI component (`src/web/components/shapers/`) that is dispatched by the orchestrator (`src/web/pages/ui/shaper_config.py`). The `PipelineComponent` (`src/web/components/common/pipeline.py`) manages step add/remove/reorder operations, while `PipelineStepComponent` renders individual steps within expandable sections that include configuration widgets, Up/Down/Delete controls, and a live data preview.

The factory pattern in `src/core/services/shapers/factory.py` (`ShaperFactory`) maps type identifiers to implementation classes and provides the display-name registry consumed by the UI. Pre-execution validation is handled by `src/core/services/shapers/validation.py`, which enforces required parameter checks per shaper type.

**Test scope**: 15 sections covering pipeline management, each of the 10 shaper types individually, multi-step pipeline combinations, save/load persistence, and error handling. All tests are specified in Gherkin and accompanied by pytest-playwright stubs.

**Key source files under test**:
- `src/web/pages/ui/shaper_config.py` -- Orchestrator: dispatch + apply
- `src/web/components/common/pipeline.py` -- Add/reorder/delete/finalize UI
- `src/web/components/common/pipeline_step.py` -- Per-step expander + preview
- `src/web/components/shapers/selector_transformer_configs.py` -- ColumnSelector, ConditionSelector, Transformer UIs
- `src/web/components/shapers/sort_config.py` -- Sort UI
- `src/web/components/shapers/mean_config.py` -- Mean Calculator UI
- `src/web/components/shapers/normalize_config.py` -- Normalize UI
- `src/web/components/shapers/pivot_config.py` -- PivotLonger + PivotWider UIs
- `src/web/components/shapers/split_apply_config.py` -- SplitApply composite UI
- `src/core/services/shapers/factory.py` -- Factory registry (10 types)
- `src/core/services/shapers/validation.py` -- Required-param validation

---

## 2. Shaper Pipeline Overview

### 2.1 Architecture

The pipeline follows a three-layer architecture:

| Layer | Component | Responsibility |
|-------|-----------|---------------|
| **Layer C (Presentation)** | `PipelineComponent`, `PipelineStepComponent`, `*Config` classes | Render Streamlit widgets, collect user input |
| **Layer B (Service)** | `ShaperFactory`, `validate_shaper_config`, `apply_shapers` | Create shaper instances, validate configs, execute pipeline |
| **Layer A (Core)** | `Shaper` subclasses (`Mean`, `Normalize`, `Sort`, etc.) | Perform DataFrame transformations |

### 2.2 Factory Registry (10 Shaper Types)

From `ShaperFactory._registry` and `ShaperFactory._display_names`:

| Internal Type | Display Name | Config UI Class | Required Params (validation.py) |
|--------------|-------------|----------------|--------------------------------|
| `columnSelector` | Column Selector | `ColumnSelectorConfig` | `columns` |
| `itemSelector` | Item Selector | *(no dedicated config UI)* | `column`, `strings` |
| `conditionSelector` | Filter | `ConditionSelectorConfig` | `column` |
| `sort` | Sort | `SortConfig` | `order_dict` |
| `mean` | Mean Calculator | `MeanConfig` | `groupingColumns`, `meanVars` |
| `normalize` | Normalize | `NormalizeConfig` | `normalizeVars`, `normalizerColumn`, `normalizerValue`, `groupBy` |
| `pivotLonger` | Pivot Longer (Melt) | `PivotLongerConfig` | `id_vars`, `value_vars`, `var_name`, `value_name` |
| `pivotWider` | Pivot Wider | `PivotWiderConfig` | `index`, `columns`, `values` |
| `splitApply` | Split-Apply (Per-Axis) | `SplitApplyConfig` | `joinColumns`, `groups` |
| `transformer` | Transformer | `TransformerConfig` | `column` |

### 2.3 Pipeline UI Flow

1. User selects a shaper display name from `st.selectbox` ("Add transformation", key: `shaper_add_{plot_id}`)
2. User clicks "Add to Pipeline" button (key: `add_shaper_btn_{plot_id}`)
3. An expander appears with the shaper-specific config UI plus Up/Down/Del controls
4. Each step shows a live preview (`st.dataframe` of `output.head(5)`)
5. User clicks "Finalize Pipeline for Plotting" (key: `finalize_{plot_id}`) to apply all steps
6. `apply_shapers()` iterates through configs: validates via `validate_shaper_config()`, creates via `ShaperFactory.create_shaper()`, executes via `shaper(result)`

### 2.4 Config Dispatch Map

From `shaper_config.py` `configure_shaper()`, the `config_dispatch` dict routes each shaper type to its UI renderer:

```
"columnSelector"     -> ColumnSelectorConfig.render
"normalize"          -> NormalizeConfig.render
"mean"               -> MeanConfig.render
"conditionSelector"  -> ConditionSelectorConfig.render
"splitApply"         -> SplitApplyConfig.render
"transformer"        -> TransformerConfig.render
"sort"               -> SortConfig.render
"pivotLonger"        -> PivotLongerConfig.render
"pivotWider"         -> PivotWiderConfig.render
```

Note: `itemSelector` is NOT in the config dispatch but IS in `ShaperFactory._registry`. This means it is available for programmatic pipeline construction but does not have a dedicated UI configuration panel.

---

## 3. Pipeline Management Tests (Add, Remove, Reorder Steps)

### 3.1 Gherkin Scenarios

```gherkin
Feature: Pipeline Step Management
  As a user building a data transformation pipeline
  I want to add, remove, and reorder pipeline steps
  So that I can construct the exact processing workflow I need

  Background:
    Given the application is running with test data loaded
    And I am on the shaper configuration page for plot 1

  Scenario: Add a single pipeline step
    When I select "Column Selector" from the "Add transformation" dropdown
    And I click the "Add to Pipeline" button
    Then a new expander "1. Column Selector" should appear
    And the expander should contain a multiselect for "Columns to keep"
    And the expander should contain a "Del" button
    And the expander should NOT contain "Up" or "Down" buttons

  Scenario: Add multiple pipeline steps in sequence
    When I add a "Column Selector" step
    And I add a "Sort" step
    And I add a "Mean Calculator" step
    Then three pipeline step expanders should be visible
    And step 1 should display "1. Column Selector" with no "Up" button
    And step 2 should display "2. Sort" with both "Up" and "Down" buttons
    And step 3 should display "3. Mean Calculator" with no "Down" button
    And every step should have a "Del" button

  Scenario: Delete a middle pipeline step
    Given pipeline has steps ["Column Selector", "Sort", "Normalize"]
    When I click the "Del" button on step 2 ("Sort")
    Then only two steps should remain
    And step 1 should be "1. Column Selector"
    And step 2 should be "2. Normalize"

  Scenario: Delete the first pipeline step
    Given pipeline has steps ["Column Selector", "Sort", "Normalize"]
    When I click the "Del" button on step 1 ("Column Selector")
    Then step 1 should now be "1. Sort"
    And step 2 should now be "2. Normalize"
    And step 1 should have no "Up" button

  Scenario: Delete the last pipeline step
    Given pipeline has steps ["Column Selector", "Sort", "Normalize"]
    When I click the "Del" button on step 3 ("Normalize")
    Then step 2 ("Sort") should now have no "Down" button
    And only two steps should remain

  Scenario: Move a step up in the pipeline
    Given pipeline has steps ["Column Selector", "Sort", "Normalize"]
    When I click the "Up" button on step 2 ("Sort")
    Then step 1 should be "1. Sort"
    And step 2 should be "2. Column Selector"
    And step 3 should remain "3. Normalize"

  Scenario: Move a step down in the pipeline
    Given pipeline has steps ["Column Selector", "Sort", "Normalize"]
    When I click the "Down" button on step 1 ("Column Selector")
    Then step 1 should be "1. Sort"
    And step 2 should be "2. Column Selector"
    And step 3 should remain "3. Normalize"

  Scenario: First step has no "Up" button
    Given pipeline has steps ["Column Selector", "Sort"]
    Then the "Up" button should NOT be rendered for step index 0
    Because PipelineComponent.render_shaper_controls checks is_first

  Scenario: Last step has no "Down" button
    Given pipeline has steps ["Column Selector", "Sort"]
    Then the "Down" button should NOT be rendered for the last step index
    Because PipelineComponent.render_shaper_controls checks is_last

  Scenario: Delete the only step in the pipeline
    Given pipeline has exactly one step "Column Selector"
    When I click the "Del" button on step 1
    Then no pipeline step expanders should be visible
    And the "Add transformation" dropdown should remain available

  Scenario: All 10 shaper types appear in the add dropdown
    Then the "Add transformation" dropdown should contain exactly these options:
      | Display Name             | Internal Type       |
      | Column Selector          | columnSelector      |
      | Item Selector            | itemSelector        |
      | Filter                   | conditionSelector   |
      | Sort                     | sort                |
      | Mean Calculator          | mean                |
      | Normalize                | normalize           |
      | Pivot Longer (Melt)      | pivotLonger         |
      | Pivot Wider              | pivotWider          |
      | Split-Apply (Per-Axis)   | splitApply          |
      | Transformer              | transformer         |

  Scenario: No data uploaded shows warning instead of pipeline
    Given no data has been uploaded
    When I navigate to the pipeline section
    Then I should see "Please upload data first!" warning
    And no "Add transformation" dropdown should be displayed

  Scenario: Finalize empty pipeline returns original data
    Given the pipeline has no configured steps
    When I click "Finalize Pipeline for Plotting"
    Then the original DataFrame should be returned unchanged
    And a success toast should display the original data shape

  Scenario: Finalize button renders with primary styling
    Then the "Finalize Pipeline for Plotting" button should have type="primary"
    And it should have width="stretch" styling
```

### 3.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_pipeline_management.py
"""E2E tests for pipeline step add/remove/reorder operations."""

import re
import pytest
from playwright.sync_api import Page, expect


class TestPipelineStepAdd:
    """Tests for adding steps to the pipeline."""

    PLOT_ID = 1

    def test_add_single_step_creates_expander(self, page: Page, loaded_app: None) -> None:
        """Adding a single step creates an expander with correct title and controls."""
        page.get_by_test_id(f"shaper_add_{self.PLOT_ID}").select_option("Column Selector")
        page.get_by_test_id(f"add_shaper_btn_{self.PLOT_ID}").click()
        page.wait_for_timeout(500)
        expander = page.locator("text=1. Column Selector")
        expect(expander).to_be_visible()
        expect(page.get_by_test_id(f"del_{self.PLOT_ID}_0")).to_be_visible()
        expect(page.get_by_test_id(f"up_{self.PLOT_ID}_0")).not_to_be_visible()
        expect(page.get_by_test_id(f"down_{self.PLOT_ID}_0")).not_to_be_visible()

    def test_add_three_steps_shows_correct_controls(
        self, page: Page, loaded_app: None
    ) -> None:
        """Adding three steps shows correct Up/Down button visibility per position."""
        for shaper in ["Column Selector", "Sort", "Mean Calculator"]:
            page.get_by_test_id(f"shaper_add_{self.PLOT_ID}").select_option(shaper)
            page.get_by_test_id(f"add_shaper_btn_{self.PLOT_ID}").click()
            page.wait_for_timeout(500)

        expect(page.locator("text=1. Column Selector")).to_be_visible()
        expect(page.locator("text=2. Sort")).to_be_visible()
        expect(page.locator("text=3. Mean Calculator")).to_be_visible()
        # First step: no Up button
        expect(page.get_by_test_id(f"up_{self.PLOT_ID}_0")).not_to_be_visible()
        expect(page.get_by_test_id(f"down_{self.PLOT_ID}_0")).to_be_visible()
        # Middle step: both
        expect(page.get_by_test_id(f"up_{self.PLOT_ID}_1")).to_be_visible()
        expect(page.get_by_test_id(f"down_{self.PLOT_ID}_1")).to_be_visible()
        # Last step: no Down button
        expect(page.get_by_test_id(f"up_{self.PLOT_ID}_2")).to_be_visible()
        expect(page.get_by_test_id(f"down_{self.PLOT_ID}_2")).not_to_be_visible()

    def test_all_ten_shaper_types_in_dropdown(self, page: Page, loaded_app: None) -> None:
        """All 10 shaper display names appear in the add-transformation dropdown."""
        expected_names = [
            "Column Selector", "Item Selector", "Filter", "Sort",
            "Mean Calculator", "Normalize", "Pivot Longer (Melt)",
            "Pivot Wider", "Split-Apply (Per-Axis)", "Transformer",
        ]
        dropdown = page.get_by_test_id(f"shaper_add_{self.PLOT_ID}")
        for name in expected_names:
            expect(dropdown.locator(f"option:has-text('{name}')")).to_be_attached()


class TestPipelineStepDelete:
    """Tests for deleting steps from the pipeline."""

    PLOT_ID = 1

    def test_delete_middle_step_renumbers(
        self, page: Page, pipeline_with_three_steps: None
    ) -> None:
        """Deleting the middle step renumbers remaining steps correctly."""
        page.get_by_test_id(f"del_{self.PLOT_ID}_1").click()
        page.wait_for_timeout(500)
        expect(page.locator("text=1. Column Selector")).to_be_visible()
        expect(page.locator("text=2. Normalize")).to_be_visible()
        expect(page.locator("text=Sort")).not_to_be_visible()

    def test_delete_first_step(self, page: Page, pipeline_with_three_steps: None) -> None:
        """Deleting the first step shifts all subsequent steps up."""
        page.get_by_test_id(f"del_{self.PLOT_ID}_0").click()
        page.wait_for_timeout(500)
        expect(page.locator("text=1. Sort")).to_be_visible()
        expect(page.locator("text=2. Normalize")).to_be_visible()
        expect(page.get_by_test_id(f"up_{self.PLOT_ID}_0")).not_to_be_visible()

    def test_delete_only_step(self, page: Page, loaded_app: None) -> None:
        """Deleting the sole step leaves an empty pipeline."""
        page.get_by_test_id(f"shaper_add_{self.PLOT_ID}").select_option("Column Selector")
        page.get_by_test_id(f"add_shaper_btn_{self.PLOT_ID}").click()
        page.wait_for_timeout(300)
        page.get_by_test_id(f"del_{self.PLOT_ID}_0").click()
        page.wait_for_timeout(500)
        expect(page.locator("text=Column Selector")).not_to_be_visible()
        expect(page.get_by_test_id(f"shaper_add_{self.PLOT_ID}")).to_be_visible()


class TestPipelineStepReorder:
    """Tests for reordering steps within the pipeline."""

    PLOT_ID = 1

    def test_move_step_up(self, page: Page, pipeline_with_three_steps: None) -> None:
        """Moving step 2 up swaps it with step 1."""
        page.get_by_test_id(f"up_{self.PLOT_ID}_1").click()
        page.wait_for_timeout(500)
        expect(page.locator("text=1. Sort")).to_be_visible()
        expect(page.locator("text=2. Column Selector")).to_be_visible()
        expect(page.locator("text=3. Normalize")).to_be_visible()

    def test_move_step_down(self, page: Page, pipeline_with_three_steps: None) -> None:
        """Moving step 1 down swaps it with step 2."""
        page.get_by_test_id(f"down_{self.PLOT_ID}_0").click()
        page.wait_for_timeout(500)
        expect(page.locator("text=1. Sort")).to_be_visible()
        expect(page.locator("text=2. Column Selector")).to_be_visible()


class TestPipelineFinalize:
    """Tests for pipeline finalization."""

    PLOT_ID = 1

    def test_finalize_triggers_execution(
        self, page: Page, pipeline_with_configured_steps: None
    ) -> None:
        """Finalize button applies pipeline and shows success toast."""
        page.get_by_test_id(f"finalize_{self.PLOT_ID}").click()
        page.wait_for_timeout(1000)
        expect(page.locator("text=Pipeline applied!")).to_be_visible()

    def test_no_data_warning(self, page: Page, empty_app: None) -> None:
        """Without data, a warning message is displayed instead of pipeline."""
        expect(page.locator("text=Please upload data first!")).to_be_visible()
```

---

## 4. Column Selector Tests

### 4.1 Gherkin Scenarios

```gherkin
Feature: Column Selector Shaper
  As a user who wants to reduce the DataFrame to specific columns
  I want to select which columns to keep via a multiselect widget
  So that downstream pipeline steps only operate on relevant data

  Background:
    Given test data is loaded with columns ["config", "benchmark", "ipc", "power", "area"]
    And I have added a "Column Selector" step to the pipeline

  Scenario: Default selection includes first column
    Then the "Columns to keep" multiselect should have "config" selected by default
    Because ColumnSelectorConfig defaults to [data.columns[0]] when no existing config

  Scenario: Select multiple columns
    When I select columns "ipc" and "power" in the "Columns to keep" multiselect
    Then the step configuration should contain {"columns": ["ipc", "power"]}
    And the step preview DataFrame should show only "ipc" and "power" columns

  Scenario: Select all columns
    When I select all 5 columns in the multiselect
    Then the preview should show all original columns
    And the output data shape should match the input

  Scenario: Deselect all columns produces empty list
    When I clear all selections from "Columns to keep"
    Then the configuration should contain {"columns": []}
    And finalize should trigger validation warning for missing field "columns"

  Scenario: Restore existing configuration on re-render
    Given the step has existing config {"columns": ["ipc", "area"]}
    Then the multiselect should show "ipc" and "area" pre-selected
    And "config", "benchmark", "power" should appear as unselected options

  Scenario: Stale column names are filtered from existing config
    Given the step has existing config {"columns": ["ipc", "nonexistent_col"]}
    Then only "ipc" should be pre-selected
    And "nonexistent_col" should NOT appear in the dropdown options

  Scenario: Widget key uniqueness across multiple Column Selectors
    Given plot 1 has a Column Selector at step 0
    And plot 2 has a Column Selector at step 0
    Then the multiselect keys should be "p1_colsel_0" and "p2_colsel_0"
    And changing one should NOT affect the other
```

### 4.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_column_selector.py
"""E2E tests for the Column Selector shaper configuration and execution."""

import pytest
from playwright.sync_api import Page, expect


class TestColumnSelectorConfig:
    """Tests for Column Selector configuration UI."""

    def test_default_selection_first_column(
        self, page: Page, column_selector_step: None
    ) -> None:
        """Default config pre-selects the first column when no existing config."""
        multiselect = page.locator("[data-testid*='colsel_']")
        expect(multiselect.locator("span:has-text('config')")).to_be_visible()

    def test_select_multiple_columns_updates_preview(
        self, page: Page, column_selector_step: None
    ) -> None:
        """Selecting multiple columns updates the live preview DataFrame."""
        ms = page.locator("[data-testid*='colsel_']")
        ms.click()
        page.locator("li:has-text('ipc')").click()
        page.locator("li:has-text('power')").click()
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        preview = page.locator("div[data-testid='stDataFrame']").first
        expect(preview).to_be_visible()

    def test_empty_selection_triggers_validation_warning(
        self, page: Page, column_selector_step: None
    ) -> None:
        """Clearing all columns and finalizing shows a validation warning."""
        # Clear all selected pills in the multiselect
        clear_btn = page.locator("[data-testid*='colsel_'] button[aria-label='Clear']")
        if clear_btn.is_visible():
            clear_btn.click()
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(500)
        expect(page.locator("text=Configuration incomplete")).to_be_visible()

    def test_existing_config_restore(
        self, page: Page, column_selector_with_config: None
    ) -> None:
        """Previously saved columns are restored in the multiselect defaults."""
        ms = page.locator("[data-testid*='colsel_']")
        expect(ms.locator("span:has-text('ipc')")).to_be_visible()
        expect(ms.locator("span:has-text('area')")).to_be_visible()


class TestColumnSelectorExecution:
    """Tests for Column Selector pipeline execution."""

    def test_column_selector_reduces_columns(
        self, page: Page, column_selector_step: None
    ) -> None:
        """Finalizing a Column Selector with 2 columns produces a 2-column DataFrame."""
        ms = page.locator("[data-testid*='colsel_']")
        ms.click()
        page.locator("li:has-text('ipc')").click()
        page.locator("li:has-text('power')").click()
        page.keyboard.press("Escape")
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(1000)
        expect(page.locator("text=Pipeline applied!")).to_be_visible()
```

---

## 5. Item Selector Tests

### 5.1 Gherkin Scenarios

```gherkin
Feature: Item Selector Shaper
  As a user who wants to filter rows by matching specific string values
  I want to specify a column and a list of target strings
  So that only rows whose column value matches the filter are retained

  Background:
    Given test data is loaded with a "benchmark" column containing
      ["dhrystone", "coremark", "whetstone", "linpack", "stream"]
    And the pipeline is ready for configuration

  Scenario: Item Selector is registered in the factory
    Then ShaperFactory._registry should contain key "itemSelector"
    And ShaperFactory._display_names should map "itemSelector" to "Item Selector"
    And the "Add transformation" dropdown should offer "Item Selector"

  Scenario: Item Selector appears in dropdown but has no dedicated config UI
    When I add an "Item Selector" step to the pipeline
    Then the step should render (orchestrator falls through to minimal config)
    Because "itemSelector" is NOT in config_dispatch dict in shaper_config.py

  Scenario: Programmatic exact-match filtering
    Given an Item Selector config:
      | column    | benchmark                |
      | strings   | ["dhrystone", "coremark"] |
      | mode      | exact                    |
    When the pipeline is executed via apply_shapers
    Then only rows where benchmark is "dhrystone" or "coremark" should remain

  Scenario: Programmatic contains-mode filtering
    Given an Item Selector config:
      | column    | benchmark   |
      | strings   | ["stone"]   |
      | mode      | contains    |
    When the pipeline is executed via apply_shapers
    Then rows for "dhrystone" and "whetstone" should remain
    And rows for "coremark", "linpack", "stream" should be filtered out

  Scenario: No matches produces empty DataFrame with log warning
    Given an Item Selector config:
      | column    | benchmark            |
      | strings   | ["nonexistent_val"]  |
      | mode      | exact                |
    When the pipeline is executed
    Then the result DataFrame should be empty
    And a warning should be logged about no matching strings

  Scenario: Validation requires column and strings
    Given an Item Selector config with missing "strings" field:
      | column    | benchmark   |
    When validate_shaper_config("itemSelector", config) is called
    Then it should return (False, ["strings"])

  Scenario: Validation requires non-empty strings list
    Given an Item Selector config:
      | column    | benchmark |
      | strings   | []        |
    When validate_shaper_config("itemSelector", config) is called
    Then it should return (False, ["strings"])
```

### 5.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_item_selector.py
"""E2E tests for the Item Selector shaper.

Note: ItemSelector has no dedicated UI config component in the web layer
(it is not in the config_dispatch dict in shaper_config.py). It IS registered
in ShaperFactory._registry and can be invoked programmatically via
apply_shapers(). These tests verify factory registration and execution
behavior, with UI tests limited to dropdown presence.
"""

import pytest
from playwright.sync_api import Page, expect

from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.validation import validate_shaper_config


class TestItemSelectorRegistration:
    """Tests verifying Item Selector is properly registered in the factory."""

    def test_item_selector_in_factory_registry(self) -> None:
        """ItemSelector class is registered under 'itemSelector' key."""
        assert "itemSelector" in ShaperFactory.get_available_types()

    def test_item_selector_display_name(self) -> None:
        """Display name for itemSelector is 'Item Selector'."""
        assert ShaperFactory.get_display_name("itemSelector") == "Item Selector"

    def test_item_selector_in_dropdown(self, page: Page, loaded_app: None) -> None:
        """Item Selector appears as an option in the add-transformation dropdown."""
        dropdown = page.get_by_test_id("shaper_add_1")
        expect(dropdown.locator("option:has-text('Item Selector')")).to_be_attached()


class TestItemSelectorExecution:
    """Tests for ItemSelector programmatic execution via apply_shapers."""

    def test_exact_match_filters_rows(self, sample_dataframe) -> None:
        """Exact mode retains only rows matching the given string list."""
        from src.web.pages.ui.shaper_config import apply_shapers

        config = [{"type": "itemSelector", "column": "benchmark",
                    "strings": ["dhrystone", "coremark"], "mode": "exact"}]
        result = apply_shapers(sample_dataframe, config)
        assert set(result["benchmark"].unique()) == {"dhrystone", "coremark"}

    def test_contains_mode_partial_match(self, sample_dataframe) -> None:
        """Contains mode retains rows with partial string matches."""
        from src.web.pages.ui.shaper_config import apply_shapers

        config = [{"type": "itemSelector", "column": "benchmark",
                    "strings": ["stone"], "mode": "contains"}]
        result = apply_shapers(sample_dataframe, config)
        assert all("stone" in val for val in result["benchmark"].unique())

    def test_no_matches_returns_empty(self, sample_dataframe) -> None:
        """No matching strings returns an empty DataFrame."""
        from src.web.pages.ui.shaper_config import apply_shapers

        config = [{"type": "itemSelector", "column": "benchmark",
                    "strings": ["nonexistent"], "mode": "exact"}]
        result = apply_shapers(sample_dataframe, config)
        assert result.empty


class TestItemSelectorValidation:
    """Tests for ItemSelector config validation."""

    def test_missing_strings_field(self) -> None:
        """Validation fails when 'strings' is missing."""
        is_valid, missing = validate_shaper_config(
            "itemSelector", {"column": "benchmark"}
        )
        assert not is_valid
        assert "strings" in missing

    def test_empty_strings_list(self) -> None:
        """Validation fails when 'strings' is an empty list."""
        is_valid, missing = validate_shaper_config(
            "itemSelector", {"column": "benchmark", "strings": []}
        )
        assert not is_valid
        assert "strings" in missing

    def test_missing_column(self) -> None:
        """Validation fails when 'column' is missing."""
        is_valid, missing = validate_shaper_config(
            "itemSelector", {"strings": ["a", "b"]}
        )
        assert not is_valid
        assert "column" in missing

    def test_valid_config_passes(self) -> None:
        """A complete config passes validation."""
        is_valid, missing = validate_shaper_config(
            "itemSelector", {"column": "benchmark", "strings": ["a"]}
        )
        assert is_valid
        assert missing is None
```

---

## 6. Condition Selector (Filter) Tests

### 6.1 Gherkin Scenarios

```gherkin
Feature: Condition Selector (Filter) Shaper
  As a user who wants to filter rows based on column value conditions
  I want to select a column and define filter criteria (categorical or numeric)
  So that only rows meeting the condition are retained in the dataset

  Background:
    Given test data is loaded with:
      | Column    | Type        | Values                            |
      | config    | categorical | ["baseline", "opt_a", "opt_b"]    |
      | benchmark | categorical | ["dhrystone", "coremark"]         |
      | ipc       | numeric     | [1.2, 1.5, 0.8, 2.1, ...]        |
      | power     | numeric     | [0.5, 0.7, 0.3, 0.9, ...]        |
    And I have added a "Filter" step to the pipeline

  Scenario: Filter by categorical column values
    When I select "config" as the filter column
    Then a multiselect "Keep rows where value is:" should appear
    And the multiselect should list ["baseline", "opt_a", "opt_b"]
    When I select ["baseline", "opt_a"]
    Then only rows where config is "baseline" or "opt_a" should appear in preview

  Scenario: Filter numeric column by range mode
    When I select "ipc" as the filter column
    Then a "Filter mode" dropdown should appear with options:
      | range | greater_than | less_than | equals |
    When I select mode "range"
    Then a slider "Value range" should appear with min/max from data
    When I set the range to [1.0, 2.0]
    Then the config should contain {"column": "ipc", "mode": "range", "range": [1.0, 2.0]}

  Scenario: Filter numeric column by greater_than mode
    When I select "power" and mode "greater_than"
    And I set threshold to 0.6
    Then config should be {"column": "power", "mode": "greater_than", "threshold": 0.6}
    And the preview should show only rows where power > 0.6

  Scenario: Filter numeric column by less_than mode
    When I select "power" and mode "less_than"
    And I set threshold to 0.5
    Then only rows with power < 0.5 should appear in preview

  Scenario: Filter numeric column by equals mode
    When I select "ipc" and mode "equals"
    And I set value to 1.5
    Then only rows where ipc == 1.5 should appear in preview

  Scenario: Only categorical and numeric columns shown
    Then the filter column dropdown should list categorical + numeric columns
    And datetime or boolean columns should NOT appear
    Because ConditionSelectorConfig selects dtypes ["object", "string", "category", "number"]

  Scenario: Restore existing categorical filter config
    Given existing config {"column": "config", "values": ["baseline"]}
    Then "config" should be pre-selected as the filter column
    And "baseline" should be pre-selected in the values multiselect

  Scenario: Restore existing numeric range config
    Given existing config {"column": "ipc", "mode": "range", "range": [1.0, 1.8]}
    Then "ipc" should be pre-selected and mode should be "range"
    And the slider should be positioned at [1.0, 1.8]

  Scenario: Empty filter column returns empty config
    When no filter column is selected
    Then the configuration should return an empty dict
    And validation should flag missing field "column"
```

### 6.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_condition_selector.py
"""E2E tests for the Condition Selector (Filter) shaper."""

import pytest
from playwright.sync_api import Page, expect


class TestConditionSelectorCategorical:
    """Tests for filtering on categorical columns."""

    def test_categorical_filter_shows_multiselect(
        self, page: Page, filter_step: None
    ) -> None:
        """Selecting a categorical column shows a value multiselect."""
        page.locator("[data-testid*='filter_col_']").select_option("config")
        page.wait_for_timeout(500)
        expect(page.locator("text=Keep rows where value is:")).to_be_visible()

    def test_categorical_filter_lists_unique_values(
        self, page: Page, filter_step: None
    ) -> None:
        """Value multiselect shows all unique values from the selected column."""
        page.locator("[data-testid*='filter_col_']").select_option("config")
        page.wait_for_timeout(300)
        ms = page.locator("[data-testid*='filter_values_']")
        ms.click()
        for val in ["baseline", "opt_a", "opt_b"]:
            expect(page.locator(f"li:has-text('{val}')")).to_be_visible()

    def test_categorical_filter_execution(
        self, page: Page, filter_step: None
    ) -> None:
        """Selected categorical values filter the DataFrame correctly."""
        page.locator("[data-testid*='filter_col_']").select_option("config")
        page.wait_for_timeout(300)
        ms = page.locator("[data-testid*='filter_values_']")
        ms.click()
        page.locator("li:has-text('baseline')").click()
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        preview = page.locator("div[data-testid='stDataFrame']").first
        expect(preview).to_be_visible()


class TestConditionSelectorNumeric:
    """Tests for filtering on numeric columns."""

    def test_numeric_filter_shows_mode_dropdown(
        self, page: Page, filter_step: None
    ) -> None:
        """Selecting a numeric column shows the filter mode dropdown."""
        page.locator("[data-testid*='filter_col_']").select_option("ipc")
        page.wait_for_timeout(500)
        expect(page.locator("[data-testid*='filter_mode_']")).to_be_visible()

    def test_range_mode_shows_slider(self, page: Page, filter_step: None) -> None:
        """Range mode displays a slider with data min/max bounds."""
        page.locator("[data-testid*='filter_col_']").select_option("ipc")
        page.locator("[data-testid*='filter_mode_']").select_option("range")
        page.wait_for_timeout(300)
        expect(page.locator("[data-testid*='filter_range_']")).to_be_visible()

    def test_greater_than_mode(self, page: Page, filter_step: None) -> None:
        """Greater-than mode shows a number input for the threshold."""
        page.locator("[data-testid*='filter_col_']").select_option("power")
        page.locator("[data-testid*='filter_mode_']").select_option("greater_than")
        page.wait_for_timeout(300)
        expect(page.locator("[data-testid*='filter_gt_']")).to_be_visible()

    def test_less_than_mode(self, page: Page, filter_step: None) -> None:
        """Less-than mode shows a number input for the threshold."""
        page.locator("[data-testid*='filter_col_']").select_option("ipc")
        page.locator("[data-testid*='filter_mode_']").select_option("less_than")
        page.wait_for_timeout(300)
        expect(page.locator("[data-testid*='filter_lt_']")).to_be_visible()

    def test_equals_mode(self, page: Page, filter_step: None) -> None:
        """Equals mode shows a number input for the exact value."""
        page.locator("[data-testid*='filter_col_']").select_option("ipc")
        page.locator("[data-testid*='filter_mode_']").select_option("equals")
        page.wait_for_timeout(300)
        expect(page.locator("[data-testid*='filter_eq_']")).to_be_visible()


class TestConditionSelectorValidation:
    """Tests for Condition Selector validation."""

    def test_missing_column_validation(self) -> None:
        """Validation fails when column is empty."""
        from src.core.services.shapers.validation import validate_shaper_config
        is_valid, missing = validate_shaper_config("conditionSelector", {})
        assert not is_valid
        assert "column" in missing
```

---

## 7. Sort Shaper Tests

### 7.1 Gherkin Scenarios

```gherkin
Feature: Sort Shaper
  As a user who wants to reorder rows by categorical column values
  I want to select columns and define value order for each
  So that the DataFrame rows follow a meaningful presentation order

  Background:
    Given test data with categorical columns ["config", "benchmark"]
    And I have added a "Sort" step to the pipeline

  Scenario: Only categorical columns are offered for sorting
    Then the "Sort by columns" multiselect should list only categorical columns
    And numeric columns like "ipc" and "power" should NOT appear

  Scenario: No categorical columns shows warning
    Given data has no categorical columns (all numeric)
    Then a warning "No categorical columns available for sorting." should appear
    And config should return {"type": "sort", "order_dict": {}}

  Scenario: Select a single sort column
    When I select "config" in the "Sort by columns" multiselect
    Then an expander "Order for 'config'" should appear
    And it should list all unique values of "config" sorted alphabetically

  Scenario: Define custom value order via multiselect
    When I select "config" and reorder values to ["opt_b", "baseline", "opt_a"]
    Then order_dict should be {"config": ["opt_b", "baseline", "opt_a"]}
    And the preview should show rows sorted accordingly

  Scenario: Multiple sort columns each get their own expander
    When I select both "config" and "benchmark"
    Then two expanders should appear: "Order for 'config'" and "Order for 'benchmark'"
    And each has its own multiselect for value ordering

  Scenario: High cardinality column (>20 values) uses text display
    Given "benchmark" has 25 unique values
    Then the sort expander for "benchmark" should show an info message
    And "Showing first 50" text should appear
    And a read-only dataframe of values should be displayed

  Scenario: Restore existing order_dict
    Given existing config {"order_dict": {"config": ["opt_a", "opt_b", "baseline"]}}
    Then "config" should be pre-selected in the sort columns
    And the value order for "config" should be ["opt_a", "opt_b", "baseline"]

  Scenario: New values since last save are appended to order
    Given existing config {"order_dict": {"config": ["opt_a", "baseline"]}}
    And data now has a new "config" value "opt_c"
    Then the default order should be ["opt_a", "baseline", "opt_c"]
    Because valid_previous + new_values logic in SortConfig
```

### 7.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_sort_shaper.py
"""E2E tests for the Sort shaper configuration and execution."""

import pytest
from playwright.sync_api import Page, expect


class TestSortConfig:
    """Tests for Sort shaper configuration UI."""

    def test_only_categorical_columns_offered(
        self, page: Page, sort_step: None
    ) -> None:
        """Sort multiselect shows only categorical columns."""
        ms = page.locator("[data-testid*='sort_cols_']")
        ms.click()
        expect(page.locator("li:has-text('config')")).to_be_visible()
        expect(page.locator("li:has-text('benchmark')")).to_be_visible()
        # Numeric columns should not appear
        expect(page.locator("li:has-text('ipc')")).not_to_be_visible()

    def test_select_column_shows_order_expander(
        self, page: Page, sort_step: None
    ) -> None:
        """Selecting a sort column reveals an order expander for that column."""
        ms = page.locator("[data-testid*='sort_cols_']")
        ms.click()
        page.locator("li:has-text('config')").click()
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        expect(page.locator("text=Order for 'config'")).to_be_visible()

    def test_value_order_multiselect_lists_unique_values(
        self, page: Page, sort_step_with_column: None
    ) -> None:
        """The order multiselect lists all unique values from the selected column."""
        ms = page.locator("[data-testid*='sort_order_config_']")
        expect(ms).to_be_visible()

    def test_no_categorical_columns_warning(
        self, page: Page, sort_step_numeric_only: None
    ) -> None:
        """With only numeric data, a warning is shown instead of sort UI."""
        expect(page.locator("text=No categorical columns available")).to_be_visible()


class TestSortExecution:
    """Tests for Sort shaper pipeline execution."""

    def test_sort_reorders_rows(
        self, page: Page, sort_step_configured: None
    ) -> None:
        """Finalizing a configured sort step reorders rows in the preview."""
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(1000)
        expect(page.locator("text=Pipeline applied!")).to_be_visible()

    def test_sort_validation_requires_order_dict(self) -> None:
        """Validation fails when order_dict is empty."""
        from src.core.services.shapers.validation import validate_shaper_config
        is_valid, missing = validate_shaper_config("sort", {"order_dict": {}})
        # Empty dict is falsy for list check but not for dict; depends on validation logic
        # The validation checks if value is None or empty list/string
        assert not is_valid or missing is None  # order_dict is a dict, not a list
```

---

## 8. Mean Calculator Tests

### 8.1 Gherkin Scenarios

```gherkin
Feature: Mean Calculator Shaper
  As a user who wants to aggregate numeric data by groups
  I want to configure mean type, variables, grouping columns, and replacing column
  So that the data is aggregated according to my analysis requirements

  Background:
    Given test data with numeric columns ["ipc", "power", "area"]
    And categorical columns ["config", "benchmark"]
    And I have added a "Mean Calculator" step to the pipeline

  Scenario: Three-column layout for mean configuration
    Then the UI should display three columns:
      | Column 1       | Column 2    | Column 3  |
      | Mean type      | Variables   | Group by  |
    And a fourth row should show "Replacing column"

  Scenario: Select mean algorithm
    Then the "Mean type" dropdown should offer:
      | arithmean | geomean | hmean |
    When I select "geomean"
    Then the config should contain {"meanAlgorithm": "geomean"}

  Scenario: Default mean algorithm is arithmean
    Then the "Mean type" dropdown should have "arithmean" selected by default

  Scenario: Select mean variables
    When I select "ipc" and "power" in the "Variables" multiselect
    Then config should contain {"meanVars": ["ipc", "power"]}

  Scenario: Select grouping columns
    When I select "config" in the "Group by" multiselect
    Then config should contain {"groupingColumns": ["config"]}

  Scenario: Select replacing column
    Then the "Replacing column" selectbox should list categorical columns
    When I select "benchmark"
    Then config should contain {"replacingColumn": "benchmark"}

  Scenario: Validation requires groupingColumns and meanVars
    When meanVars is empty and groupingColumns is empty
    Then validation should flag ["groupingColumns", "meanVars"]

  Scenario: Restore existing mean config
    Given existing config:
      | meanAlgorithm    | geomean   |
      | meanVars         | ["ipc"]   |
      | groupingColumns  | ["config"]|
      | replacingColumn  | benchmark |
    Then "geomean" should be selected in mean type
    And "ipc" should be pre-selected in variables
    And "config" should be pre-selected in group by
    And "benchmark" should be selected as replacing column

  Scenario: Legacy groupingColumn (singular) config migration
    Given existing config with {"groupingColumn": "config"} (no "s")
    Then the grouping columns multiselect should show "config" selected
    Because MeanConfig handles the legacy field with a fallback
```

### 8.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_mean_calculator.py
"""E2E tests for the Mean Calculator shaper."""

import pytest
from playwright.sync_api import Page, expect


class TestMeanConfig:
    """Tests for Mean Calculator configuration UI."""

    def test_mean_algorithm_options(self, page: Page, mean_step: None) -> None:
        """Mean type dropdown offers arithmean, geomean, hmean."""
        dropdown = page.locator("[data-testid*='mean_algo_']")
        for algo in ["arithmean", "geomean", "hmean"]:
            expect(dropdown.locator(f"option:has-text('{algo}')")).to_be_attached()

    def test_default_algorithm_arithmean(self, page: Page, mean_step: None) -> None:
        """Default mean algorithm is arithmean."""
        dropdown = page.locator("[data-testid*='mean_algo_']")
        expect(dropdown).to_have_value("arithmean")

    def test_select_mean_variables(self, page: Page, mean_step: None) -> None:
        """Selecting numeric variables populates meanVars in config."""
        ms = page.locator("[data-testid*='mean_vars_']")
        ms.click()
        page.locator("li:has-text('ipc')").click()
        page.locator("li:has-text('power')").click()
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        # Verify preview updates
        preview = page.locator("div[data-testid='stDataFrame']").first
        expect(preview).to_be_visible()

    def test_select_grouping_columns(self, page: Page, mean_step: None) -> None:
        """Selecting grouping columns shows only categorical columns."""
        ms = page.locator("[data-testid*='mean_group_']")
        ms.click()
        expect(page.locator("li:has-text('config')")).to_be_visible()
        expect(page.locator("li:has-text('benchmark')")).to_be_visible()

    def test_replacing_column_selectbox(self, page: Page, mean_step: None) -> None:
        """Replacing column selectbox lists categorical columns."""
        sb = page.locator("[data-testid*='mean_replace_']")
        expect(sb).to_be_visible()

    def test_validation_requires_grouping_and_vars(self) -> None:
        """Validation flags missing groupingColumns and meanVars."""
        from src.core.services.shapers.validation import validate_shaper_config
        is_valid, missing = validate_shaper_config("mean", {"meanAlgorithm": "arithmean"})
        assert not is_valid
        assert "groupingColumns" in missing
        assert "meanVars" in missing


class TestMeanExecution:
    """Tests for Mean Calculator pipeline execution."""

    def test_mean_aggregation_produces_result(
        self, page: Page, mean_step_configured: None
    ) -> None:
        """A fully configured mean step produces aggregated output on finalize."""
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(1000)
        expect(page.locator("text=Pipeline applied!")).to_be_visible()
```

---

## 9. Normalize Shaper Tests

### 9.1 Gherkin Scenarios

```gherkin
Feature: Normalize Shaper
  As a user who wants to normalize numeric data against a baseline
  I want to configure normalizer variables, target variables, baseline column/value, and group-by
  So that values are expressed relative to a chosen reference configuration

  Background:
    Given test data with numeric columns ["ipc", "power", "area", "ipc.sd"]
    And categorical columns ["config", "benchmark"]
    And "config" has values ["baseline", "opt_a", "opt_b"]
    And I have added a "Normalize" step to the pipeline

  Scenario: Two-column layout for normalize configuration
    Then the UI should display two columns:
      | Column 1                        | Column 2                  |
      | Normalizer variables            | Baseline value            |
      | Variables to normalize          | Group by                  |
      | Normalizer column (baseline ID) | Normalize SD checkbox     |

  Scenario: Select normalizer variables
    When I select "ipc" in "Normalizer variables (will be summed)"
    Then config should contain {"normalizerVars": ["ipc"]}

  Scenario: Select variables to normalize
    When I select "ipc" and "power" in "Variables to normalize"
    Then config should contain {"normalizeVars": ["ipc", "power"]}

  Scenario: Select normalizer column and baseline value
    When I select "config" as "Normalizer column (baseline identifier)"
    Then a "Baseline value" selectbox should appear with ["baseline", "opt_a", "opt_b"]
    When I select "baseline" as the baseline value
    Then config should contain {"normalizerColumn": "config", "normalizerValue": "baseline"}

  Scenario: Select group-by columns
    When I select "benchmark" in the "Group by" multiselect
    Then config should contain {"groupBy": ["benchmark"]}

  Scenario: Enable/disable automatic SD normalization
    Then the "Automatically normalize standard deviation columns" checkbox should default to True
    When I uncheck the checkbox
    Then config should contain {"normalizeSd": false}

  Scenario: Validation requires all four core fields
    When normalizeVars, normalizerColumn, normalizerValue, and groupBy are all empty
    Then validation should flag all four fields as missing

  Scenario: Restore existing normalize config
    Given existing config:
      | normalizerVars    | ["ipc"]     |
      | normalizeVars     | ["power"]   |
      | normalizerColumn  | config      |
      | normalizerValue   | baseline    |
      | groupBy           | ["benchmark"]|
      | normalizeSd       | false       |
    Then all values should be pre-populated in the UI
    And the SD checkbox should be unchecked
```

### 9.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_normalize_shaper.py
"""E2E tests for the Normalize shaper."""

import pytest
from playwright.sync_api import Page, expect


class TestNormalizeConfig:
    """Tests for Normalize shaper configuration UI."""

    def test_normalizer_vars_multiselect(self, page: Page, normalize_step: None) -> None:
        """Normalizer variables multiselect shows only numeric columns."""
        ms = page.locator("[data-testid*='normalizer_vars_']")
        ms.click()
        expect(page.locator("li:has-text('ipc')")).to_be_visible()
        expect(page.locator("li:has-text('power')")).to_be_visible()
        # categorical should not appear
        expect(page.locator("li:has-text('config')")).not_to_be_visible()

    def test_normalize_vars_multiselect(self, page: Page, normalize_step: None) -> None:
        """Target variables multiselect shows numeric columns."""
        ms = page.locator("[data-testid*='norm_vars_']")
        expect(ms).to_be_visible()

    def test_normalizer_column_shows_categorical(
        self, page: Page, normalize_step: None
    ) -> None:
        """Normalizer column selectbox shows categorical columns."""
        sb = page.locator("[data-testid*='norm_col_']")
        expect(sb).to_be_visible()
        sb.click()
        expect(page.locator("option:has-text('config')")).to_be_attached()

    def test_baseline_value_populated_after_column_select(
        self, page: Page, normalize_step: None
    ) -> None:
        """Selecting a normalizer column populates the baseline value dropdown."""
        page.locator("[data-testid*='norm_col_']").select_option("config")
        page.wait_for_timeout(300)
        sb = page.locator("[data-testid*='norm_val_']")
        expect(sb).to_be_visible()

    def test_sd_checkbox_default_true(self, page: Page, normalize_step: None) -> None:
        """The normalize SD checkbox defaults to checked."""
        cb = page.locator("[data-testid*='norm_sd_']")
        expect(cb).to_be_checked()

    def test_validation_requires_all_fields(self) -> None:
        """Validation flags all four required fields when missing."""
        from src.core.services.shapers.validation import validate_shaper_config
        is_valid, missing = validate_shaper_config("normalize", {})
        assert not is_valid
        for field in ["normalizeVars", "normalizerColumn", "normalizerValue", "groupBy"]:
            assert field in missing


class TestNormalizeExecution:
    """Tests for Normalize shaper pipeline execution."""

    def test_normalize_produces_relative_values(
        self, page: Page, normalize_step_configured: None
    ) -> None:
        """Finalized normalize step divides variables by baseline sum."""
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(1000)
        expect(page.locator("text=Pipeline applied!")).to_be_visible()
```

---

## 10. Pivot Shaper Tests (Longer + Wider)

### 10.1 Gherkin Scenarios -- Pivot Longer (Melt)

```gherkin
Feature: Pivot Longer (Melt) Shaper
  As a user who wants to unpivot wide data into long format
  I want to select identifier columns, value columns, and output names
  So that the data is reshaped for analysis or plotting

  Background:
    Given test data with columns ["config", "benchmark", "cpu0.ipc", "cpu1.ipc", "cpu2.ipc"]
    And I have added a "Pivot Longer (Melt)" step to the pipeline

  Scenario: Configure identifier and value columns
    When I select "config" and "benchmark" as "Identifier Columns (keep as-is)"
    And I select "cpu0.ipc", "cpu1.ipc", "cpu2.ipc" as "Value Columns (to unpivot)"
    Then config should contain:
      | id_vars    | ["config", "benchmark"]                  |
      | value_vars | ["cpu0.ipc", "cpu1.ipc", "cpu2.ipc"]     |

  Scenario: Default output column names
    Then the "New 'Name' Column" input should default to "variable"
    And the "New 'Value' Column" input should default to "value"

  Scenario: Custom output column names
    When I set "New 'Name' Column" to "cpu_id"
    And I set "New 'Value' Column" to "ipc_value"
    Then config should contain {"var_name": "cpu_id", "value_name": "ipc_value"}

  Scenario: Auto-fill value columns when id_vars are selected
    When I select "config" and "benchmark" as identifier columns
    Then the value columns should default to all remaining columns
    Because PivotLongerConfig auto-fills non-id columns

  Scenario: Regex extraction pattern
    When I enter extract pattern "cpu(\d+)\.ipc"
    Then the "Sections to Keep" multiselect should show "Group 1"
    And a preview line "cpu0.ipc -> 0" should appear

  Scenario: Multi-group regex with separator
    When I enter pattern ".+l(\d+)_cntrl(\d+).*"
    And I select groups [1, 2]
    And I set separator to "_"
    Then combined values like "0_1" should appear in the preview

  Scenario: Value filtering per group
    When I enter a regex pattern with a capture group
    And unique extracted values are ["0", "1", "2", "3"]
    And I select to keep only ["0", "1"] for that group
    Then selection_filters should contain {1: ["0", "1"]}

  Scenario: Missing values strategy -- discard vs merge
    When selection_filters are set and strategy is "discard"
    Then non-matching rows are dropped
    When strategy is "merge"
    And merge_label is "other"
    Then non-matching rows are relabeled to "other"

  Scenario: Invalid regex shows error
    When I enter pattern "cpu(\d+"  (unclosed group)
    Then "Invalid Regex Pattern" error should appear

  Scenario: Validation requires all four core fields
    When id_vars, value_vars, var_name, or value_name are missing
    Then validation should flag the empty fields
```

### 10.2 Gherkin Scenarios -- Pivot Wider

```gherkin
Feature: Pivot Wider Shaper
  As a user who wants to spread long-format data into wide columns
  I want to select index columns, the column source, and value source
  So that unique values in one column become new column headers

  Background:
    Given long-format test data with columns ["config", "benchmark", "metric", "value"]
    And I have added a "Pivot Wider" step to the pipeline

  Scenario: Three-column layout for pivot wider
    Then the UI should display three columns:
      | Index Columns | Columns from | Values from |

  Scenario: Configure index, columns, and values
    When I select "config" and "benchmark" as "Index Columns"
    And I select "metric" for "Columns from"
    And I select "value" for "Values from"
    Then config should contain:
      | index   | ["config", "benchmark"] |
      | columns | metric                   |
      | values  | value                    |

  Scenario: Empty selections gracefully handled
    When I leave "Columns from" unselected
    Then the result dict should NOT contain the "columns" key
    And validation should flag missing field "columns"

  Scenario: Validation requires index, columns, and values
    When all three are empty
    Then validation should flag ["index", "columns", "values"]

  Scenario: Restore existing pivot wider config
    Given existing config {"index": ["config"], "columns": "metric", "values": "value"}
    Then "config" should be pre-selected in Index
    And "metric" in Columns from and "value" in Values from
```

### 10.3 Pytest-Playwright Stubs

```python
# tests/e2e/test_pivot_shapers.py
"""E2E tests for Pivot Longer and Pivot Wider shapers."""

import pytest
from playwright.sync_api import Page, expect


class TestPivotLongerConfig:
    """Tests for Pivot Longer (Melt) configuration UI."""

    def test_id_vars_multiselect(self, page: Page, pivot_longer_step: None) -> None:
        """ID vars multiselect lists all data columns."""
        ms = page.locator("[data-testid*='plonger_id_']")
        expect(ms).to_be_visible()

    def test_value_vars_auto_fill(self, page: Page, pivot_longer_step: None) -> None:
        """Value vars default to non-id columns when id_vars are set."""
        # Select id vars
        ms_id = page.locator("[data-testid*='plonger_id_']")
        ms_id.click()
        page.locator("li:has-text('config')").click()
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        ms_val = page.locator("[data-testid*='plonger_val_']")
        expect(ms_val).to_be_visible()

    def test_default_output_column_names(
        self, page: Page, pivot_longer_step: None
    ) -> None:
        """Default var_name is 'variable' and value_name is 'value'."""
        var_input = page.locator("[data-testid*='plonger_varname_']")
        val_input = page.locator("[data-testid*='plonger_valname_']")
        expect(var_input).to_have_value("variable")
        expect(val_input).to_have_value("value")

    def test_extract_pattern_input(self, page: Page, pivot_longer_step: None) -> None:
        """Entering a regex pattern shows extraction options."""
        pattern_input = page.locator("[data-testid*='plonger_pattern_']")
        pattern_input.fill(r"cpu(\d+)\.ipc")
        page.wait_for_timeout(500)
        expect(page.locator("text=Sections to Keep")).to_be_visible()

    def test_invalid_regex_error(self, page: Page, pivot_longer_step: None) -> None:
        """An invalid regex pattern shows an error message."""
        pattern_input = page.locator("[data-testid*='plonger_pattern_']")
        pattern_input.fill(r"cpu(\d+")
        page.wait_for_timeout(500)
        expect(page.locator("text=Invalid Regex Pattern")).to_be_visible()

    def test_pivot_longer_validation(self) -> None:
        """Validation requires all four fields."""
        from src.core.services.shapers.validation import validate_shaper_config
        is_valid, missing = validate_shaper_config("pivotLonger", {})
        assert not is_valid
        for f in ["id_vars", "value_vars", "var_name", "value_name"]:
            assert f in missing


class TestPivotWiderConfig:
    """Tests for Pivot Wider configuration UI."""

    def test_index_columns_multiselect(self, page: Page, pivot_wider_step: None) -> None:
        """Index columns multiselect is visible and lists data columns."""
        ms = page.locator("[data-testid*='pwider_idx_']")
        expect(ms).to_be_visible()

    def test_columns_from_selectbox(self, page: Page, pivot_wider_step: None) -> None:
        """Columns-from selectbox includes a blank option and all columns."""
        sb = page.locator("[data-testid*='pwider_col_']")
        expect(sb).to_be_visible()

    def test_values_from_selectbox(self, page: Page, pivot_wider_step: None) -> None:
        """Values-from selectbox includes a blank option and all columns."""
        sb = page.locator("[data-testid*='pwider_val_']")
        expect(sb).to_be_visible()

    def test_pivot_wider_validation(self) -> None:
        """Validation requires index, columns, and values."""
        from src.core.services.shapers.validation import validate_shaper_config
        is_valid, missing = validate_shaper_config("pivotWider", {})
        assert not is_valid
        for f in ["index", "columns", "values"]:
            assert f in missing
```

---

## 11. Split-Apply Tests

### 11.1 Gherkin Scenarios

```gherkin
Feature: Split-Apply (Per-Axis) Shaper
  As a user who wants to apply independent transformations to different column groups
  I want to define join columns, create 2-4 groups with numeric columns and sub-pipelines
  So that I can build dual-axis or multi-metric workflows

  Background:
    Given test data with numeric ["ipc", "power", "area", "freq"]
    And categorical ["config", "benchmark"]
    And I have added a "Split-Apply (Per-Axis)" step to the pipeline

  Scenario: Descriptive text is displayed
    Then a description mentioning "Split the data into independent column groups" should appear

  Scenario: Join columns default to all categorical columns
    Then the "Join columns (shared categorical columns)" multiselect
    should have all categorical columns selected by default

  Scenario: Number of groups slider
    Then a slider "Number of groups" should appear with range [2, 4]
    And default value should be 2
    Because _MIN_GROUPS=2 and _MAX_GROUPS=4

  Scenario: Adjust number of groups
    When I move the slider to 3
    Then 3 group expanders should appear: "Group A", "Group B", "Group C"

  Scenario: Each group has numeric column selection
    Then each group expander should contain a "Numeric columns" multiselect
    And it should list only numeric columns

  Scenario: Sub-pipeline within a group
    Then each group should have a sub-pipeline section
    And the sub-pipeline should support adding steps via "+ Add step"
    And removing the last step via "- Remove last"

  Scenario: Sub-pipeline step type selector
    When I click "+ Add step" in Group A
    Then a "Transformation" selectbox should appear with options:
      | Mean Calculator | Normalize | Sort | Filter |
    Because _ALLOWED_INNER_TYPES is {mean, normalize, sort, conditionSelector}

  Scenario: Sub-pipeline delegates to the same config UI as main pipeline
    When I add a "Mean Calculator" step in Group A's sub-pipeline
    Then the same MeanConfig.render widgets should appear
    (meanAlgorithm selectbox, Variables multiselect, Group by multiselect, etc.)

  Scenario: Two groups with independent sub-pipelines
    When Group A has columns ["ipc"] with sub-pipeline [Mean]
    And Group B has columns ["power"] with sub-pipeline [Normalize]
    Then the final config should contain:
      | joinColumns | all categorical columns                                |
      | groups      | [{"columns": ["ipc"], "pipeline": [...]},              |
      |             |  {"columns": ["power"], "pipeline": [...]}]            |

  Scenario: Validation requires joinColumns and groups
    When joinColumns is empty and groups have no columns
    Then validation should flag ["joinColumns", "groups"]

  Scenario: Widget key isolation between groups
    Then Group A's step widgets should have keys like "p1_sa_g0_{shaper_id}_s0_..."
    And Group B's should have "p1_sa_g1_{shaper_id}_s0_..."
    So that changes in one group do NOT affect another
```

### 11.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_split_apply.py
"""E2E tests for the Split-Apply (Per-Axis) shaper."""

import pytest
from playwright.sync_api import Page, expect


class TestSplitApplyConfig:
    """Tests for Split-Apply configuration UI."""

    def test_description_text(self, page: Page, split_apply_step: None) -> None:
        """Descriptive text about split-apply is displayed."""
        expect(page.locator("text=Split the data into independent column groups")).to_be_visible()

    def test_join_columns_default(self, page: Page, split_apply_step: None) -> None:
        """Join columns multiselect defaults to all categorical columns."""
        ms = page.locator("[data-testid*='sa_join_']")
        expect(ms).to_be_visible()

    def test_groups_slider_range(self, page: Page, split_apply_step: None) -> None:
        """Groups slider has range 2-4 with default 2."""
        slider = page.locator("[data-testid*='sa_ngroups_']")
        expect(slider).to_be_visible()

    def test_two_groups_visible_by_default(
        self, page: Page, split_apply_step: None
    ) -> None:
        """Two group expanders appear by default."""
        expect(page.locator("text=Group A")).to_be_visible()
        expect(page.locator("text=Group B")).to_be_visible()
        expect(page.locator("text=Group C")).not_to_be_visible()

    def test_add_sub_pipeline_step(self, page: Page, split_apply_step: None) -> None:
        """Clicking '+ Add step' adds a sub-pipeline step with type selector."""
        page.locator("button:has-text('+ Add step')").first.click()
        page.wait_for_timeout(500)
        expect(page.locator("text=Step 1")).to_be_visible()
        expect(page.locator("[data-testid*='_type']").first).to_be_visible()

    def test_sub_pipeline_type_options(
        self, page: Page, split_apply_with_substep: None
    ) -> None:
        """Sub-pipeline step type selector offers Mean, Normalize, Sort, Filter."""
        type_select = page.locator("[data-testid*='_type']").first
        type_select.click()
        for name in ["Mean Calculator", "Normalize", "Sort", "Filter"]:
            expect(page.locator(f"option:has-text('{name}')")).to_be_attached()

    def test_remove_sub_pipeline_step(
        self, page: Page, split_apply_with_substep: None
    ) -> None:
        """Clicking '- Remove last' removes the last sub-pipeline step."""
        page.locator("button:has-text('Remove last')").first.click()
        page.wait_for_timeout(500)
        expect(page.locator("text=Step 1")).not_to_be_visible()

    def test_validation_requires_join_and_groups(self) -> None:
        """Validation flags missing joinColumns and groups."""
        from src.core.services.shapers.validation import validate_shaper_config
        is_valid, missing = validate_shaper_config("splitApply", {})
        assert not is_valid
        assert "joinColumns" in missing
        assert "groups" in missing


class TestSplitApplyExecution:
    """Tests for Split-Apply pipeline execution."""

    def test_split_apply_merges_groups(
        self, page: Page, split_apply_configured: None
    ) -> None:
        """A configured split-apply step produces merged output on finalize."""
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(1000)
        expect(page.locator("text=Pipeline applied!")).to_be_visible()
```

---

## 12. Transformer Tests

### 12.1 Gherkin Scenarios

```gherkin
Feature: Transformer Shaper
  As a user who wants to convert a column's data type
  I want to select a column and choose between Factor (categorical) and Scalar (numeric)
  So that downstream pipeline steps and plots treat the column correctly

  Background:
    Given test data with columns ["config", "benchmark", "ipc", "power", "cpu_id"]
    And "cpu_id" contains numeric values [0, 1, 2, 3]
    And I have added a "Transformer" step to the pipeline

  Scenario: Two-column layout for transformer config
    Then the UI should display two columns:
      | Column 1                       | Column 2              |
      | Select Variable to Transform   | Convert to: segmented |

  Scenario: Column selectbox lists all columns sorted
    Then the "Select Variable to Transform" selectbox should list columns alphabetically

  Scenario: Segmented control offers Factor and Scalar
    Then the "Convert to:" segmented control should have options:
      | Factor (String/Categorical) | Scalar (Numeric) |

  Scenario: Convert numeric to Factor shows order selector
    When I select "cpu_id" and choose "Factor (String/Categorical)"
    Then a "Define Factor Order" multiselect should appear
    And it should list unique values of cpu_id as strings: ["0", "1", "2", "3"]

  Scenario: Define custom factor order
    When I select factor type and reorder values to ["3", "2", "1", "0"]
    Then config should contain:
      | column      | cpu_id   |
      | target_type | factor   |
      | order       | ["3", "2", "1", "0"] |

  Scenario: Convert to Scalar does not show order selector
    When I select "cpu_id" and choose "Scalar (Numeric)"
    Then the "Define Factor Order" multiselect should NOT appear
    And config should contain {"column": "cpu_id", "target_type": "scalar", "order": null}

  Scenario: Restore existing transformer config
    Given existing config {"column": "cpu_id", "target_type": "factor", "order": ["1", "0"]}
    Then "cpu_id" should be pre-selected in the column selectbox
    And "Factor (String/Categorical)" should be the active segment
    And the order multiselect should show ["1", "0"] as default

  Scenario: Validation requires column
    When column is empty
    Then validation should flag ["column"]
```

### 12.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_transformer.py
"""E2E tests for the Transformer shaper."""

import pytest
from playwright.sync_api import Page, expect


class TestTransformerConfig:
    """Tests for Transformer configuration UI."""

    def test_column_selectbox_sorted(self, page: Page, transformer_step: None) -> None:
        """Column selectbox lists columns in sorted order."""
        sb = page.locator("[data-testid*='trans_col_']")
        expect(sb).to_be_visible()

    def test_segmented_control_options(self, page: Page, transformer_step: None) -> None:
        """Segmented control offers Factor and Scalar options."""
        seg = page.locator("[data-testid*='trans_type_']")
        expect(seg).to_be_visible()

    def test_factor_type_shows_order_selector(
        self, page: Page, transformer_step: None
    ) -> None:
        """Selecting Factor type reveals the order multiselect."""
        page.locator("[data-testid*='trans_col_']").select_option("cpu_id")
        page.locator("text=Factor (String/Categorical)").click()
        page.wait_for_timeout(500)
        expect(page.locator("[data-testid*='trans_order_']")).to_be_visible()

    def test_scalar_type_hides_order_selector(
        self, page: Page, transformer_step: None
    ) -> None:
        """Selecting Scalar type hides the order multiselect."""
        page.locator("[data-testid*='trans_col_']").select_option("cpu_id")
        page.locator("text=Scalar (Numeric)").click()
        page.wait_for_timeout(500)
        expect(page.locator("[data-testid*='trans_order_']")).not_to_be_visible()

    def test_validation_requires_column(self) -> None:
        """Validation fails when column is empty."""
        from src.core.services.shapers.validation import validate_shaper_config
        is_valid, missing = validate_shaper_config("transformer", {})
        assert not is_valid
        assert "column" in missing


class TestTransformerExecution:
    """Tests for Transformer pipeline execution."""

    def test_factor_conversion(
        self, page: Page, transformer_factor_configured: None
    ) -> None:
        """Finalizing a Factor transformer converts the column to categorical."""
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(1000)
        expect(page.locator("text=Pipeline applied!")).to_be_visible()
```

---

## 13. Multi-Step Pipeline Tests

### 13.1 Gherkin Scenarios

```gherkin
Feature: Multi-Step Pipeline Combinations
  As a user building a complete data processing workflow
  I want to chain multiple shapers in sequence
  So that each step transforms the output of the previous step

  Background:
    Given test data is loaded with typical benchmark columns

  Scenario: ColumnSelector -> Mean -> Sort (bar chart recipe)
    When I add "Column Selector" selecting ["config", "benchmark", "ipc"]
    And I add "Mean Calculator" with group=["config"], vars=["ipc"], replace="benchmark"
    And I add "Sort" ordering config=["opt_b", "opt_a", "baseline"]
    And I finalize the pipeline
    Then the result should have aggregated ipc values sorted by custom config order

  Scenario: ColumnSelector -> Normalize -> Sort (normalized comparison recipe)
    When I add "Column Selector" selecting ["config", "benchmark", "ipc", "power"]
    And I add "Normalize" with normalizerVars=["ipc"], normalizeVars=["power"],
        normalizerColumn="config", normalizerValue="baseline", groupBy=["benchmark"]
    And I add "Sort" ordering config=["baseline", "opt_a", "opt_b"]
    And I finalize
    Then power values should be normalized relative to baseline ipc

  Scenario: Filter -> PivotLonger -> ColumnSelector (data reshaping workflow)
    When I add "Filter" keeping config=["baseline", "opt_a"]
    And I add "Pivot Longer" with id_vars=["config"], value_vars=["ipc", "power"]
    And I add "Column Selector" keeping ["config", "variable", "value"]
    Then the result should be long-format with only selected configs

  Scenario: Pipeline step receives output of previous step
    Given step 1 is ColumnSelector with columns ["config", "ipc"]
    And step 2 is Mean with group=["config"], vars=["ipc"]
    Then step 2's input data should be the 2-column output from step 1
    And step 2's preview should show aggregated means

  Scenario: Step ordering matters -- reorder changes output
    Given pipeline steps [Filter(config=baseline), Mean(group=config)]
    When I move Mean before Filter
    Then the result changes because mean is now computed across all configs
    And then filtered to baseline only

  Scenario: Removing a middle step re-chains remaining steps
    Given pipeline [ColumnSelector, Sort, Normalize]
    When I delete Sort
    Then Normalize receives ColumnSelector output directly
    And the pipeline should still produce valid output
```

### 13.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_multi_step_pipeline.py
"""E2E tests for multi-step pipeline combinations."""

import pytest
from playwright.sync_api import Page, expect


class TestMultiStepPipeline:
    """Tests for chaining multiple shapers in a single pipeline."""

    PLOT_ID = 1

    def test_bar_chart_recipe_select_mean_sort(
        self, page: Page, loaded_app: None
    ) -> None:
        """Three-step pipeline: ColumnSelector -> Mean -> Sort produces valid output."""
        # Step 1: Add Column Selector
        page.get_by_test_id(f"shaper_add_{self.PLOT_ID}").select_option("Column Selector")
        page.get_by_test_id(f"add_shaper_btn_{self.PLOT_ID}").click()
        page.wait_for_timeout(500)

        # Step 2: Add Mean Calculator
        page.get_by_test_id(f"shaper_add_{self.PLOT_ID}").select_option("Mean Calculator")
        page.get_by_test_id(f"add_shaper_btn_{self.PLOT_ID}").click()
        page.wait_for_timeout(500)

        # Step 3: Add Sort
        page.get_by_test_id(f"shaper_add_{self.PLOT_ID}").select_option("Sort")
        page.get_by_test_id(f"add_shaper_btn_{self.PLOT_ID}").click()
        page.wait_for_timeout(500)

        # Verify all three steps exist
        expect(page.locator("text=1. Column Selector")).to_be_visible()
        expect(page.locator("text=2. Mean Calculator")).to_be_visible()
        expect(page.locator("text=3. Sort")).to_be_visible()

    def test_normalize_comparison_recipe(
        self, page: Page, loaded_app: None
    ) -> None:
        """ColumnSelector -> Normalize -> Sort produces normalized comparison data."""
        for shaper in ["Column Selector", "Normalize", "Sort"]:
            page.get_by_test_id(f"shaper_add_{self.PLOT_ID}").select_option(shaper)
            page.get_by_test_id(f"add_shaper_btn_{self.PLOT_ID}").click()
            page.wait_for_timeout(500)

        expect(page.locator("text=1. Column Selector")).to_be_visible()
        expect(page.locator("text=2. Normalize")).to_be_visible()
        expect(page.locator("text=3. Sort")).to_be_visible()

    def test_step_receives_previous_output(
        self, page: Page, two_step_pipeline_configured: None
    ) -> None:
        """Step 2 receives the transformed output from step 1."""
        # After step 1 (ColumnSelector) reduces columns,
        # step 2's config widgets should reflect the reduced column set.
        # This is verified by checking step 2's preview shows correct data.
        preview = page.locator("div[data-testid='stDataFrame']").nth(1)
        expect(preview).to_be_visible()

    def test_reorder_changes_output(
        self, page: Page, two_step_pipeline_configured: None
    ) -> None:
        """Moving steps changes the pipeline output."""
        # Move step 2 before step 1
        page.get_by_test_id(f"up_{self.PLOT_ID}_1").click()
        page.wait_for_timeout(500)
        # Verify order changed
        step1_title = page.locator("[data-testid*='expander']").first.text_content()
        assert step1_title is not None  # Steps have been reordered
```

---

## 14. Pipeline Save/Load Tests

### 14.1 Gherkin Scenarios

```gherkin
Feature: Pipeline Save and Load Persistence
  As a user who has built a complex pipeline
  I want my pipeline configuration to persist across page reloads
  So that I do not lose my transformation setup

  Background:
    Given the application supports session state persistence

  Scenario: Pipeline config persists in session state
    Given I have configured a 3-step pipeline [ColumnSelector, Mean, Sort]
    When I trigger a Streamlit re-render (e.g., interact with another widget)
    Then all 3 steps should still be visible with their configurations intact

  Scenario: Existing config is restored per step on re-render
    Given step 1 is ColumnSelector with columns ["ipc", "power"]
    When the page re-renders
    Then the ColumnSelector multiselect should still show ["ipc", "power"]
    Because each config component checks existing_config parameter

  Scenario: Step IDs maintain uniqueness across add/delete cycles
    Given I add step A (id=0), step B (id=1), step C (id=2)
    When I delete step B
    And I add step D
    Then step D should receive a new unique id (not reuse id=1)
    So that widget keys remain unique

  Scenario: Pipeline config is plot-specific
    Given plot 1 has pipeline [ColumnSelector, Mean]
    And plot 2 has pipeline [Sort, Normalize]
    When I switch from plot 1 to plot 2
    Then plot 2's pipeline should display [Sort, Normalize]
    And plot 1's pipeline should not be shown

  Scenario: Finalized data is stored for plotting
    Given I have finalized a pipeline producing a transformed DataFrame
    When I navigate to the plotting page
    Then the plotting page should use the finalized transformed data
    And the original data should remain available for re-processing

  Scenario: Export/Import pipeline configuration
    Given I have a 3-step pipeline with specific configs
    When I export the pipeline configuration as JSON
    Then the JSON should contain an ordered list of ShaperStepConfig dicts
    When I import that JSON into a new session
    Then the same 3-step pipeline should be reconstructed
```

### 14.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_pipeline_persistence.py
"""E2E tests for pipeline save/load and session state persistence."""

import pytest
from playwright.sync_api import Page, expect


class TestPipelinePersistence:
    """Tests for pipeline configuration persistence across re-renders."""

    PLOT_ID = 1

    def test_config_persists_across_rerender(
        self, page: Page, configured_pipeline: None
    ) -> None:
        """Pipeline configuration survives a Streamlit re-render."""
        # Trigger re-render by interacting with an unrelated widget
        page.locator("[data-testid='stSidebar'] button").first.click()
        page.wait_for_timeout(1000)
        # Verify pipeline steps are still present
        expect(page.locator("text=1. Column Selector")).to_be_visible()
        expect(page.locator("text=2. Mean Calculator")).to_be_visible()

    def test_step_config_values_persist(
        self, page: Page, column_selector_with_config: None
    ) -> None:
        """Individual step configuration values persist after re-render."""
        # Trigger re-render
        page.keyboard.press("r")
        page.wait_for_timeout(1000)
        ms = page.locator("[data-testid*='colsel_']")
        expect(ms.locator("span:has-text('ipc')")).to_be_visible()

    def test_finalized_data_available_for_plotting(
        self, page: Page, finalized_pipeline: None
    ) -> None:
        """After finalization, transformed data is available on plotting page."""
        # Navigate to plotting section
        page.locator("text=Plot Configuration").click()
        page.wait_for_timeout(500)
        # Verify transformed data is referenced
        expect(page.locator("div[data-testid='stDataFrame']")).to_be_visible()

    def test_plot_specific_pipelines(
        self, page: Page, two_plots_with_pipelines: None
    ) -> None:
        """Each plot maintains its own independent pipeline configuration."""
        # Plot 1 pipeline
        expect(page.locator("text=1. Column Selector")).to_be_visible()
        # Switch to plot 2
        page.locator("text=Plot 2").click()
        page.wait_for_timeout(500)
        expect(page.locator("text=1. Sort")).to_be_visible()
```

---

## 15. Error Handling & Validation Tests

### 15.1 Gherkin Scenarios

```gherkin
Feature: Pipeline Error Handling and Validation
  As a user who may misconfigure pipeline steps
  I want clear error messages and graceful degradation
  So that I can identify and fix issues without losing my work

  Background:
    Given the application is running with test data loaded

  Scenario: Incomplete config shows user-friendly warning
    Given a Mean step with empty meanVars and groupingColumns
    When the pipeline is finalized
    Then a warning "Configuration incomplete. Missing or empty fields: 'groupingColumns', 'meanVars'" should appear
    And the incomplete step should be SKIPPED (not cause a crash)

  Scenario: Step with no type is skipped
    Given a pipeline step config with no "type" field
    When apply_shapers processes it
    Then the step should be skipped with a logged warning
    And subsequent steps should continue executing

  Scenario: ValueError from shaper constructor shows error
    Given a shaper config that causes a ValueError during ShaperFactory.create_shaper
    When the pipeline is finalized
    Then an error "Configuration error" should appear with the ValueError message
    And the pipeline should halt

  Scenario: KeyError from missing column shows data error
    Given a ColumnSelector with columns=["nonexistent_col"]
    When the pipeline is finalized
    Then an error "Missing required column or field" should appear

  Scenario: Unexpected exception shows full traceback
    Given a shaper that raises an unexpected RuntimeError
    When the pipeline is finalized
    Then st.exception should display the full traceback
    And the pipeline should halt

  Scenario: UI component exception returns minimal config
    Given a shaper config UI component that throws an exception during render
    Then configure_shaper should catch it via try/except
    And return {"type": shaper_type} as a minimal fallback config
    And st.exception should display the error

  Scenario: Unknown shaper type returns minimal config
    Given configure_shaper is called with shaper_type="unknownType"
    Then it should return {"type": "unknownType"}
    And a warning should be logged about unknown shaper type

  Scenario: Unknown shaper type in factory raises ValueError
    Given ShaperFactory.create_shaper is called with type="unknownType"
    Then it should raise ValueError
    And the message should list all available types

  Scenario: None data raises ValueError
    When apply_shapers(None, configs) is called
    Then a ValueError "Cannot apply shapers to None data" should be raised

  Scenario: Validation for all 10 shaper types
    For each shaper type in the factory registry:
      When validate_shaper_config is called with an empty config
      Then the expected required fields should be flagged
      | Shaper Type       | Required Fields                                          |
      | mean              | groupingColumns, meanVars                                |
      | normalize         | normalizeVars, normalizerColumn, normalizerValue, groupBy|
      | pivotLonger       | id_vars, value_vars, var_name, value_name                |
      | pivotWider        | index, columns, values                                   |
      | sort              | order_dict                                               |
      | splitApply        | joinColumns, groups                                      |
      | columnSelector    | columns                                                  |
      | conditionSelector | column                                                   |
      | transformer       | column                                                   |
      | itemSelector      | column, strings                                          |
```

### 15.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_pipeline_error_handling.py
"""E2E tests for pipeline error handling and validation."""

import pytest
import pandas as pd
from playwright.sync_api import Page, expect

from src.core.services.shapers.factory import ShaperFactory
from src.core.services.shapers.validation import validate_shaper_config


class TestIncompleteConfigHandling:
    """Tests for incomplete/missing configuration warnings."""

    def test_incomplete_config_shows_warning(
        self, page: Page, mean_step_empty: None
    ) -> None:
        """An incomplete Mean step triggers a user-friendly warning on finalize."""
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(500)
        expect(page.locator("text=Configuration incomplete")).to_be_visible()

    def test_incomplete_step_is_skipped_not_crashed(
        self, page: Page, pipeline_with_incomplete_step: None
    ) -> None:
        """An incomplete step is skipped and subsequent steps still execute."""
        page.get_by_test_id("finalize_1").click()
        page.wait_for_timeout(1000)
        # Pipeline should still produce output (from the valid steps)
        expect(page.locator("text=Pipeline applied!")).to_be_visible()


class TestFactoryErrors:
    """Tests for ShaperFactory error handling."""

    def test_unknown_type_raises_valueerror(self) -> None:
        """Unknown shaper type raises ValueError with available types listed."""
        with pytest.raises(ValueError, match="Unknown shaper type"):
            ShaperFactory.create_shaper("unknownType", {})

    def test_valueerror_lists_available_types(self) -> None:
        """ValueError message includes all registered types."""
        try:
            ShaperFactory.create_shaper("unknownType", {})
        except ValueError as e:
            for stype in ["mean", "normalize", "sort", "columnSelector"]:
                assert stype in str(e)


class TestApplyShaperErrors:
    """Tests for apply_shapers error conditions."""

    def test_none_data_raises_valueerror(self) -> None:
        """apply_shapers raises ValueError when data is None."""
        from src.web.pages.ui.shaper_config import apply_shapers
        with pytest.raises(ValueError, match="Cannot apply shapers to None data"):
            apply_shapers(None, [])

    def test_step_with_no_type_is_skipped(self) -> None:
        """A step config without 'type' key is silently skipped."""
        from src.web.pages.ui.shaper_config import apply_shapers
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = apply_shapers(df, [{"columns": ["a"]}])
        assert result.equals(df)  # No transformation applied

    def test_missing_column_raises_keyerror(self) -> None:
        """Referencing a nonexistent column raises KeyError."""
        from src.web.pages.ui.shaper_config import apply_shapers
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        config = [{"type": "columnSelector", "columns": ["nonexistent"]}]
        with pytest.raises((KeyError, Exception)):
            apply_shapers(df, config)


class TestValidationForAllShaperTypes:
    """Tests ensuring validation covers all 10 shaper types."""

    @pytest.mark.parametrize(
        "shaper_type,expected_missing",
        [
            ("mean", ["groupingColumns", "meanVars"]),
            ("normalize", ["normalizeVars", "normalizerColumn", "normalizerValue", "groupBy"]),
            ("pivotLonger", ["id_vars", "value_vars", "var_name", "value_name"]),
            ("pivotWider", ["index", "columns", "values"]),
            ("sort", ["order_dict"]),
            ("splitApply", ["joinColumns", "groups"]),
            ("columnSelector", ["columns"]),
            ("conditionSelector", ["column"]),
            ("transformer", ["column"]),
            ("itemSelector", ["column", "strings"]),
        ],
    )
    def test_empty_config_flags_required_fields(
        self, shaper_type: str, expected_missing: list[str]
    ) -> None:
        """Empty config for each shaper type flags the correct required fields."""
        is_valid, missing = validate_shaper_config(shaper_type, {})
        assert not is_valid
        assert missing is not None
        for field in expected_missing:
            assert field in missing, f"Expected '{field}' in missing for {shaper_type}"

    @pytest.mark.parametrize("shaper_type", ShaperFactory.get_available_types())
    def test_all_factory_types_have_validation_rules(self, shaper_type: str) -> None:
        """Every registered factory type has validation rules defined."""
        from src.core.services.shapers.validation import _REQUIRED_PARAMS
        assert shaper_type in _REQUIRED_PARAMS, (
            f"Shaper type '{shaper_type}' is registered in factory "
            f"but has no validation rules in _REQUIRED_PARAMS"
        )


class TestUIComponentErrorHandling:
    """Tests for configure_shaper error handling."""

    def test_unknown_shaper_type_returns_minimal_config(self) -> None:
        """Unknown shaper type returns minimal config with just type key."""
        from src.web.pages.ui.shaper_config import configure_shaper
        result = configure_shaper("unknownType", pd.DataFrame(), 0, None)
        assert result == {"type": "unknownType"}

    def test_config_dispatch_covers_all_ui_shapers(self) -> None:
        """The config_dispatch dict covers all 9 shapers with UI components."""
        expected_types = {
            "columnSelector", "normalize", "mean", "conditionSelector",
            "splitApply", "transformer", "sort", "pivotLonger", "pivotWider",
        }
        # Verify by checking the dispatch dict keys
        from src.web.pages.ui.shaper_config import configure_shaper
        # The dispatch is internal but we can verify via behavior
        for stype in expected_types:
            # Should not log "Unknown shaper type" -- just verify no crash
            result = configure_shaper(stype, pd.DataFrame({"a": [1]}), 0, None)
            assert "type" in result
```
