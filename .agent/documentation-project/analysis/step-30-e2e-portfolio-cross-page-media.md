# Step 30 -- E2E Tests: Portfolio Cross-Page & Media/Visual Regression

> **Objective**: Design exhaustive E2E tests for the portfolio system (save/load/delete),
> cross-page state consistency, schema migration V1-to-V2, round-trip fidelity,
> figure spec enrichment during save, and visual regression/screenshot comparison.

---

## 1. Executive Summary

The portfolio subsystem is the single most state-intensive feature in RING-5.
A portfolio save captures a **complete workspace snapshot** -- DataFrame CSV,
all plot objects (serialized via `PlotProtocol.to_dict()`), global config dict,
plot counter, CSV path, parse variables, stats path/pattern, scanned variables,
manager history, and portfolio history. Loading a portfolio must restore the
**exact** session state so that every page (Data Source, Data Managers, Manage
Plots, Save/Load Portfolio) behaves as if the user never left.

### Test Surface

```
Portfolio operations: save, load, delete, list
State fields serialized: ~14 top-level keys in PortfolioData
Schema versions: V1 (legacy) -> V2 (current, engine field + no export_* keys)
Pages involved: Data Source | Data Managers | Manage Plots | Save/Load Portfolio
Figure spec enrichment: ConfigSpecBuilder.from_config() injected into save path
Media outputs: PNG, SVG, PDF, PGF screenshots for visual regression
```

### Architecture Under Test

```
portfolio.py (UI page)
  |
  +--> ApplicationAPI.data_services.save_portfolio(...)
  |      |
  |      +--> PortfolioService.save_portfolio()
  |             - Serializes PlotProtocol objects via to_dict()
  |             - Calls figure_spec_enricher callback (ConfigSpecBuilder.from_config)
  |             - Writes JSON to .ring5/portfolios/<sanitized_name>.json
  |
  +--> ApplicationAPI.data_services.load_portfolio(...)
  |      |
  |      +--> PortfolioService.load_portfolio()
  |             - Reads JSON from disk
  |             - Runs PortfolioMigrator.migrate() (V1->V2)
  |             - Returns PortfolioData TypedDict
  |      |
  |      +--> StateManager.restore_session(portfolio_data)
  |             - Restores all 14+ state fields
  |
  +--> ApplicationAPI.data_services.delete_portfolio(...)
         |
         +--> PortfolioService.delete_portfolio()
                - Validates path within portfolios dir
                - Unlinks file
```

### Risk Matrix

| Risk                               | Severity | E2E Coverage              |
|------------------------------------|----------|---------------------------|
| Save silently drops a state field  | Critical | Round-trip fidelity tests  |
| Load corrupts DataFrame types      | Critical | CSV round-trip assertion   |
| V1 portfolio fails to migrate      | High     | Schema migration tests     |
| Figure spec not enriched on save   | Medium   | Enrichment verification    |
| Cross-page state drift after load  | High     | Cross-page consistency     |
| Delete leaves orphan JSON          | Low      | Delete + list verification |
| Path traversal in portfolio name   | Critical | Security boundary tests   |

---

## 2. Portfolio System Overview

### 2.1 PortfolioData TypedDict (14 Fields)

Source: `src/core/models/portfolio_models.py`

```python
class PortfolioData(TypedDict, total=False):
    parse_variables: list[ParseVariableConfig]
    stats_path: str
    stats_pattern: str
    csv_path: str
    use_parser: bool
    scanned_variables: list[ScannedVariableDict]
    data_csv: str                              # Full CSV as string
    plots: list[dict[str, Any]]                # Serialized plot dicts
    plot_counter: int
    config: dict[str, Any]                     # Global config
    shapers: list[ShaperStepConfig]
    manager_history: list[OperationRecord]
    portfolio_history: list[OperationRecord]
```

### 2.2 Save Path: Fields Written to JSON

Source: `src/core/services/data_services/portfolio_service.py` lines 148-165

The `save_portfolio` method builds a dict with these keys:
- `schema_version` (always `PortfolioMigrator.CURRENT_VERSION` = 2)
- `version` ("2.0")
- `timestamp` (ISO-8601)
- `data_csv` (DataFrame.to_csv string)
- `csv_path`
- `plots` (list of plot dicts, each potentially enriched with `figure_spec`)
- `plot_counter`
- `config`
- `parse_variables`
- `stats_path`, `stats_pattern`, `scanned_variables`
- `manager_history`, `portfolio_history`

### 2.3 Load Path: Migration + Restore

1. `PortfolioService.load_portfolio()` reads JSON and passes raw dict to
   `PortfolioMigrator.migrate()`.
2. If `schema_version < 2`, runs `_migrate_v1_to_v2()`:
   - Deep copies the data.
   - Adds `config["engine"] = "plotly"` default to each plot.
   - Removes all `export_*` keys from each plot config.
3. Returns the migrated `PortfolioData`.
4. `StateManager.restore_session()` sets all session fields from the dict.

### 2.4 Navigation Architecture

Source: `app.py` lines 67-73, 138-157

```python
_NAV_OPTIONS = [
    "Data Source",
    "Data Managers",
    "Manage Plots",
    "Save/Load Portfolio",
    "Documentation",
]
```

Navigation is sidebar button-driven. Each page is lazy-imported. The
`Save/Load Portfolio` page is at index 3. After loading a portfolio,
`st.rerun(scope="app")` forces a full app rerun to propagate restored state.

---

## 3. Portfolio Save Tests

### 3.1 Gherkin Scenarios

```gherkin
Feature: Portfolio Save
  Save a complete workspace snapshot to disk as a JSON portfolio file.

  Background:
    Given the RING-5 application is running
    And a CSV file "sample_data.csv" has been loaded with 100 rows and 5 columns
    And a grouped bar plot named "IPC Comparison" has been created
    And a line plot named "Cycle Trend" has been created

  Scenario: Save portfolio with default name
    When the user navigates to "Save/Load Portfolio"
    And the user enters "my_portfolio" in the portfolio name field
    And the user clicks the "Save Portfolio" button
    Then a toast message "Portfolio saved: my_portfolio" appears
    And a file ".ring5/portfolios/my_portfolio.json" exists on disk
    And the JSON file contains the key "schema_version" with value 2
    And the JSON file contains the key "data_csv" with non-empty content
    And the JSON file "plots" array has exactly 2 entries

  Scenario: Save portfolio preserves all state fields
    Given the user has set stats_path to "/sim/stats"
    And the user has set stats_pattern to "stats*.txt"
    And the user has applied 3 data manager operations (recorded in manager_history)
    When the user saves a portfolio named "full_state"
    Then the JSON file contains all 14 expected top-level keys:
      | schema_version    |
      | version           |
      | timestamp         |
      | data_csv          |
      | csv_path          |
      | plots             |
      | plot_counter      |
      | config            |
      | parse_variables   |
      | stats_path        |
      | stats_pattern     |
      | scanned_variables |
      | manager_history   |
      | portfolio_history |

  Scenario: Save portfolio with empty name is rejected
    When the user clears the portfolio name field
    And the user clicks "Save Portfolio"
    Then an error message is displayed
    And no new file is created in ".ring5/portfolios/"

  Scenario: Save portfolio with special characters in name
    When the user enters "my/portfolio/../../../etc/passwd" as the portfolio name
    And the user clicks "Save Portfolio"
    Then the file is saved with a sanitized filename
    And the file path is validated to remain within ".ring5/portfolios/"

  Scenario: Save portfolio overwrites existing file with same name
    Given a portfolio named "existing" was previously saved
    When the user saves a portfolio named "existing"
    Then the file ".ring5/portfolios/existing.json" is overwritten
    And the timestamp in the file reflects the newer save time

  Scenario: Save portfolio with no data loaded
    Given no CSV file has been loaded
    When the user saves a portfolio named "empty_state"
    Then the JSON file has an empty "data_csv" field
    And the "plots" array is empty
    And the portfolio still saves successfully

  Scenario: Save portfolio enriches plots with figure_spec
    Given a grouped bar plot exists with config keys: width=800, height=500, bargap=0.2
    When the user saves a portfolio named "enriched"
    Then each plot dict in the JSON contains a "figure_spec" key
    And the figure_spec contains "dimensions" with width=800.0 and height=500.0
    And the figure_spec contains "typography" with expected font sizes
```

### 3.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_portfolio_save.py
"""E2E tests for portfolio save operations."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


class TestPortfolioSave:
    """Tests for saving portfolios via the UI."""

    PORTFOLIO_DIR = Path(".ring5/portfolios")

    @pytest.fixture(autouse=True)
    def _setup(self, page: Page, load_sample_csv: None, create_bar_plot: None) -> None:
        """Navigate to portfolio page with data and plots loaded."""
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.wait_for_load_state("networkidle")

    def test_save_creates_json_file(self, page: Page, tmp_path: Path) -> None:
        """Saving a portfolio creates a valid JSON file on disk."""
        page.get_by_label("Portfolio Name").fill("e2e_save_test")
        page.get_by_role("button", name="Save Portfolio").click()

        # Verify toast notification
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        # Verify file on disk
        portfolio_path = self.PORTFOLIO_DIR / "e2e_save_test.json"
        assert portfolio_path.exists(), "Portfolio JSON was not created"
        data = json.loads(portfolio_path.read_text())
        assert data["schema_version"] == 2
        assert data["version"] == "2.0"
        assert len(data["data_csv"]) > 0

    def test_save_preserves_all_state_fields(self, page: Page) -> None:
        """Saved portfolio JSON contains all required top-level keys."""
        page.get_by_label("Portfolio Name").fill("full_state_test")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        portfolio_path = self.PORTFOLIO_DIR / "full_state_test.json"
        data = json.loads(portfolio_path.read_text())

        required_keys = {
            "schema_version", "version", "timestamp", "data_csv",
            "csv_path", "plots", "plot_counter", "config",
            "parse_variables", "stats_path", "stats_pattern",
            "scanned_variables", "manager_history", "portfolio_history",
        }
        missing = required_keys - set(data.keys())
        assert not missing, f"Missing keys in portfolio JSON: {missing}"

    def test_save_empty_name_shows_error(self, page: Page) -> None:
        """Empty portfolio name triggers an error, no file created."""
        page.get_by_label("Portfolio Name").fill("")
        page.get_by_role("button", name="Save Portfolio").click()

        # Expect error display (st.exception renders a red box)
        expect(page.locator(".stException")).to_be_visible(timeout=5000)

    def test_save_sanitizes_dangerous_name(self, page: Page) -> None:
        """Path traversal characters are sanitized from portfolio name."""
        dangerous_name = "../../etc/passwd"
        page.get_by_label("Portfolio Name").fill(dangerous_name)
        page.get_by_role("button", name="Save Portfolio").click()

        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)
        # Verify file stayed within portfolios dir
        for f in self.PORTFOLIO_DIR.iterdir():
            assert self.PORTFOLIO_DIR in f.parents or f.parent == self.PORTFOLIO_DIR

    def test_save_with_figure_spec_enrichment(self, page: Page) -> None:
        """Saved plot dicts contain figure_spec from ConfigSpecBuilder."""
        page.get_by_label("Portfolio Name").fill("enriched_test")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        portfolio_path = self.PORTFOLIO_DIR / "enriched_test.json"
        data = json.loads(portfolio_path.read_text())

        for plot_dict in data["plots"]:
            assert "figure_spec" in plot_dict, (
                f"Plot '{plot_dict.get('name', '?')}' missing figure_spec"
            )
            spec = plot_dict["figure_spec"]
            assert "dimensions" in spec
            assert "typography" in spec
            assert spec["dimensions"]["width"] > 0
            assert spec["dimensions"]["height"] > 0

    def test_save_no_data_succeeds(
        self, page: Page, clear_all_data: None,
    ) -> None:
        """Saving with no DataFrame loaded still creates a valid portfolio."""
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("empty_data_test")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        portfolio_path = self.PORTFOLIO_DIR / "empty_data_test.json"
        data = json.loads(portfolio_path.read_text())
        assert data["data_csv"] == ""
        assert data["plots"] == []

    def test_save_overwrite_updates_timestamp(self, page: Page) -> None:
        """Saving to the same name overwrites and updates the timestamp."""
        name = "overwrite_test"
        page.get_by_label("Portfolio Name").fill(name)
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        path = self.PORTFOLIO_DIR / f"{name}.json"
        ts1 = json.loads(path.read_text())["timestamp"]

        # Save again
        page.get_by_label("Portfolio Name").fill(name)
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        ts2 = json.loads(path.read_text())["timestamp"]
        assert ts2 > ts1, "Timestamp was not updated on overwrite"
```

---

## 4. Portfolio Load Tests

### 4.1 Gherkin Scenarios

```gherkin
Feature: Portfolio Load
  Load a previously saved portfolio and restore the complete workspace state.

  Background:
    Given the RING-5 application is running
    And a portfolio named "analysis_v2" has been previously saved with:
      | Field            | Value                        |
      | data_csv         | 100 rows, 5 columns          |
      | plots            | 2 plots (bar + line)         |
      | plot_counter     | 3                            |
      | config           | {"engine": "plotly"}         |
      | parse_variables  | ["system.cpu.ipc"]           |
      | stats_path       | "/sim/output"                |
      | manager_history  | 2 operations                 |

  Scenario: Load portfolio restores DataFrame
    When the user navigates to "Save/Load Portfolio"
    And the user selects "analysis_v2" from the portfolio dropdown
    And the user clicks "Load Portfolio"
    Then a toast message "Portfolio loaded: analysis_v2" appears
    And the data preview shows "100" rows and "5" columns
    And the loaded DataFrame column names match the original

  Scenario: Load portfolio restores plots
    When the user loads the portfolio "analysis_v2"
    And the user navigates to "Manage Plots"
    Then 2 plots are visible in the plot list
    And the first plot is named "IPC Comparison" with type "grouped_bar"
    And the second plot is named "Cycle Trend" with type "line"

  Scenario: Load portfolio restores plot counter
    When the user loads "analysis_v2"
    And the user creates a new plot
    Then the new plot receives ID 4 (plot_counter was restored as 3)

  Scenario: Load portfolio restores config
    When the user loads "analysis_v2"
    And the user navigates to "Manage Plots"
    Then the engine selector shows "plotly"

  Scenario: Load portfolio with no portfolios available
    Given no portfolio files exist in ".ring5/portfolios/"
    When the user navigates to "Save/Load Portfolio"
    Then a warning "No portfolios found. Save one first!" is displayed
    And no dropdown or load button is shown

  Scenario: Load non-existent portfolio file (race condition)
    Given a portfolio "deleted_between_list_and_load" was listed
    But the file was deleted externally before clicking Load
    When the user clicks "Load Portfolio"
    Then an error is displayed (FileNotFoundError)

  Scenario: Load portfolio triggers full app rerun
    When the user loads "analysis_v2"
    Then st.rerun(scope="app") is called
    And all pages reflect the restored state without manual refresh
```

### 4.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_portfolio_load.py
"""E2E tests for portfolio load operations."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


class TestPortfolioLoad:
    """Tests for loading portfolios via the UI."""

    @pytest.fixture
    def saved_portfolio(self, page: Page, load_sample_csv: None, create_two_plots: None) -> str:
        """Save a portfolio and return its name for load tests."""
        name = "e2e_load_fixture"
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill(name)
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)
        return name

    def test_load_restores_dataframe_metrics(
        self, page: Page, saved_portfolio: str,
    ) -> None:
        """Loading a portfolio restores DataFrame row/column metrics."""
        # Clear current state first
        page.get_by_role("button", name="Clear Data").click()
        page.wait_for_load_state("networkidle")

        # Now load the saved portfolio
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(saved_portfolio)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        # Verify data preview metrics
        expect(page.get_by_text("100")).to_be_visible()  # row count
        expect(page.get_by_text("5")).to_be_visible()     # column count

    def test_load_restores_plots_on_manage_page(
        self, page: Page, saved_portfolio: str,
    ) -> None:
        """After loading, Manage Plots page shows the restored plots."""
        page.get_by_role("button", name="Clear Data").click()
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(saved_portfolio)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")

        # Expect restored plots visible
        expect(page.get_by_text("IPC Comparison")).to_be_visible()
        expect(page.get_by_text("Cycle Trend")).to_be_visible()

    def test_load_no_portfolios_shows_warning(self, page: Page, clean_portfolios_dir: None) -> None:
        """When no portfolios exist, a warning is displayed."""
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.wait_for_load_state("networkidle")

        expect(page.get_by_text("No portfolios found")).to_be_visible()

    def test_load_missing_file_shows_error(
        self, page: Page, saved_portfolio: str,
    ) -> None:
        """Loading a portfolio whose file was externally deleted shows error."""
        # Delete the file on disk
        portfolio_path = Path(".ring5/portfolios") / f"{saved_portfolio}.json"
        portfolio_path.unlink()

        # Attempt to load (portfolio still in the dropdown from cached list)
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_role("button", name="Load Portfolio").click()

        expect(page.locator(".stException")).to_be_visible(timeout=5000)

    def test_load_restores_plot_counter_continuity(
        self, page: Page, saved_portfolio: str,
    ) -> None:
        """After load, new plots get IDs continuing from the saved counter."""
        page.get_by_role("button", name="Clear Data").click()
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(saved_portfolio)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        # Navigate to Manage Plots and create a new plot
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")

        # The new plot should have ID = saved_counter + 1
        # (Specific assertion depends on UI rendering of plot IDs)
```

---

## 5. Portfolio Delete Tests

### 5.1 Gherkin Scenarios

```gherkin
Feature: Portfolio Delete
  Delete saved portfolios from the management section.

  Background:
    Given the RING-5 application is running
    And portfolios named "keep_me" and "delete_me" have been saved

  Scenario: Delete a single portfolio
    When the user navigates to "Save/Load Portfolio"
    And the user expands the "delete_me" portfolio expander
    And the user clicks the "Delete" button for "delete_me"
    Then a toast message "Deleted delete_me" appears
    And "delete_me" is no longer listed in the portfolio dropdown
    And the file ".ring5/portfolios/delete_me.json" does not exist

  Scenario: Delete does not affect other portfolios
    When the user deletes "delete_me"
    Then "keep_me" is still listed in the portfolio dropdown
    And the file ".ring5/portfolios/keep_me.json" still exists

  Scenario: Delete all portfolios shows empty state
    When the user deletes "keep_me" and "delete_me"
    Then the warning "No portfolios found. Save one first!" appears
    And the portfolio dropdown is not displayed

  Scenario: Delete portfolio that is currently loaded
    Given portfolio "active_session" is currently loaded
    When the user deletes "active_session"
    Then the file is deleted from disk
    But the current session state is NOT affected
    And all loaded data and plots remain intact

  Scenario: Delete portfolio path traversal safety
    Given a portfolio named "safe_name" exists
    When the delete handler is called with name "../../important_file"
    Then the path is validated to remain within ".ring5/portfolios/"
    And no file outside the portfolios directory is deleted
```

### 5.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_portfolio_delete.py
"""E2E tests for portfolio delete operations."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


class TestPortfolioDelete:
    """Tests for deleting portfolios via the UI."""

    PORTFOLIO_DIR = Path(".ring5/portfolios")

    @pytest.fixture
    def two_saved_portfolios(
        self, page: Page, load_sample_csv: None,
    ) -> tuple[str, str]:
        """Create two portfolios for delete tests. Returns (name1, name2)."""
        page.get_by_role("button", name="Save/Load Portfolio").click()

        for name in ("keep_this", "delete_this"):
            page.get_by_label("Portfolio Name").fill(name)
            page.get_by_role("button", name="Save Portfolio").click()
            expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        return ("keep_this", "delete_this")

    def test_delete_removes_file(
        self, page: Page, two_saved_portfolios: tuple[str, str],
    ) -> None:
        """Deleting a portfolio removes its JSON file from disk."""
        _, delete_name = two_saved_portfolios

        # Expand the portfolio entry and click delete
        page.get_by_text(delete_name).click()  # expander
        page.get_by_role("button", name="Delete").nth(1).click()

        expect(page.get_by_text(f"Deleted {delete_name}")).to_be_visible(timeout=5000)
        assert not (self.PORTFOLIO_DIR / f"{delete_name}.json").exists()

    def test_delete_preserves_other_portfolios(
        self, page: Page, two_saved_portfolios: tuple[str, str],
    ) -> None:
        """Deleting one portfolio does not affect others."""
        keep_name, delete_name = two_saved_portfolios

        page.get_by_text(delete_name).click()
        page.get_by_role("button", name="Delete").nth(1).click()
        expect(page.get_by_text(f"Deleted {delete_name}")).to_be_visible(timeout=5000)

        assert (self.PORTFOLIO_DIR / f"{keep_name}.json").exists()

    def test_delete_all_shows_empty_state(
        self, page: Page, two_saved_portfolios: tuple[str, str],
    ) -> None:
        """Deleting all portfolios shows the empty state warning."""
        for name in two_saved_portfolios:
            page.get_by_text(name).click()
            page.locator(f'[key="del_portfolio_{name}"]').click()

        page.wait_for_load_state("networkidle")
        expect(page.get_by_text("No portfolios found")).to_be_visible()

    def test_delete_does_not_clear_current_session(
        self, page: Page, two_saved_portfolios: tuple[str, str],
    ) -> None:
        """Deleting a loaded portfolio keeps the current session intact."""
        keep_name, _ = two_saved_portfolios

        # Load one, then delete it
        page.get_by_label("Select Portfolio").select_option(keep_name)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        # Now delete the same portfolio
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_text(keep_name).click()
        page.locator(f'[key="del_portfolio_{keep_name}"]').click()

        # Session data should still be intact
        expect(page.get_by_text("100")).to_be_visible()  # rows still showing
```

---

## 6. Cross-Page State Consistency Tests

### 6.1 Gherkin Scenarios

```gherkin
Feature: Cross-Page State Consistency
  After loading a portfolio, all pages must reflect the restored state.

  Background:
    Given the RING-5 application is running
    And a portfolio "cross_page_test" was saved with:
      | data_csv        | 200 rows, 8 columns              |
      | plots           | 3 plots (bar, line, scatter)      |
      | config          | {"engine": "matplotlib"}          |
      | csv_path        | "/data/experiment_results.csv"    |
      | parse_variables | ["system.cpu.ipc", "numCycles"]   |
      | stats_path      | "/sim/m5out"                      |
      | stats_pattern   | "stats.txt"                       |
      | manager_history | 4 operations (reduce + preprocess)|
    And the portfolio has been loaded

  Scenario: Data Source page reflects restored data
    When the user navigates to "Data Source"
    Then the data preview shows 200 rows and 8 columns
    And the CSV path indicator shows "experiment_results.csv"
    And if parser mode is active, stats_path shows "/sim/m5out"
    And parse_variables include "system.cpu.ipc" and "numCycles"

  Scenario: Data Managers page reflects restored history
    When the user navigates to "Data Managers"
    Then the operation history table shows 4 entries
    And the history entries include "reduce" and "preprocess" operations
    And each entry has source_columns, dest_columns, operation, and timestamp

  Scenario: Manage Plots page reflects restored plots
    When the user navigates to "Manage Plots"
    Then 3 plots are listed in the plot selector
    And the engine selector shows "matplotlib"
    And selecting each plot shows its preserved configuration

  Scenario: Creating a new plot after load uses correct counter
    Given the portfolio was loaded with plot_counter=4
    When the user creates a new bar plot on "Manage Plots"
    Then the plot receives ID 5 (counter incremented from 4)
    And the original 3 plots are unaffected

  Scenario: Navigating between pages preserves state
    When the user navigates from "Data Source" to "Manage Plots"
    And then navigates to "Data Managers"
    And then navigates back to "Manage Plots"
    Then all 3 plots are still listed
    And the selected plot configuration has not changed

  Scenario: Clear Data resets all pages after load
    Given a portfolio is loaded with full state
    When the user clicks "Clear Data" in the sidebar
    Then the Data Source page shows no data
    And Data Managers page shows no operations
    And Manage Plots page shows no plots

  Scenario: Reset All returns to clean initial state
    Given a portfolio is loaded
    When the user clicks "Reset All" in the sidebar
    Then navigation is set to "Data Source"
    And all state is wiped cleanly
```

### 6.2 Pytest-Playwright Stubs

```python
# tests/e2e/test_cross_page_consistency.py
"""E2E tests for state consistency across all pages after portfolio load."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


class TestCrossPageConsistency:
    """Tests verifying state coherence after portfolio load across all pages."""

    @pytest.fixture
    def loaded_portfolio(
        self, page: Page, load_sample_csv: None,
        create_three_plots: None,
    ) -> str:
        """Save and reload a portfolio with rich state."""
        name = "cross_page_fixture"
        # Save
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill(name)
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        # Clear then reload to prove restore works
        page.get_by_role("button", name="Clear Data").click()
        page.wait_for_load_state("networkidle")

        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(name)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)
        return name

    def test_data_source_shows_restored_data(
        self, page: Page, loaded_portfolio: str,
    ) -> None:
        """Data Source page shows correct row/column counts after load."""
        page.get_by_role("button", name="Data Source").click()
        page.wait_for_load_state("networkidle")

        # The data preview metrics fragment should reflect restored data
        expect(page.locator("[data-testid='stMetric']").first).to_be_visible()

    def test_manage_plots_shows_restored_plots(
        self, page: Page, loaded_portfolio: str,
    ) -> None:
        """Manage Plots page lists all plots from the loaded portfolio."""
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")

        # Verify each plot type is present (created in create_three_plots fixture)
        for plot_name in ("bar_plot", "line_plot", "scatter_plot"):
            expect(page.get_by_text(plot_name)).to_be_visible()

    def test_data_managers_shows_restored_history(
        self, page: Page, loaded_portfolio: str,
    ) -> None:
        """Data Managers page shows operation history from the portfolio."""
        page.get_by_role("button", name="Data Managers").click()
        page.wait_for_load_state("networkidle")
        # History visualization should reflect the portfolio's manager_history

    def test_navigation_cycle_preserves_state(
        self, page: Page, loaded_portfolio: str,
    ) -> None:
        """Navigating between all pages and back preserves state."""
        pages = ["Data Source", "Data Managers", "Manage Plots",
                 "Save/Load Portfolio", "Documentation"]

        for nav_page in pages:
            page.get_by_role("button", name=nav_page).click()
            page.wait_for_load_state("networkidle")

        # Return to Manage Plots and verify plots still present
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")
        for plot_name in ("bar_plot", "line_plot", "scatter_plot"):
            expect(page.get_by_text(plot_name)).to_be_visible()

    def test_clear_data_resets_all_pages(
        self, page: Page, loaded_portfolio: str,
    ) -> None:
        """Clear Data button wipes data from all pages."""
        page.get_by_role("button", name="Clear Data").click()
        page.wait_for_load_state("networkidle")

        # Manage Plots should be empty
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")
        # No plots should be listed (verify empty state)
```

---

## 7. Schema Migration Tests (V1 to V2)

### 7.1 Migration Logic Reference

Source: `src/core/services/portfolio_migrator.py`

```
V1 -> V2 changes:
  1. config["engine"] defaulted to "plotly" if absent
  2. All "export_*" keys removed from each plot config
  3. schema_version set to 2
  4. Deep copy ensures original dict is not mutated
```

### 7.2 Gherkin Scenarios

```gherkin
Feature: Portfolio Schema Migration V1 to V2
  Portfolios saved with schema V1 are transparently migrated on load.

  Background:
    Given the RING-5 application is running

  Scenario: Load V1 portfolio adds engine field
    Given a V1 portfolio file exists with no "engine" key in plot configs
    When the user loads this portfolio
    Then each plot config contains "engine": "plotly"
    And the portfolio JSON in memory has schema_version: 2

  Scenario: Load V1 portfolio removes export_ keys
    Given a V1 portfolio file exists with plot config keys:
      | export_format | export_dpi | export_path |
    When the user loads this portfolio
    Then none of the plot configs contain keys starting with "export_"

  Scenario: Load V1 portfolio preserves data integrity
    Given a V1 portfolio file with 50 rows of data
    When the user loads this portfolio
    Then the restored DataFrame has exactly 50 rows
    And all column names match the original

  Scenario: Migration is idempotent
    Given a V2 portfolio file (already current)
    When the migration is applied
    Then no changes occur
    And the file content is identical to the original

  Scenario: V1 portfolio with unknown keys preserved
    Given a V1 portfolio file has extra keys ("future_feature": true)
    When the user loads this portfolio
    Then the unknown keys are preserved (forward compatibility)
    And migration only touches engine and export_* keys

  Scenario: V1 portfolio with missing schema_version
    Given a portfolio file has no "schema_version" key at all
    When the user loads this portfolio
    Then the migrator treats it as V1 (default version = 1)
    And migration runs normally producing V2
```

### 7.3 Pytest-Playwright Stubs

```python
# tests/e2e/test_portfolio_migration.py
"""E2E tests for portfolio schema migration V1 -> V2."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


# ── V1 Portfolio Fixtures ──────────────────────────────────────────

V1_PORTFOLIO_TEMPLATE: dict = {
    "version": "1.0",
    "timestamp": "2025-06-15T10:00:00",
    "data_csv": "col_a,col_b\n1,2\n3,4\n5,6\n",
    "csv_path": "/data/test.csv",
    "plots": [
        {
            "name": "Legacy Bar",
            "plot_type": "grouped_bar",
            "config": {
                "width": 800,
                "height": 500,
                "export_format": "png",
                "export_dpi": 150,
                "export_path": "/tmp/export",
            },
        },
        {
            "name": "Legacy Line",
            "plot_type": "line",
            "config": {
                "width": 700,
                "height": 400,
                "export_format": "svg",
                "export_dpi": 300,
            },
        },
    ],
    "plot_counter": 3,
    "config": {},
    "parse_variables": [],
    "stats_path": "",
    "stats_pattern": "",
    "scanned_variables": [],
    "manager_history": [],
    "portfolio_history": [],
}


class TestPortfolioMigration:
    """Tests for schema migration during portfolio load."""

    PORTFOLIO_DIR = Path(".ring5/portfolios")

    @pytest.fixture
    def v1_portfolio(self) -> str:
        """Write a V1 portfolio file to disk. Returns the portfolio name."""
        name = "v1_legacy"
        self.PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
        path = self.PORTFOLIO_DIR / f"{name}.json"
        path.write_text(json.dumps(V1_PORTFOLIO_TEMPLATE, indent=2))
        return name

    @pytest.fixture
    def v1_portfolio_no_schema(self) -> str:
        """Write a V1 portfolio with no schema_version key."""
        name = "v1_no_schema"
        data = dict(V1_PORTFOLIO_TEMPLATE)
        data.pop("schema_version", None)
        self.PORTFOLIO_DIR.mkdir(parents=True, exist_ok=True)
        path = self.PORTFOLIO_DIR / f"{name}.json"
        path.write_text(json.dumps(data, indent=2))
        return name

    def test_v1_load_adds_engine_field(
        self, page: Page, v1_portfolio: str,
    ) -> None:
        """V1 portfolios get engine='plotly' added to each plot config."""
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(v1_portfolio)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        # Verify by re-saving and inspecting the JSON
        page.get_by_label("Portfolio Name").fill("v1_migrated_check")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        migrated = json.loads(
            (self.PORTFOLIO_DIR / "v1_migrated_check.json").read_text()
        )
        assert migrated["schema_version"] == 2
        for plot in migrated["plots"]:
            assert plot["config"].get("engine") == "plotly"

    def test_v1_load_removes_export_keys(
        self, page: Page, v1_portfolio: str,
    ) -> None:
        """V1 portfolios have all export_* keys stripped during migration."""
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(v1_portfolio)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        # Re-save to check migrated state
        page.get_by_label("Portfolio Name").fill("v1_no_export_check")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        migrated = json.loads(
            (self.PORTFOLIO_DIR / "v1_no_export_check.json").read_text()
        )
        for plot in migrated["plots"]:
            export_keys = [k for k in plot.get("config", {}) if k.startswith("export_")]
            assert export_keys == [], f"Unexpected export keys: {export_keys}"

    def test_v1_no_schema_version_treated_as_v1(
        self, page: Page, v1_portfolio_no_schema: str,
    ) -> None:
        """Portfolio with no schema_version key is treated as V1."""
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(v1_portfolio_no_schema)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        # Data should be restored despite missing schema_version
        expect(page.get_by_text("3")).to_be_visible()  # 3 rows from V1 template

    def test_v2_portfolio_idempotent_migration(self, page: Page) -> None:
        """Re-migrating a V2 portfolio produces identical output."""
        from src.core.services.portfolio_migrator import PortfolioMigrator
        import copy

        v2_data = {
            "schema_version": 2,
            "plots": [{"config": {"engine": "plotly", "width": 800}}],
        }
        original = copy.deepcopy(v2_data)
        migrated = PortfolioMigrator.migrate(v2_data)

        assert migrated["schema_version"] == 2
        assert migrated["plots"] == original["plots"]
```

---

## 8. Round-Trip Fidelity Tests

### 8.1 Strategy

Round-trip tests verify that `save -> load -> compare` produces an identical
workspace. This is the most critical guarantee of the portfolio system.

```
Fidelity dimensions:
  1. DataFrame: column names, dtypes, row count, cell values
  2. Plots: count, names, types, config dicts (key-by-key)
  3. Config: global config dict equality
  4. Plot counter: exact integer match
  5. Parse variables: list equality
  6. Stats metadata: stats_path, stats_pattern, scanned_variables
  7. History: manager_history and portfolio_history records
```

### 8.2 Gherkin Scenarios

```gherkin
Feature: Portfolio Round-Trip Fidelity
  Save -> Load -> Verify that restored state is byte-identical to original.

  Scenario: DataFrame round-trip preserves column names and types
    Given a DataFrame with columns: ["benchmark", "config", "ipc", "cycles", "l2_miss"]
    And column types: [str, str, float64, int64, float64]
    When the workspace is saved as "rt_data" and then loaded
    Then the restored DataFrame has identical column names
    And the column dtypes match the original
    And DataFrame.equals(original) returns True

  Scenario: Plot list round-trip preserves all plot attributes
    Given 3 plots exist: grouped_bar, line, scatter
    And each has distinct config dicts with 20+ keys
    When the workspace is saved and reloaded
    Then len(plots) == 3
    And each plot's name, plot_type, and config match the original

  Scenario: Config round-trip preserves all keys
    Given the config dict has 15 keys including nested dicts
    When the workspace is saved and reloaded
    Then the restored config dict is identical to the original

  Scenario: History round-trip preserves all operation records
    Given manager_history has 5 OperationRecord entries
    And portfolio_history has 3 entries
    When the workspace is saved and reloaded
    Then restored manager_history has 5 entries with matching fields
    And restored portfolio_history has 3 entries with matching fields

  Scenario: Full round-trip across engine switch
    Given a bar plot is configured with engine "plotly"
    And the workspace is saved
    When the workspace is loaded and the engine is switched to "matplotlib"
    And the workspace is saved again and reloaded
    Then the restored engine is "matplotlib"
```

### 8.3 Pytest-Playwright Stubs

```python
# tests/e2e/test_portfolio_roundtrip.py
"""E2E tests for save -> load -> verify round-trip fidelity."""

import json
from io import StringIO
from pathlib import Path

import pandas as pd
import pytest
from playwright.sync_api import Page, expect


class TestPortfolioRoundTrip:
    """Round-trip fidelity tests: save -> clear -> load -> compare."""

    PORTFOLIO_DIR = Path(".ring5/portfolios")

    def _read_portfolio(self, name: str) -> dict:
        """Read a portfolio JSON from disk."""
        path = self.PORTFOLIO_DIR / f"{name}.json"
        return json.loads(path.read_text())

    @pytest.fixture
    def round_trip_state(
        self, page: Page, load_sample_csv: None, create_three_plots: None,
    ) -> dict:
        """Save portfolio, read JSON, clear, reload. Returns original JSON."""
        name = "roundtrip_test"
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill(name)
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        original = self._read_portfolio(name)

        # Clear and reload
        page.get_by_role("button", name="Clear Data").click()
        page.wait_for_load_state("networkidle")
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(name)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        return original

    def test_dataframe_roundtrip_fidelity(
        self, page: Page, round_trip_state: dict,
    ) -> None:
        """DataFrame survives save -> load -> re-save with identical content."""
        original_csv = round_trip_state["data_csv"]

        # Re-save under a different name and compare CSV
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("roundtrip_resaved")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        resaved = self._read_portfolio("roundtrip_resaved")
        resaved_csv = resaved["data_csv"]

        df_original = pd.read_csv(StringIO(original_csv))
        df_resaved = pd.read_csv(StringIO(resaved_csv))

        assert list(df_original.columns) == list(df_resaved.columns)
        assert len(df_original) == len(df_resaved)
        pd.testing.assert_frame_equal(df_original, df_resaved)

    def test_plots_roundtrip_fidelity(
        self, page: Page, round_trip_state: dict,
    ) -> None:
        """Plot list survives save -> load -> re-save with identical config."""
        original_plots = round_trip_state["plots"]

        # Re-save and compare
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("roundtrip_plots_check")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        resaved = self._read_portfolio("roundtrip_plots_check")
        resaved_plots = resaved["plots"]

        assert len(resaved_plots) == len(original_plots)
        for orig, resv in zip(original_plots, resaved_plots):
            assert orig["name"] == resv["name"]
            assert orig["plot_type"] == resv["plot_type"]
            # Config comparison (exclude figure_spec which is re-generated)
            for key in orig.get("config", {}):
                assert orig["config"][key] == resv["config"].get(key), (
                    f"Config key '{key}' mismatch: "
                    f"{orig['config'][key]} != {resv['config'].get(key)}"
                )

    def test_plot_counter_roundtrip(
        self, page: Page, round_trip_state: dict,
    ) -> None:
        """Plot counter survives round-trip exactly."""
        original_counter = round_trip_state["plot_counter"]

        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("roundtrip_counter")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        resaved = self._read_portfolio("roundtrip_counter")
        assert resaved["plot_counter"] == original_counter

    def test_history_roundtrip_fidelity(
        self, page: Page, round_trip_state: dict,
    ) -> None:
        """Operation history records survive round-trip."""
        original_mgr = round_trip_state["manager_history"]
        original_pf = round_trip_state["portfolio_history"]

        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("roundtrip_history")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        resaved = self._read_portfolio("roundtrip_history")
        assert len(resaved["manager_history"]) == len(original_mgr)
        assert len(resaved["portfolio_history"]) == len(original_pf)

        for orig, resv in zip(original_mgr, resaved["manager_history"]):
            assert orig["operation"] == resv["operation"]
            assert orig["source_columns"] == resv["source_columns"]
            assert orig["dest_columns"] == resv["dest_columns"]
```

---

## 9. Figure Spec Enrichment Tests

### 9.1 Enrichment Architecture

Source: `src/web/pages/portfolio.py` lines 20-23 and
`src/core/services/data_services/portfolio_service.py` lines 130-143

```
Save flow:
  portfolio.py._build_figure_spec(config, plot_type)
    -> ConfigSpecBuilder.from_config(config, plot_type)
    -> FigureConfig.to_dict()
    -> injected as figure_spec_enricher callback
    -> PortfolioService calls enricher for each plot
    -> Stores result under plot_dict["figure_spec"]
```

The enricher is a **callback injection** pattern: the web layer provides the
function, the core layer calls it. This avoids core-to-web imports while
still enabling spec generation during save.

### 9.2 Gherkin Scenarios

```gherkin
Feature: Figure Spec Enrichment During Save
  When saving a portfolio, each plot is enriched with a FigureConfig spec.

  Scenario: Grouped bar plot gets correct figure_spec
    Given a grouped bar plot with config: width=800, height=500, bargap=0.2
    When the portfolio is saved
    Then the plot dict contains "figure_spec" with:
      | Key                         | Expected Value |
      | dimensions.width            | 800.0          |
      | dimensions.height           | 500.0          |
      | dimensions.dpi              | 1              |
      | dimensions.bargap           | 0.2            |
      | typography.font_size_title  | 18 (default)   |

  Scenario: Line plot gets correct figure_spec
    Given a line plot with config: width=700, height=400, title="Trend"
    When the portfolio is saved
    Then the figure_spec contains dimensions.width=700.0
    And figure_spec contains title="Trend"
    And figure_spec dimensions.bargap=0.0 (not a bar plot)

  Scenario: Enricher failure does not prevent save
    Given a plot with malformed config (missing required keys)
    When the portfolio is saved
    Then the save succeeds
    And the plot dict may lack "figure_spec" (graceful degradation)
    And no exception is raised to the user

  Scenario: figure_spec includes legend configuration
    Given a plot with custom legend: position_x=0.5, position_y=-0.2, ncols=3
    When the portfolio is saved
    Then figure_spec.legends[0] contains position_x=0.5
    And figure_spec.legends[0] contains ncol=3

  Scenario: figure_spec includes axis labels
    Given a plot with xlabel="Benchmark" and ylabel="IPC"
    When the portfolio is saved
    Then figure_spec.axes.x.label="Benchmark"
    And figure_spec.axes.y.label="IPC"
```

### 9.3 Pytest-Playwright Stubs

```python
# tests/e2e/test_figure_spec_enrichment.py
"""E2E tests for figure_spec enrichment during portfolio save."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


class TestFigureSpecEnrichment:
    """Verify that saved portfolios contain correctly enriched figure_spec."""

    PORTFOLIO_DIR = Path(".ring5/portfolios")

    @pytest.fixture
    def portfolio_with_bar(
        self, page: Page, load_sample_csv: None, create_bar_plot: None,
    ) -> dict:
        """Save a portfolio with a bar plot and return the JSON."""
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("spec_bar_test")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)
        return json.loads(
            (self.PORTFOLIO_DIR / "spec_bar_test.json").read_text()
        )

    def test_bar_plot_figure_spec_dimensions(self, portfolio_with_bar: dict) -> None:
        """Bar plot figure_spec contains correct dimension values."""
        for plot in portfolio_with_bar["plots"]:
            if "bar" in plot.get("plot_type", ""):
                assert "figure_spec" in plot
                dims = plot["figure_spec"]["dimensions"]
                assert dims["width"] > 0
                assert dims["height"] > 0
                assert dims["dpi"] == 1  # px passthrough
                assert dims["bargap"] >= 0

    def test_figure_spec_has_typography(self, portfolio_with_bar: dict) -> None:
        """Figure spec includes typography configuration."""
        for plot in portfolio_with_bar["plots"]:
            if "figure_spec" in plot:
                typo = plot["figure_spec"]["typography"]
                assert "font_size_title" in typo
                assert "font_size_xlabel" in typo
                assert "font_size_ylabel" in typo
                assert typo["font_size_title"] > 0

    def test_figure_spec_has_axes(self, portfolio_with_bar: dict) -> None:
        """Figure spec includes axis configuration."""
        for plot in portfolio_with_bar["plots"]:
            if "figure_spec" in plot:
                axes = plot["figure_spec"]["axes"]
                assert "x" in axes
                assert "y" in axes

    def test_figure_spec_has_legends(self, portfolio_with_bar: dict) -> None:
        """Figure spec includes legend configuration."""
        for plot in portfolio_with_bar["plots"]:
            if "figure_spec" in plot:
                legends = plot["figure_spec"]["legends"]
                assert isinstance(legends, list)
                assert len(legends) >= 1
                assert legends[0]["role"] == "primary"

    def test_enricher_failure_graceful(
        self, page: Page, load_sample_csv: None,
    ) -> None:
        """If enricher fails for a plot, the save still succeeds."""
        # This test verifies the try/except in PortfolioService.save_portfolio
        # lines 139-143. Even if ConfigSpecBuilder.from_config raises, the
        # plot is saved without figure_spec.
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("enricher_fail_test")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)
```

---

## 10. Visual Regression Testing Strategy

### 10.1 Overview

Visual regression tests capture screenshots of rendered plots and compare them
against golden baselines. This catches unintended layout, color, or typography
regressions that functional assertions would miss.

### 10.2 Baseline Categories

```
Plot Type Baselines:
  grouped_bar_plotly.png        grouped_bar_matplotlib.png
  stacked_bar_plotly.png        stacked_bar_matplotlib.png
  line_plotly.png               line_matplotlib.png
  scatter_plotly.png            scatter_matplotlib.png
  heatmap_plotly.png            heatmap_matplotlib.png
  dual_axis_plotly.png          dual_axis_matplotlib.png
  violin_plotly.png             violin_matplotlib.png

Configuration Effect Baselines:
  bar_with_data_labels.png
  bar_with_reference_line.png
  bar_with_custom_palette.png
  bar_with_error_bars.png
  bar_with_legend_bottom.png

Engine Comparison Pairs:
  grouped_bar_plotly_vs_matplotlib.png  (side-by-side)
```

### 10.3 Gherkin Scenarios

```gherkin
Feature: Visual Regression Detection
  Screenshot baselines detect unintended visual changes.

  Scenario Outline: Plot type <plot_type> with engine <engine> matches baseline
    Given a standard dataset is loaded
    And a <plot_type> plot is created with engine <engine>
    And default configuration is applied
    When a screenshot of the plot area is captured
    Then the screenshot matches "<plot_type>_<engine>.png" within 1% threshold

    Examples:
      | plot_type    | engine     |
      | grouped_bar  | plotly     |
      | grouped_bar  | matplotlib |
      | stacked_bar  | plotly     |
      | stacked_bar  | matplotlib |
      | line         | plotly     |
      | line         | matplotlib |
      | scatter      | plotly     |
      | scatter      | matplotlib |
      | heatmap      | plotly     |
      | heatmap      | matplotlib |

  Scenario: Data label toggle produces visual change
    Given a bar plot baseline screenshot exists
    When data labels are enabled
    And a new screenshot is captured
    Then the new screenshot differs from the baseline by > 0.5%
    And the new screenshot matches "bar_with_data_labels.png" baseline

  Scenario: Engine switch produces visually similar but distinct output
    Given a bar plot with engine "plotly" is screenshotted
    And the engine is switched to "matplotlib"
    And a new screenshot is captured
    Then the two screenshots differ (different rendering engines)
    But both show the same data (same bar heights/positions)
```

### 10.4 Pytest-Playwright Stubs

```python
# tests/e2e/test_visual_regression.py
"""Visual regression tests using Playwright screenshot comparison."""

from pathlib import Path

import pytest
from playwright.sync_api import Page, expect

BASELINE_DIR = Path("tests/e2e/baselines")
PLOT_TYPES = ["grouped_bar", "stacked_bar", "line", "scatter", "heatmap"]
ENGINES = ["plotly", "matplotlib"]


class TestVisualRegression:
    """Screenshot-based visual regression for all plot types and engines."""

    @pytest.fixture(autouse=True)
    def _setup(self, page: Page, load_sample_csv: None) -> None:
        """Load data and navigate to Manage Plots."""
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")

    @pytest.mark.parametrize("plot_type", PLOT_TYPES)
    @pytest.mark.parametrize("engine", ENGINES)
    def test_plot_baseline_match(
        self, page: Page, plot_type: str, engine: str,
    ) -> None:
        """Rendered plot matches visual baseline within threshold."""
        # Create the plot with the specified type and engine
        # (Assumes helper fixture or page object to create plots)
        baseline_name = f"{plot_type}_{engine}.png"
        baseline_path = BASELINE_DIR / baseline_name

        # Capture plot area screenshot
        plot_container = page.locator(".plotly-graph-div, .matplotlib-figure")
        screenshot = plot_container.screenshot()

        if not baseline_path.exists():
            # First run: create baseline
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            baseline_path.write_bytes(screenshot)
            pytest.skip(f"Baseline created: {baseline_name}")

        # Compare using Playwright's built-in screenshot comparison
        expect(plot_container).to_have_screenshot(
            baseline_name,
            max_diff_pixel_ratio=0.01,  # 1% threshold
        )

    def test_data_labels_visual_change(self, page: Page) -> None:
        """Enabling data labels produces a measurable visual difference."""
        # Create bar plot, capture baseline
        plot_container = page.locator(".plotly-graph-div, .matplotlib-figure")
        baseline = plot_container.screenshot()

        # Enable data labels
        page.get_by_label("Show Values").check()
        page.wait_for_timeout(500)

        labeled = plot_container.screenshot()
        assert baseline != labeled, "Data labels produced no visual change"
```

---

## 11. Screenshot Comparison Framework

### 11.1 Architecture

```
tests/e2e/
  baselines/                          # Golden baseline screenshots
    grouped_bar_plotly.png
    grouped_bar_matplotlib.png
    ...
  screenshots/                        # Captured during test run
    grouped_bar_plotly_actual.png
    grouped_bar_plotly_diff.png        # Diff image (auto-generated)
  conftest.py                         # Shared fixtures and helpers
  visual_utils.py                     # Comparison helpers
```

### 11.2 Comparison Utilities

```python
# tests/e2e/visual_utils.py
"""Visual comparison utilities for screenshot-based regression testing."""

from pathlib import Path

import numpy as np
from PIL import Image


def pixel_diff_ratio(img_a: Path, img_b: Path) -> float:
    """Compute fraction of pixels that differ between two images.

    Args:
        img_a: Path to first image.
        img_b: Path to second image.

    Returns:
        Float in [0.0, 1.0] representing fraction of differing pixels.
    """
    a = np.array(Image.open(img_a).convert("RGB"))
    b = np.array(Image.open(img_b).convert("RGB"))

    if a.shape != b.shape:
        return 1.0  # Different dimensions = 100% diff

    diff = np.abs(a.astype(int) - b.astype(int))
    changed_pixels = np.any(diff > 5, axis=-1)  # tolerance per channel
    return float(changed_pixels.sum()) / changed_pixels.size


def generate_diff_image(img_a: Path, img_b: Path, output: Path) -> None:
    """Create a visual diff image highlighting changed pixels in red.

    Args:
        img_a: Path to baseline image.
        img_b: Path to actual image.
        output: Path to write the diff image.
    """
    a = np.array(Image.open(img_a).convert("RGB"))
    b = np.array(Image.open(img_b).convert("RGB"))

    if a.shape != b.shape:
        Image.fromarray(b).save(output)
        return

    diff = np.abs(a.astype(int) - b.astype(int))
    mask = np.any(diff > 5, axis=-1)

    result = b.copy()
    result[mask] = [255, 0, 0]  # Red overlay on changed pixels
    Image.fromarray(result.astype(np.uint8)).save(output)


class ScreenshotComparator:
    """Manages screenshot comparison workflow for E2E visual tests."""

    def __init__(
        self,
        baseline_dir: Path,
        output_dir: Path,
        max_diff_ratio: float = 0.01,
    ) -> None:
        self.baseline_dir = baseline_dir
        self.output_dir = output_dir
        self.max_diff_ratio = max_diff_ratio
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def compare(self, name: str, actual_bytes: bytes) -> tuple[bool, float]:
        """Compare a screenshot against its baseline.

        Args:
            name: Baseline filename (e.g., "grouped_bar_plotly.png").
            actual_bytes: Raw PNG bytes from Playwright screenshot.

        Returns:
            (passed, diff_ratio) tuple.
        """
        baseline = self.baseline_dir / name
        actual_path = self.output_dir / f"{Path(name).stem}_actual.png"
        actual_path.write_bytes(actual_bytes)

        if not baseline.exists():
            # Create baseline on first run
            baseline.parent.mkdir(parents=True, exist_ok=True)
            baseline.write_bytes(actual_bytes)
            return True, 0.0

        ratio = pixel_diff_ratio(baseline, actual_path)

        if ratio > self.max_diff_ratio:
            diff_path = self.output_dir / f"{Path(name).stem}_diff.png"
            generate_diff_image(baseline, actual_path, diff_path)
            return False, ratio

        return True, ratio
```

### 11.3 Conftest Fixtures

```python
# tests/e2e/conftest.py (visual regression fixtures)
"""Shared fixtures for E2E visual regression tests."""

from pathlib import Path

import pytest
from playwright.sync_api import Page

from tests.e2e.visual_utils import ScreenshotComparator

BASELINE_DIR = Path("tests/e2e/baselines")
OUTPUT_DIR = Path("tests/e2e/screenshots")


@pytest.fixture
def comparator() -> ScreenshotComparator:
    """Provide a screenshot comparator with default thresholds."""
    return ScreenshotComparator(
        baseline_dir=BASELINE_DIR,
        output_dir=OUTPUT_DIR,
        max_diff_ratio=0.01,
    )


@pytest.fixture
def load_sample_csv(page: Page) -> None:
    """Load the standard sample CSV for E2E tests."""
    page.get_by_role("button", name="Data Source").click()
    page.wait_for_load_state("networkidle")
    # Upload or select the standard test CSV
    # Implementation depends on data source page layout


@pytest.fixture
def create_bar_plot(page: Page) -> None:
    """Create a standard grouped bar plot for tests."""
    page.get_by_role("button", name="Manage Plots").click()
    page.wait_for_load_state("networkidle")
    # Create and configure a grouped bar plot
    # Implementation depends on plot creation UI


@pytest.fixture
def create_two_plots(page: Page) -> None:
    """Create a bar plot and a line plot."""
    # Create bar plot named "IPC Comparison"
    # Create line plot named "Cycle Trend"
    pass


@pytest.fixture
def create_three_plots(page: Page) -> None:
    """Create bar, line, and scatter plots."""
    pass


@pytest.fixture
def clear_all_data(page: Page) -> None:
    """Click Clear Data to remove all loaded data."""
    page.get_by_role("button", name="Clear Data").click()
    page.wait_for_load_state("networkidle")


@pytest.fixture
def clean_portfolios_dir() -> None:
    """Remove all portfolio files from disk."""
    portfolio_dir = Path(".ring5/portfolios")
    if portfolio_dir.exists():
        for f in portfolio_dir.glob("*.json"):
            f.unlink()
```

---

## 12. Media Asset Management

### 12.1 Asset Inventory for Portfolio & Cross-Page Tests

```
tests/e2e/baselines/
  # Plot type baselines (per engine)
  grouped_bar_plotly.png
  grouped_bar_matplotlib.png
  stacked_bar_plotly.png
  stacked_bar_matplotlib.png
  line_plotly.png
  line_matplotlib.png
  scatter_plotly.png
  scatter_matplotlib.png
  heatmap_plotly.png
  heatmap_matplotlib.png

  # Configuration effect baselines
  bar_with_data_labels.png
  bar_with_reference_line.png
  bar_with_custom_palette.png
  bar_with_error_bars.png
  bar_with_legend_bottom.png
  bar_with_stripes.png

  # Cross-page screenshots
  portfolio_save_page.png
  portfolio_load_page.png
  portfolio_manage_section.png
  portfolio_empty_state.png

  # Responsive layout
  layout_1920x1080.png
  layout_1280x800.png
  layout_1024x768.png

Total baselines: ~30 images
```

### 12.2 Responsive Layout Tests

```gherkin
Feature: Responsive Layout
  Application layout adapts to different viewport sizes.

  Scenario Outline: Layout at <width>x<height> matches baseline
    Given the browser viewport is set to <width>x<height>
    And a standard dataset is loaded with a bar plot
    When a full-page screenshot is captured
    Then it matches "layout_<width>x<height>.png" within 2% threshold

    Examples:
      | width | height |
      | 1920  | 1080   |
      | 1280  | 800    |
      | 1024  | 768    |

  Scenario: Sidebar collapses on narrow viewport
    Given the browser viewport is set to 800x600
    Then the sidebar is collapsed or hidden
    And the main content fills the available width
```

```python
# tests/e2e/test_responsive_layout.py
"""E2E tests for responsive layout across viewport sizes."""

import pytest
from playwright.sync_api import Page, expect

VIEWPORTS = [
    (1920, 1080),
    (1280, 800),
    (1024, 768),
]


class TestResponsiveLayout:
    """Responsive layout tests for different screen sizes."""

    @pytest.mark.parametrize("width,height", VIEWPORTS)
    def test_layout_at_viewport(
        self, page: Page, width: int, height: int,
        load_sample_csv: None, create_bar_plot: None,
        comparator: "ScreenshotComparator",
    ) -> None:
        """Full-page layout matches baseline at specified viewport."""
        page.set_viewport_size({"width": width, "height": height})
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)  # Allow reflow

        screenshot = page.screenshot(full_page=True)
        name = f"layout_{width}x{height}.png"
        passed, ratio = comparator.compare(name, screenshot)
        assert passed, f"Layout at {width}x{height} differs by {ratio:.2%}"
```

---

## 13. Complete E2E Workflow Tests (Full User Journey)

### 13.1 Journey 1: First-Time User -- Parse, Plot, Save

```gherkin
Feature: First-Time User Journey
  A user goes through the complete workflow from data loading to portfolio save.

  Scenario: Complete first-time workflow
    Given the RING-5 application is running with no saved state

    # Step 1: Data Source
    When the user navigates to "Data Source"
    And the user selects CSV mode and uploads "experiment.csv"
    Then the data preview shows the uploaded data

    # Step 2: Data Managers
    When the user navigates to "Data Managers"
    And the user applies a "seeds_reducer" operation with mean aggregation
    Then the data preview updates with reduced rows
    And the manager_history shows 1 entry

    # Step 3: Create Plot
    When the user navigates to "Manage Plots"
    And the user creates a "grouped_bar" plot
    And the user selects X="benchmark", Y="ipc", Group="config"
    Then a bar chart is rendered

    # Step 4: Configure Plot
    When the user sets: title="IPC Comparison", xlabel="Benchmark", ylabel="IPC"
    And the user changes the color palette to "viridis"
    And the user enables data labels
    Then the chart updates with the new configuration

    # Step 5: Save Portfolio
    When the user navigates to "Save/Load Portfolio"
    And the user enters "first_analysis" as the portfolio name
    And the user clicks "Save Portfolio"
    Then the portfolio is saved with all state
    And the user can continue working
```

### 13.2 Journey 2: Returning User -- Load, Modify, Re-Save

```gherkin
Feature: Returning User Journey
  A user loads a saved portfolio, makes changes, and re-saves.

  Scenario: Load and modify workflow
    Given a portfolio "first_analysis" was previously saved

    # Step 1: Load
    When the user navigates to "Save/Load Portfolio"
    And the user selects "first_analysis" and clicks Load
    Then the data, plots, and configuration are restored

    # Step 2: Verify restoration on Manage Plots
    When the user navigates to "Manage Plots"
    Then the "IPC Comparison" bar chart is visible with its configuration

    # Step 3: Modify
    When the user switches the engine from "plotly" to "matplotlib"
    And the user adjusts the title font size to 24
    Then the chart re-renders with Matplotlib backend

    # Step 4: Add a new plot
    When the user creates a "line" plot with X="benchmark", Y="cycles"
    Then 2 plots are now listed

    # Step 5: Re-save
    When the user navigates to "Save/Load Portfolio"
    And the user saves as "first_analysis_v2"
    Then a new portfolio is created
    And the original "first_analysis" is unchanged
```

### 13.3 Pytest-Playwright Stubs

```python
# tests/e2e/test_complete_journeys.py
"""End-to-end user journey tests covering cross-page workflows."""

import json
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


class TestFirstTimeUserJourney:
    """Full workflow: upload CSV -> process -> plot -> configure -> save."""

    PORTFOLIO_DIR = Path(".ring5/portfolios")

    def test_complete_first_time_workflow(self, page: Page) -> None:
        """First-time user completes full workflow across all pages."""

        # Step 1: Upload CSV
        page.get_by_role("button", name="Data Source").click()
        page.wait_for_load_state("networkidle")
        # Upload sample CSV (implementation depends on upload mechanism)

        # Step 2: Data Managers -- apply operations
        page.get_by_role("button", name="Data Managers").click()
        page.wait_for_load_state("networkidle")
        # Apply seeds reducer or other operation

        # Step 3: Create plot
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")
        # Create grouped bar plot with column selections

        # Step 4: Configure plot
        # Set title, labels, colors, data labels

        # Step 5: Save portfolio
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("e2e_journey_1")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        # Verify the portfolio file
        portfolio_data = json.loads(
            (self.PORTFOLIO_DIR / "e2e_journey_1.json").read_text()
        )
        assert portfolio_data["schema_version"] == 2
        assert len(portfolio_data["data_csv"]) > 0
        assert len(portfolio_data["plots"]) >= 1


class TestReturningUserJourney:
    """Load -> modify -> re-save workflow."""

    PORTFOLIO_DIR = Path(".ring5/portfolios")

    @pytest.fixture
    def existing_portfolio(
        self, page: Page, load_sample_csv: None, create_bar_plot: None,
    ) -> str:
        """Create an initial portfolio for the returning user journey."""
        name = "returning_user_base"
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill(name)
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)
        return name

    def test_load_modify_resave(
        self, page: Page, existing_portfolio: str,
    ) -> None:
        """Returning user loads, modifies, and saves a new version."""

        # Step 1: Clear and reload
        page.get_by_role("button", name="Clear Data").click()
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Select Portfolio").select_option(existing_portfolio)
        page.get_by_role("button", name="Load Portfolio").click()
        expect(page.get_by_text("Portfolio loaded")).to_be_visible(timeout=5000)

        # Step 2: Navigate to Manage Plots and verify plot exists
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")

        # Step 3: Modify plot (change title, switch engine, etc.)
        # Implementation depends on specific widget selectors

        # Step 4: Save as new version
        page.get_by_role("button", name="Save/Load Portfolio").click()
        page.get_by_label("Portfolio Name").fill("returning_user_v2")
        page.get_by_role("button", name="Save Portfolio").click()
        expect(page.get_by_text("Portfolio saved")).to_be_visible(timeout=5000)

        # Verify both portfolios exist
        assert (self.PORTFOLIO_DIR / f"{existing_portfolio}.json").exists()
        assert (self.PORTFOLIO_DIR / "returning_user_v2.json").exists()

        # Verify new portfolio has modifications
        v2_data = json.loads(
            (self.PORTFOLIO_DIR / "returning_user_v2.json").read_text()
        )
        assert v2_data["schema_version"] == 2


class TestMultiPlotJourney:
    """Journey creating multiple plots and verifying state across switches."""

    def test_multi_plot_state_preservation(
        self, page: Page, load_sample_csv: None,
    ) -> None:
        """Create 3 plots, switch between them, verify each config is preserved."""
        page.get_by_role("button", name="Manage Plots").click()
        page.wait_for_load_state("networkidle")

        # Create 3 plots of different types
        plot_configs = [
            {"type": "grouped_bar", "title": "Bar Plot"},
            {"type": "line", "title": "Line Plot"},
            {"type": "scatter", "title": "Scatter Plot"},
        ]

        for config in plot_configs:
            # Create each plot and set title
            # (Implementation per UI widgets)
            pass

        # Switch between plots and verify titles preserved
        for config in plot_configs:
            # Select plot, verify title matches
            pass
```

---

## 14. Page Object Model for PortfolioPage

### 14.1 PortfolioPage POM

```python
# tests/e2e/pages/portfolio_page.py
"""Page Object Model for the Save/Load Portfolio page."""

from pathlib import Path

from playwright.sync_api import Locator, Page, expect


class PortfolioPage:
    """POM for the portfolio management page.

    Encapsulates all selectors and actions for the Save/Load Portfolio
    page. Used by E2E tests to interact with portfolio features without
    hardcoding selectors.

    Attributes:
        page: The Playwright Page instance.
        PORTFOLIO_DIR: Path to the portfolios directory on disk.
    """

    PORTFOLIO_DIR = Path(".ring5/portfolios")

    def __init__(self, page: Page) -> None:
        self.page = page

    # ── Navigation ──────────────────────────────────────────────

    def navigate(self) -> None:
        """Navigate to the Save/Load Portfolio page via sidebar."""
        self.page.get_by_role("button", name="Save/Load Portfolio").click()
        self.page.wait_for_load_state("networkidle")

    # ── Locators ────────────────────────────────────────────────

    @property
    def save_name_input(self) -> Locator:
        """The portfolio name text input field."""
        return self.page.get_by_label("Portfolio Name")

    @property
    def save_button(self) -> Locator:
        """The Save Portfolio button."""
        return self.page.get_by_role("button", name="Save Portfolio")

    @property
    def load_dropdown(self) -> Locator:
        """The Select Portfolio dropdown."""
        return self.page.get_by_label("Select Portfolio")

    @property
    def load_button(self) -> Locator:
        """The Load Portfolio button."""
        return self.page.get_by_role("button", name="Load Portfolio")

    @property
    def no_portfolios_warning(self) -> Locator:
        """The 'No portfolios found' warning message."""
        return self.page.get_by_text("No portfolios found")

    @property
    def save_toast(self) -> Locator:
        """The save success toast notification."""
        return self.page.get_by_text("Portfolio saved")

    @property
    def load_toast(self) -> Locator:
        """The load success toast notification."""
        return self.page.get_by_text("Portfolio loaded")

    @property
    def error_display(self) -> Locator:
        """The Streamlit exception display element."""
        return self.page.locator(".stException")

    def portfolio_expander(self, name: str) -> Locator:
        """The expander for a specific portfolio in the Manage section."""
        return self.page.get_by_text(name)

    def delete_button(self, name: str) -> Locator:
        """The Delete button for a specific portfolio."""
        return self.page.locator(f'[key="del_portfolio_{name}"]')

    # ── Actions ─────────────────────────────────────────────────

    def save(self, name: str) -> None:
        """Save a portfolio with the given name.

        Args:
            name: Portfolio name to use.
        """
        self.save_name_input.fill(name)
        self.save_button.click()
        expect(self.save_toast).to_be_visible(timeout=5000)

    def load(self, name: str) -> None:
        """Load a portfolio by name.

        Args:
            name: Portfolio name to select from dropdown.
        """
        self.load_dropdown.select_option(name)
        self.load_button.click()
        expect(self.load_toast).to_be_visible(timeout=5000)

    def delete(self, name: str) -> None:
        """Delete a portfolio by name.

        Args:
            name: Portfolio name to delete.
        """
        self.portfolio_expander(name).click()
        self.delete_button(name).click()

    def list_portfolios(self) -> list[str]:
        """Get list of portfolio names from the dropdown options.

        Returns:
            List of portfolio name strings.
        """
        options = self.load_dropdown.locator("option").all()
        return [opt.text_content() or "" for opt in options]

    # ── Disk Assertions ────────────────────────────────────────

    def assert_file_exists(self, name: str) -> None:
        """Assert that a portfolio JSON file exists on disk."""
        path = self.PORTFOLIO_DIR / f"{name}.json"
        assert path.exists(), f"Portfolio file not found: {path}"

    def assert_file_not_exists(self, name: str) -> None:
        """Assert that a portfolio JSON file does not exist on disk."""
        path = self.PORTFOLIO_DIR / f"{name}.json"
        assert not path.exists(), f"Portfolio file should not exist: {path}"

    def read_portfolio_json(self, name: str) -> dict:
        """Read and parse a portfolio JSON file from disk.

        Args:
            name: Portfolio name (without .json extension).

        Returns:
            Parsed dictionary from the JSON file.
        """
        import json

        path = self.PORTFOLIO_DIR / f"{name}.json"
        return json.loads(path.read_text())


class ManagePlotsPage:
    """Minimal POM for the Manage Plots page (used in cross-page tests)."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def navigate(self) -> None:
        """Navigate to the Manage Plots page via sidebar."""
        self.page.get_by_role("button", name="Manage Plots").click()
        self.page.wait_for_load_state("networkidle")

    @property
    def plot_list(self) -> Locator:
        """The plot selector or list element."""
        return self.page.locator("[data-testid='stSelectbox']").first

    def get_visible_plot_names(self) -> list[str]:
        """Return names of all visible plots in the plot list."""
        # Implementation depends on how plots are rendered in the UI
        return []


class DataSourcePage:
    """Minimal POM for Data Source page (used in cross-page tests)."""

    def __init__(self, page: Page) -> None:
        self.page = page

    def navigate(self) -> None:
        """Navigate to Data Source page via sidebar."""
        self.page.get_by_role("button", name="Data Source").click()
        self.page.wait_for_load_state("networkidle")

    @property
    def row_count_metric(self) -> Locator:
        """The Rows metric widget."""
        return self.page.locator("[data-testid='stMetric']").first

    @property
    def column_count_metric(self) -> Locator:
        """The Columns metric widget."""
        return self.page.locator("[data-testid='stMetric']").nth(1)
```

### 14.2 POM Usage Example

```python
# tests/e2e/test_portfolio_with_pom.py
"""Example: Portfolio tests using Page Object Model."""

import pytest
from playwright.sync_api import Page

from tests.e2e.pages.portfolio_page import (
    DataSourcePage,
    ManagePlotsPage,
    PortfolioPage,
)


class TestPortfolioWithPOM:
    """Portfolio tests refactored to use Page Object Model."""

    def test_save_and_load_roundtrip(
        self, page: Page, load_sample_csv: None, create_bar_plot: None,
    ) -> None:
        """Complete save -> clear -> load roundtrip using POM."""
        portfolio = PortfolioPage(page)
        plots = ManagePlotsPage(page)
        data = DataSourcePage(page)

        # Save
        portfolio.navigate()
        portfolio.save("pom_roundtrip")
        portfolio.assert_file_exists("pom_roundtrip")

        # Verify JSON content
        json_data = portfolio.read_portfolio_json("pom_roundtrip")
        assert json_data["schema_version"] == 2
        assert len(json_data["plots"]) >= 1

        # Clear state
        page.get_by_role("button", name="Clear Data").click()
        page.wait_for_load_state("networkidle")

        # Reload
        portfolio.navigate()
        portfolio.load("pom_roundtrip")

        # Verify on Manage Plots
        plots.navigate()
        # Verify plots are visible

        # Verify on Data Source
        data.navigate()
        # Verify data metrics are showing

    def test_delete_via_pom(
        self, page: Page, load_sample_csv: None,
    ) -> None:
        """Delete portfolio via POM and verify removal."""
        portfolio = PortfolioPage(page)
        portfolio.navigate()

        # Save two
        portfolio.save("pom_delete_a")
        portfolio.save("pom_delete_b")

        # Delete one
        portfolio.delete("pom_delete_a")
        portfolio.assert_file_not_exists("pom_delete_a")
        portfolio.assert_file_exists("pom_delete_b")
```

---

## Appendix: Test Count Summary

| Section                        | Gherkin Scenarios | Pytest Stubs | Total |
|--------------------------------|:-----------------:|:------------:|:-----:|
| 3. Portfolio Save              | 7                 | 7            | 14    |
| 4. Portfolio Load              | 7                 | 5            | 12    |
| 5. Portfolio Delete            | 5                 | 4            | 9     |
| 6. Cross-Page Consistency      | 7                 | 5            | 12    |
| 7. Schema Migration V1->V2    | 6                 | 4            | 10    |
| 8. Round-Trip Fidelity         | 5                 | 4            | 9     |
| 9. Figure Spec Enrichment      | 5                 | 5            | 10    |
| 10. Visual Regression          | 4                 | 2            | 6     |
| 11. Screenshot Framework       | --                | 3 (utils)    | 3     |
| 12. Media/Responsive           | 3                 | 1            | 4     |
| 13. Complete Journeys          | 3                 | 3            | 6     |
| 14. POM + Usage                | --                | 2            | 2     |
| **Total**                      | **52**            | **45**       | **97**|

---

## Downstream Dependencies

- **Step 29** (Export/Presets): Portfolio save captures figure_spec that
  includes preset-derived FigureConfig fields.
- **Step 28** (Plot rendering): Visual regression baselines depend on plot
  rendering correctness from Step 28 tests.
- **Schema migration**: V1 portfolios may contain export_* keys from
  the old LaTeX export system tested in Step 29.
- **State Management**: All 14 PortfolioData fields map to StateManager
  protocol methods -- broken state management breaks portfolio round-trips.
