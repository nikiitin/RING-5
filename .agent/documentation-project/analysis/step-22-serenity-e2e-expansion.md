# Step 22: Serenity BDD E2E Expansion Plan

## 1. Executive Summary

This document presents a comprehensive Serenity BDD-style end-to-end test expansion plan for
the RING-5 Unified Engine v2, adapted from the Java/Selenium Serenity framework into a
Python/Playwright equivalent tailored for Streamlit applications. The plan covers the full
Screenplay pattern -- Actors, Tasks, Questions, and Abilities -- applied to all five application
pages: Data Source, Data Managers, Manage Plots, Save/Load Portfolio, and Documentation.

The RING-5 application is a Streamlit-based gem5 simulator data analysis and visualization
platform. Its architecture follows a Controller/Component pattern with dependency injection
via protocols, managed through a centralized `ApplicationAPI` and `UIStateManager`. The
five-page navigation structure (sidebar-driven via `st.session_state["_nav_page"]`) presents
distinct workflows: data ingestion and parsing (Data Source), data transformation with four
sub-managers across seven tabs (Data Managers), plot lifecycle and pipeline management via
three injected controllers (Manage Plots), portfolio persistence with save/load/delete
(Save/Load Portfolio), and static documentation (Documentation).

The Serenity BDD expansion targets three objectives:

1. **Behavioral Coverage**: Every user-facing workflow mapped to Gherkin feature files with
   Given/When/Then scenarios that describe business outcomes, not implementation details.
2. **Maintainable Test Architecture**: The Screenplay pattern decouples test intent from
   Streamlit widget interaction mechanics, making tests resilient to UI refactoring.
3. **Living Documentation**: Auto-generated test reports that serve as always-current
   documentation of system capabilities for stakeholders, researchers, and developers.

The implementation adapts Serenity's Java patterns to Python idioms: protocol classes replace
Java interfaces, `dataclass` builders replace Java builder pattern boilerplate, and
`pytest-bdd` replaces JBehave/Cucumber-JVM as the Gherkin execution engine.

---

## 2. Serenity Screenplay Pattern Overview

### 2.1 Pattern Philosophy

The Screenplay pattern (also called the Journey pattern) models tests from the perspective
of actors performing tasks to achieve goals, rather than page objects with method chains.
This inversion produces tests that read as behavioral specifications:

```python
DataAnalyst.attempts_to(
    LoadCSVFromPool(file_index=0),
    NavigateTo("Data Managers"),
    ApplySeedsReduction(reduce_column="random_seed"),
)
DataAnalyst.should(
    see_that(TheDataTable.row_count(), is_less_than(original_count)),
    see_that(TheDataTable.has_column("simTicks.sd"), is_true()),
)
```

This approach maps directly to RING-5's user workflows. A `DataAnalyst` does not "click a
button labeled Apply Seeds Reducer" -- they "apply seeds reduction on the random_seed column."
The Screenplay layer translates the business intent into widget interactions, isolating test
logic from Streamlit's DOM structure.

### 2.2 Core Abstractions

The Screenplay pattern defines four interacting layers:

| Abstraction | Role | RING-5 Example |
|---|---|---|
| **Actor** | A persona with abilities who performs tasks | `DataAnalyst`, `Researcher`, `PortfolioManager` |
| **Ability** | A capability an actor possesses | `BrowseTheWeb`, `InteractWithStreamlit`, `AccessFileSystem` |
| **Task** | A high-level action composed of interactions | `LoadCSVFromPool`, `CreateBarPlot`, `ApplyShaper` |
| **Question** | An assertion target querying observable state | `TheDataTable.row_count()`, `ThePlot.has_legend()` |
| **Interaction** | An atomic UI operation (click, type, select) | `Click(locator)`, `SelectFromDropdown(label, value)` |

### 2.3 Python Adaptation Architecture

```
tests/
  e2e/
    actors/
      __init__.py
      actor.py                    # Base Actor class with abilities registry
      personas.py                 # Pre-configured actor instances
    abilities/
      __init__.py
      browse_the_web.py           # Playwright page wrapper
      interact_with_streamlit.py  # Streamlit-specific widget interactions
      access_file_system.py       # File upload/download capabilities
      manage_test_state.py        # Direct ApplicationAPI access for setup
    tasks/
      __init__.py
      data_source/                # Tasks for Data Source page
        load_csv.py
        configure_parser.py
        scan_variables.py
      data_managers/              # Tasks for Data Managers page
        seeds_reducer.py
        outlier_remover.py
        preprocessor.py
        mixer.py
        search_data.py
      manage_plots/               # Tasks for Manage Plots page
        plot_lifecycle.py
        pipeline_management.py
        visualization_config.py
      portfolio/                  # Tasks for Portfolio page
        portfolio_management.py
      navigation.py               # Cross-page navigation tasks
    questions/
      __init__.py
      data_table.py               # Questions about data display
      plot_display.py             # Questions about plot rendering
      page_state.py               # Questions about page state and metrics
      navigation.py               # Questions about current page/location
      portfolio.py                # Questions about portfolio state
    interactions/
      __init__.py
      streamlit_widgets.py        # Atomic Streamlit widget interactions
      wait_conditions.py          # Streamlit-specific wait strategies
    features/
      data_source.feature
      data_managers.feature
      manage_plots.feature
      portfolio.feature
    builders/
      __init__.py
      csv_data_builder.py         # Test data builders for CSV fixtures
      plot_config_builder.py      # Test data builders for plot configs
      portfolio_builder.py        # Portfolio snapshot builders
      variable_config_builder.py  # Parser variable config builders
    conftest.py                   # pytest-bdd fixtures and hooks
    living_docs/
      report_generator.py         # Serenity-style living doc generation
      template/                   # HTML report templates
```

### 2.4 Protocol Contracts

```python
# tests/e2e/actors/actor.py
from typing import Protocol, TypeVar, Any, Generic

T = TypeVar("T")

class Ability(Protocol):
    """Base protocol for all abilities."""
    pass

class Performable(Protocol):
    """Something an actor can perform (Task or Interaction)."""
    def perform_as(self, actor: "Actor") -> Any: ...

class Answerable(Protocol[T]):
    """Something that resolves to a value (Question)."""
    def answered_by(self, actor: "Actor") -> T: ...

class Expectation:
    """An assertion wrapping a Question and a matcher."""
    def __init__(self, question: Answerable, matcher: Any) -> None:
        self._question = question
        self._matcher = matcher

    def evaluate(self, actor: "Actor") -> None:
        actual = self._question.answered_by(actor)
        assert self._matcher(actual), (
            f"Expected {self._matcher} but got {actual}"
        )

def see_that(question: Answerable[T], matcher: Any) -> Expectation:
    """Factory for creating Expectations from Questions and matchers."""
    return Expectation(question, matcher)

class Actor:
    """A user persona who can perform tasks and ask questions."""

    def __init__(self, name: str) -> None:
        self.name = name
        self._abilities: dict[type, Ability] = {}

    def who_can(self, *abilities: Ability) -> "Actor":
        """Grant abilities to this actor."""
        for ability in abilities:
            self._abilities[type(ability)] = ability
        return self

    def ability_to(self, ability_type: type[T]) -> T:
        """Retrieve a specific ability by type."""
        if ability_type not in self._abilities:
            raise RuntimeError(
                f"{self.name} does not have the ability {ability_type.__name__}"
            )
        return self._abilities[ability_type]

    def attempts_to(self, *tasks: Performable) -> None:
        """Perform a sequence of tasks."""
        for task in tasks:
            task.perform_as(self)

    def should(self, *expectations: Expectation) -> None:
        """Assert a sequence of expectations."""
        for expectation in expectations:
            expectation.evaluate(self)
```

---

## 3. Actor Definitions

The RING-5 application serves distinct user personas, each representing a different workflow
focus and expertise level. Actors are pre-configured with appropriate abilities.

### 3.1 DataAnalyst

The primary persona. A researcher who loads simulation data, applies transformations, builds
visualizations, and exports results. This actor exercises the full pipeline from data
ingestion through plot generation.

```python
# tests/e2e/actors/personas.py
from tests.e2e.abilities.browse_the_web import BrowseTheWeb
from tests.e2e.abilities.interact_with_streamlit import InteractWithStreamlit
from tests.e2e.abilities.access_file_system import AccessFileSystem

def create_data_analyst(playwright_page, base_url, test_data_dir) -> Actor:
    return (
        Actor("DataAnalyst")
        .who_can(
            BrowseTheWeb.using(playwright_page),
            InteractWithStreamlit.on(base_url),
            AccessFileSystem.at(test_data_dir),
        )
    )
```

**Primary workflows**: Load CSV -> Transform Data (Seeds Reducer, Outlier Remover,
Preprocessor, Mixer) -> Create Plots -> Configure Pipeline -> Finalize -> Export.

### 3.2 Researcher

A read-heavy persona who loads existing portfolios, explores data, and adjusts plot
configurations without performing destructive operations. Tests the "load and explore"
journey through the Summary and Data Visualization tabs.

```python
def create_researcher(playwright_page, base_url) -> Actor:
    return (
        Actor("Researcher")
        .who_can(
            BrowseTheWeb.using(playwright_page),
            InteractWithStreamlit.on(base_url),
        )
    )
```

**Primary workflows**: Load Portfolio -> Explore Data Managers (Summary tab, Data
Visualization tab with search/filter) -> Adjust Plot Config -> View Documentation.

### 3.3 PortfolioManager

A persona focused on session persistence: saving work, loading previous sessions, managing
portfolio files, and verifying state restoration integrity across the two-column layout
(Save column, Load column) and the Manage Saved Portfolios expander section.

```python
def create_portfolio_manager(playwright_page, base_url, portfolio_dir) -> Actor:
    return (
        Actor("PortfolioManager")
        .who_can(
            BrowseTheWeb.using(playwright_page),
            InteractWithStreamlit.on(base_url),
            AccessFileSystem.at(portfolio_dir),
        )
    )
```

**Primary workflows**: Save Portfolio -> List Portfolios -> Load Portfolio -> Verify State
Restoration -> Delete Portfolio.

### 3.4 PowerUser

An advanced persona exercising edge cases: complex multi-step pipelines with multiple shapers
(`Normalizer`, `Filter`, `Sorter`), reordering steps, large datasets, rapid navigation
between pages, concurrent operations, and error recovery paths.

```python
def create_power_user(playwright_page, base_url, test_data_dir) -> Actor:
    return (
        Actor("PowerUser")
        .who_can(
            BrowseTheWeb.using(playwright_page),
            InteractWithStreamlit.on(base_url),
            AccessFileSystem.at(test_data_dir),
        )
    )
```

**Primary workflows**: Complex Pipeline Chains -> Multiple Plots with Different Types ->
Cross-Page State Consistency -> Error Recovery -> Engine Switching (Plotly/Matplotlib).

---

## 4. Ability Objects Catalog

Abilities encapsulate the technical capabilities that actors use to interact with the system.
Each ability wraps a driver, client, or system interface behind a consistent protocol.

### 4.1 BrowseTheWeb

Wraps Playwright's `Page` object to provide browser automation capabilities. This is the
foundational ability for all web-based interactions.

```python
# tests/e2e/abilities/browse_the_web.py
from playwright.sync_api import Page

class BrowseTheWeb:
    """Ability to interact with web pages via Playwright."""

    def __init__(self, page: Page) -> None:
        self._page = page

    @classmethod
    def using(cls, page: Page) -> "BrowseTheWeb":
        return cls(page)

    @property
    def page(self) -> Page:
        return self._page

    def navigate_to(self, url: str) -> None:
        self._page.goto(url)

    def wait_for_streamlit(self, timeout: int = 10000) -> None:
        """Wait for Streamlit app to finish rerunning.

        Streamlit shows a status widget during rerun. We wait until it
        disappears, indicating the page has stabilized.
        """
        self._page.wait_for_function(
            "() => !document.querySelector('[data-testid=\"stStatusWidget\"]')",
            timeout=timeout,
        )

    def take_screenshot(self, name: str) -> bytes:
        """Capture a screenshot for living documentation."""
        return self._page.screenshot(full_page=True)
```

### 4.2 InteractWithStreamlit

A higher-level ability that understands Streamlit's widget rendering model. Provides
methods for interacting with Streamlit-specific components: `st.selectbox`, `st.button`,
`st.multiselect`, `st.segmented_control`, `st.tabs`, `st.pills`, `st.dataframe`,
`st.metric`, `st.toast`, `st.file_uploader`, and `st.dialog`.

```python
# tests/e2e/abilities/interact_with_streamlit.py
from playwright.sync_api import Page

class InteractWithStreamlit:
    """Ability to interact with Streamlit-specific widgets."""

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    @classmethod
    def on(cls, base_url: str) -> "InteractWithStreamlit":
        return cls(base_url)

    def click_sidebar_nav(self, page: Page, label: str) -> None:
        """Click a navigation button in the RING-5 sidebar.

        The sidebar uses st.button with type='primary' for active and
        type='tertiary' for inactive nav items.
        """
        sidebar = page.locator('[data-testid="stSidebar"]')
        sidebar.get_by_role("button", name=label).click()

    def click_button(self, page: Page, label: str) -> None:
        """Click a Streamlit button by its visible label text."""
        page.get_by_role("button", name=label).click()

    def select_from_selectbox(self, page: Page, label: str, value: str) -> None:
        """Select a value from a Streamlit st.selectbox widget."""
        selectbox = page.locator(f'[data-testid="stSelectbox"]:has-text("{label}")')
        selectbox.click()
        page.get_by_role("option", name=value).click()

    def select_tab(self, page: Page, label: str) -> None:
        """Click a tab in a Streamlit st.tabs group.

        Used extensively on the Data Managers page which has 7 tabs:
        Summary, Data Visualization, Seeds Reducer, Outlier Remover,
        Preprocessor, Mixer, Operations History.
        """
        page.locator(f'[data-testid="stTab"]:has-text("{label}")').click()

    def select_segmented_control(self, page: Page, label: str, value: str) -> None:
        """Select an option in a Streamlit st.segmented_control.

        Used on Data Source page (data source choice) and Mixer (mode).
        """
        control = page.locator(
            f'[data-testid="stSegmentedControl"]:has-text("{label}")'
        )
        control.get_by_role("button", name=value).click()

    def get_metric_value(self, page: Page, label: str) -> str:
        """Read the value from a Streamlit st.metric widget.

        Metrics are used throughout: Rows/Columns/Source on the header,
        Original Rows/Reduced Rows on Seeds Reducer, etc.
        """
        metric = page.locator(f'[data-testid="stMetric"]:has-text("{label}")')
        return metric.locator('[data-testid="stMetricValue"]').inner_text()

    def get_dataframe_row_count(self, page: Page) -> int:
        """Count visible rows in a Streamlit st.dataframe widget."""
        df = page.locator('[data-testid="stDataFrame"]').first
        rows = df.locator("tr[data-testid]")
        return rows.count()

    def wait_for_toast(self, page: Page, text: str, timeout: int = 5000) -> None:
        """Wait for a Streamlit st.toast notification containing text."""
        page.locator(f'[data-testid="stToast"]:has-text("{text}")').wait_for(
            timeout=timeout
        )

    def upload_file(self, page: Page, label: str, file_path: str) -> None:
        """Upload a file to a Streamlit st.file_uploader widget."""
        uploader = page.locator(
            f'[data-testid="stFileUploader"]:has-text("{label}")'
        )
        uploader.locator("input[type='file']").set_input_files(file_path)

    def fill_text_input(self, page: Page, label: str, value: str) -> None:
        """Fill a Streamlit st.text_input widget."""
        input_widget = page.locator(
            f'[data-testid="stTextInput"]:has-text("{label}")'
        )
        input_widget.locator("input").fill(value)

    def select_multiselect(
        self, page: Page, label: str, values: list[str]
    ) -> None:
        """Select multiple values in a Streamlit st.multiselect widget."""
        ms = page.locator(f'[data-testid="stMultiSelect"]:has-text("{label}")')
        ms_input = ms.locator("input")
        for val in values:
            ms_input.fill(val)
            page.locator(f'[role="option"]:has-text("{val}")').click()
```

### 4.3 AccessFileSystem

Provides the ability to create test fixture files, manage temporary directories, and verify
downloaded files. Essential for data ingestion and export testing.

```python
# tests/e2e/abilities/access_file_system.py
from pathlib import Path
import pandas as pd

class AccessFileSystem:
    """Ability to interact with the local filesystem for test fixtures."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    @classmethod
    def at(cls, base_dir: Path) -> "AccessFileSystem":
        return cls(base_dir)

    def fixture_path(self, filename: str) -> Path:
        """Return the path to a test fixture file."""
        return self._base_dir / filename

    def create_temp_csv(self, data: pd.DataFrame, name: str = "test.csv") -> Path:
        """Create a temporary CSV file from a DataFrame."""
        path = self._base_dir / name
        data.to_csv(path, index=False)
        return path

    def verify_download(self, download_dir: Path, pattern: str) -> Path | None:
        """Verify a file was downloaded matching a glob pattern."""
        matches = list(download_dir.glob(pattern))
        return matches[0] if matches else None

    def read_csv(self, path: Path) -> pd.DataFrame:
        """Read a CSV file into a DataFrame."""
        return pd.read_csv(path)
```

### 4.4 ManageTestState

An internal ability for test orchestration: seeding the Streamlit session state, injecting
data directly via the `ApplicationAPI` for setup phases, and clearing state between tests.
This ability enables Given-step shortcuts that bypass the UI for faster test setup.

```python
# tests/e2e/abilities/manage_test_state.py
from src.core.application_api import ApplicationAPI
import pandas as pd

class ManageTestState:
    """Ability to directly manipulate application state for test setup.

    Used in Given steps to pre-seed data without going through the UI,
    dramatically reducing test execution time for scenarios that focus
    on transformation or visualization behavior.
    """

    def __init__(self, api: ApplicationAPI) -> None:
        self._api = api

    @classmethod
    def with_api(cls, api: ApplicationAPI) -> "ManageTestState":
        return cls(api)

    def seed_data(self, data: pd.DataFrame) -> None:
        """Inject a DataFrame directly into session state."""
        self._api.state_manager.set_data(data)

    def seed_plots(self, plots: list) -> None:
        """Inject plots directly into session state."""
        for plot in plots:
            self._api.state_manager.get_plots().append(plot)

    def seed_portfolio(self, name: str, data: pd.DataFrame) -> None:
        """Save a portfolio directly via the data services layer."""
        self._api.data_services.save_portfolio(
            name=name,
            data=data,
            plots=[],
            config={},
            plot_counter=0,
            csv_path=None,
            parse_variables=None,
            figure_spec_enricher=lambda c, t: None,
        )

    def reset(self) -> None:
        """Reset the entire application session."""
        self._api.reset_session()
```

---

## 5. Task Objects Catalog (Per Page)

Tasks are the primary building blocks of test scenarios. Each task represents a meaningful
user action and is composed of lower-level interactions. Tasks implement the `Performable`
protocol with a `perform_as(actor)` method.

### 5.1 Navigation Tasks

These tasks handle cross-page navigation via the RING-5 sidebar, which uses `st.button`
elements for the five navigation items plus "Clear Data" and "Reset All" controls.

```python
# tests/e2e/tasks/navigation.py
from dataclasses import dataclass
from tests.e2e.actors.actor import Actor, Performable
from tests.e2e.abilities.browse_the_web import BrowseTheWeb
from tests.e2e.abilities.interact_with_streamlit import InteractWithStreamlit

@dataclass
class NavigateTo:
    """Navigate to a specific page via the sidebar.

    Valid page names: 'Data Source', 'Data Managers', 'Manage Plots',
    'Save/Load Portfolio', 'Documentation'.
    """
    page_name: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.click_sidebar_nav(page, self.page_name)
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ClearAllData:
    """Click the 'Clear Data' sidebar button to reset loaded data and plots."""

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.click_sidebar_nav(page, "Clear Data")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ResetApplication:
    """Click the 'Reset All' sidebar button to restore full defaults."""

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.click_sidebar_nav(page, "Reset All")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()
```

### 5.2 Data Source Page Tasks

These tasks correspond to the three data source modes exposed by `DataSourcePage.render()`:
parser configuration, CSV upload, and recent file loading.

```python
# tests/e2e/tasks/data_source/load_csv.py
@dataclass
class SelectDataSourceMode:
    """Select the data source input method via st.segmented_control.

    Modes map to the data_source_options list in DataSourcePage.render():
    - 'Parse {sim} Stats Files' (dynamic label based on simulator)
    - 'I already have CSV data'
    - 'Load from Recent'
    """
    mode: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.select_segmented_control(page, "Select your data source:", self.mode)
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class LoadCSVFromPool:
    """Load a CSV file from the recent files pool (CSV pool).

    Corresponds to the DataSourceComponents.render_csv_pool() flow
    which iterates csv_pool entries and renders file_info_card() for each.
    """
    file_index: int = 0

    def perform_as(self, actor: Actor) -> None:
        SelectDataSourceMode("Load from Recent").perform_as(actor)
        page = actor.ability_to(BrowseTheWeb).page
        load_buttons = page.locator('button:has-text("Load")').all()
        if self.file_index < len(load_buttons):
            load_buttons[self.file_index].click()
            actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ConfigureParser:
    """Configure the stats parser with path, pattern, and strategy.

    Maps to the fragment _parser_config_fragment() in
    DataSourceComponents.render_parser_config() which renders:
    - stats_path text_input
    - stats_pattern text_input
    - parser_strategy segmented_control
    - simulator_selector pills
    """
    stats_path: str
    stats_pattern: str = "stats.txt"
    strategy: str | None = None

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        SelectDataSourceMode("Parse gem5 Stats Files").perform_as(actor)
        streamlit.fill_text_input(page, "Stats directory path", self.stats_path)
        streamlit.fill_text_input(page, "File pattern", self.stats_pattern)
        if self.strategy:
            streamlit.select_segmented_control(
                page, "Select ingestion strategy:", self.strategy
            )
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class SelectSimulator:
    """Select the simulator backend via st.pills navigation.

    Corresponds to the simulator_selector pills widget in
    DataSourceComponents.render_parser_config().
    """
    simulator_name: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        page.locator(
            f'[data-testid="stPills"] button:has-text("{self.simulator_name}")'
        ).click()
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ScanForVariables:
    """Trigger a quick/deep scan for available variables.

    Maps to the scan button flow in _parser_config_fragment() which
    calls api.submit_scan_async() and iterates as_completed futures.
    """
    deep_scan: bool = False

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        if self.deep_scan:
            page.locator('label:has-text("Deep Scan")').click()
        page.locator('button:has-text("Quick Scan")').click()
        page.locator(
            '[data-testid="stStatus"]:has-text("complete")'
        ).wait_for(timeout=30000)

@dataclass
class AddVariable:
    """Add a variable through the st.dialog Add Variable dialog.

    Maps to DataSourceComponents.variable_config_dialog() which
    presents method selection (Search Scanned / Manual Entry),
    type-specific config forms, and the 'Add to Configuration' button.
    """
    name: str
    var_type: str = "scalar"
    method: str = "Manual Entry"

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.click_button(page, "Add Variable")
        page.locator('[data-testid="stDialog"]').wait_for()
        page.locator(
            f'[data-testid="stPills"] button:has-text("{self.method}")'
        ).click()
        if self.method == "Manual Entry":
            streamlit.fill_text_input(page, "Variable Name", self.name)
            streamlit.select_from_selectbox(page, "Type", self.var_type)
        streamlit.click_button(page, "Add to Configuration")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ParseStatsFiles:
    """Click the Parse button and wait for dialog completion.

    Maps to the parse button outside _parser_config_fragment() and the
    _show_parse_dialog() which shows progress and a 'Close & Reload' button.
    """

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        page.locator('button:has-text("Parse")').click()
        page.locator('[data-testid="stDialog"]').wait_for()
        page.locator('text="Done!"').wait_for(timeout=60000)
        page.locator('button:has-text("Close & Reload")').click()
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()
```

### 5.3 Data Managers Page Tasks

These tasks correspond to the seven-tab layout in `show_data_managers_page()`:
Summary, Data Visualization, Seeds Reducer, Outlier Remover, Preprocessor, Mixer,
and Operations History.

```python
# tests/e2e/tasks/data_managers/transformations.py
@dataclass
class SwitchToTab:
    """Switch to a specific tab on the Data Managers page."""
    tab_name: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.select_tab(page, self.tab_name)
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ApplySeedsReduction:
    """Configure and apply the Seeds Reducer transformation.

    Maps to SeedsReducerManager.render() which provides:
    - Column to reduce over (selectbox, defaults to random_seed)
    - Categorical columns for grouping (multiselect)
    - Numeric columns for statistics (multiselect)
    - Apply -> Preview -> Confirm two-step flow
    """
    reduce_column: str = "random_seed"

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        SwitchToTab("Seeds Reducer").perform_as(actor)
        streamlit.select_from_selectbox(
            page, "Column to reduce over", self.reduce_column
        )
        streamlit.click_button(page, "Apply Seeds Reducer")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()
        streamlit.click_button(page, "Confirm and Apply Seeds Reducer")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ApplyOutlierRemoval:
    """Configure and apply the Outlier Remover.

    Maps to OutlierRemoverManager.render() which filters rows where
    the target column exceeds Q3 within each group.
    """
    outlier_column: str
    group_by_cols: list[str] | None = None

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        SwitchToTab("Outlier Remover").perform_as(actor)
        streamlit.select_from_selectbox(
            page, "Column to check for outliers", self.outlier_column
        )
        streamlit.click_button(page, "Apply Outlier Remover")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()
        streamlit.click_button(page, "Confirm and Apply Outlier Remover")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ApplyPreprocessor:
    """Create a new computed column using the Preprocessor.

    Maps to PreprocessorManager.render() which supports Division,
    Sum, Subtraction, and Multiplication between two source columns.
    """
    source_col_1: str
    operation: str
    source_col_2: str
    new_column_name: str | None = None

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        SwitchToTab("Preprocessor").perform_as(actor)
        streamlit.select_from_selectbox(page, "Source Column 1", self.source_col_1)
        streamlit.select_from_selectbox(page, "Operation", self.operation)
        streamlit.select_from_selectbox(page, "Source Column 2", self.source_col_2)
        if self.new_column_name:
            streamlit.fill_text_input(page, "New column name", self.new_column_name)
        streamlit.click_button(page, "Preview Result")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()
        streamlit.click_button(page, "Confirm and Add Column to Dataset")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ApplyMixer:
    """Merge multiple columns using the Mixer.

    Maps to MixerManager.render() which supports two modes:
    - Numerical Operations (Sum, Mean) with SD propagation
    - Configuration Merge (Concatenate) for string columns
    """
    columns: list[str]
    operation: str = "Sum"
    new_column_name: str = "merged"
    mode: str = "Numerical Operations"

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        SwitchToTab("Mixer").perform_as(actor)
        streamlit.select_segmented_control(page, "Mixer Mode", self.mode)
        streamlit.select_multiselect(
            page, "Select columns to merge", self.columns
        )
        streamlit.select_from_selectbox(page, "Operation", self.operation)
        streamlit.fill_text_input(page, "New Column Name", self.new_column_name)
        streamlit.click_button(page, "Preview Merge")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()
        streamlit.click_button(page, "Confirm and Merge")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class SearchDataVisualization:
    """Search and filter data in the Data Visualization tab.

    Maps to DataManagerComponents.render_visualization_tab() which
    provides column-scoped text search and display filtering.
    """
    search_column: str = "All Columns"
    search_term: str = ""

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        SwitchToTab("Data Visualization").perform_as(actor)
        streamlit.select_from_selectbox(
            page, "Search in column", self.search_column
        )
        streamlit.fill_text_input(page, "Search term", self.search_term)
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()
```

### 5.4 Manage Plots Page Tasks

These tasks map to the three controllers composed in `show_manage_plots_page()`:
`PlotCreationController` (create/select/rename/delete/duplicate),
`PipelineController` (shaper pipeline editing), and
`PlotRenderController` (configuration + figure generation + display).

```python
# tests/e2e/tasks/manage_plots/plot_lifecycle.py
@dataclass
class CreatePlot:
    """Create a new plot with name and type.

    Maps to PlotCreationController.render_create_section() which
    delegates to PlotCreationComponent.render().
    """
    name: str = "Plot 1"
    plot_type: str = "bar"

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.fill_text_input(page, "Plot Name", self.name)
        streamlit.select_from_selectbox(page, "Plot Type", self.plot_type)
        streamlit.click_button(page, "Create Plot")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class SelectPlot:
    """Select an existing plot from the selector dropdown.

    Maps to PlotCreationController.render_selector() which delegates
    to PlotSelectorComponent.render().
    """
    plot_name: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.select_from_selectbox(page, "Select Plot", self.plot_name)
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class RenamePlot:
    """Rename the currently selected plot.

    Maps to PlotCreationController.render_controls() which delegates
    to PlotControlsComponent.render() and reads the new_name field.
    """
    new_name: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.fill_text_input(page, "Rename", self.new_name)
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class DeleteCurrentPlot:
    """Delete the currently selected plot."""

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.click_button(page, "Delete")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class DuplicateCurrentPlot:
    """Duplicate the currently selected plot."""

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.click_button(page, "Duplicate")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class AddShaperToPipeline:
    """Add a shaper step to the current plot's pipeline.

    Maps to PipelineController.render() which delegates the 'Add
    transformation' selector to PipelineComponent.render_add_shaper().
    """
    shaper_type: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.select_from_selectbox(
            page, "Add transformation", self.shaper_type
        )
        streamlit.click_button(page, "Add")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class FinalizePipeline:
    """Apply the complete pipeline to raw data.

    Maps to PipelineComponent.render_finalize_button() and
    PipelineController._handle_finalize().
    """

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.click_button(page, "Finalize")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ChangePlotType:
    """Change the plot type via the visualization config.

    Maps to PlotRenderController.render() which shows a Plot Type
    selectbox and triggers lifecycle.change_plot_type() on change.
    """
    new_type: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.select_from_selectbox(page, "Plot Type", self.new_type)
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class ToggleAdvancedSettings:
    """Toggle the advanced settings panel.

    Maps to the st.toggle 'Show advanced settings' in
    PlotRenderController.render().
    """

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        page.locator('label:has-text("Show advanced settings")').click()
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class SwitchRenderingEngine:
    """Switch between Plotly and Matplotlib engines.

    Maps to ChartDisplayComponent.render_engine_selector() which
    renders st.pills for engine selection.
    """
    engine: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        page.locator(
            f'[data-testid="stPills"] button:has-text("{self.engine}")'
        ).click()
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()
```

### 5.5 Portfolio Page Tasks

These tasks map to the `_portfolio_fragment()` function in `portfolio.py` which renders
the two-column Save/Load layout and the Manage Saved Portfolios expander section.

```python
# tests/e2e/tasks/portfolio/portfolio_management.py
@dataclass
class SavePortfolio:
    """Save the current session as a portfolio.

    Maps to the Save Portfolio column in _portfolio_fragment() which
    calls api.data_services.save_portfolio() with all session state.
    """
    name: str = "my_portfolio"

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.fill_text_input(page, "Portfolio Name", self.name)
        streamlit.click_button(page, "Save Portfolio")
        streamlit.wait_for_toast(page, "Portfolio saved")

@dataclass
class LoadPortfolio:
    """Load a previously saved portfolio.

    Maps to the Load Portfolio column which calls
    api.data_services.load_portfolio() and api.state_manager.restore_session().
    """
    portfolio_name: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        streamlit.select_from_selectbox(
            page, "Select Portfolio", self.portfolio_name
        )
        streamlit.click_button(page, "Load Portfolio")
        streamlit.wait_for_toast(page, "Portfolio loaded")
        actor.ability_to(BrowseTheWeb).wait_for_streamlit()

@dataclass
class DeletePortfolio:
    """Delete a saved portfolio from the management section.

    Maps to the expander/delete button flow in _portfolio_fragment()
    which iterates portfolios and renders delete buttons per item.
    """
    portfolio_name: str

    def perform_as(self, actor: Actor) -> None:
        page = actor.ability_to(BrowseTheWeb).page
        streamlit = actor.ability_to(InteractWithStreamlit)
        page.locator(
            f'[data-testid="stExpander"]:has-text("{self.portfolio_name}")'
        ).click()
        streamlit.click_button(page, "Delete")
        streamlit.wait_for_toast(page, f"Deleted {self.portfolio_name}")
```

---

## 6. Question Objects Catalog (Per Page)

Question objects encapsulate assertions about observable system state. Each Question
implements `answered_by(actor) -> T` and returns a concrete value for matchers to evaluate.

### 6.1 Navigation Questions

```python
# tests/e2e/questions/navigation.py
class TheCurrentPage:
    """Questions about navigation state."""

    @staticmethod
    def title() -> "Answerable[str]":
        """Return the current page heading text (the h2 element)."""
        class _PageTitle:
            def answered_by(self, actor: Actor) -> str:
                page = actor.ability_to(BrowseTheWeb).page
                return page.locator("h2").first.inner_text()
        return _PageTitle()

    @staticmethod
    def is_displayed(page_name: str) -> "Answerable[bool]":
        """Check if a specific page is active in sidebar navigation.

        Active pages use type='primary' buttons in the sidebar.
        """
        class _PageDisplayed:
            def answered_by(self, actor: Actor) -> bool:
                page = actor.ability_to(BrowseTheWeb).page
                active = page.locator(
                    f'[data-testid="stSidebar"] '
                    f'button[kind="primary"]:has-text("{page_name}")'
                )
                return active.is_visible()
        return _PageDisplayed()
```

### 6.2 Data Table Questions

```python
# tests/e2e/questions/data_table.py
class TheDataTable:
    """Questions about data display and metrics across pages."""

    @staticmethod
    def row_count() -> "Answerable[int]":
        """Return the row count from the Rows metric widget."""
        class _RowCount:
            def answered_by(self, actor: Actor) -> int:
                page = actor.ability_to(BrowseTheWeb).page
                streamlit = actor.ability_to(InteractWithStreamlit)
                value = streamlit.get_metric_value(page, "Rows")
                return int(value.replace(",", ""))
        return _RowCount()

    @staticmethod
    def column_count() -> "Answerable[int]":
        """Return the column count from the Columns metric widget."""
        class _ColumnCount:
            def answered_by(self, actor: Actor) -> int:
                page = actor.ability_to(BrowseTheWeb).page
                streamlit = actor.ability_to(InteractWithStreamlit)
                value = streamlit.get_metric_value(page, "Columns")
                return int(value.replace(",", ""))
        return _ColumnCount()

    @staticmethod
    def has_column(column_name: str) -> "Answerable[bool]":
        """Check if a column header is visible in the displayed dataframe."""
        class _HasColumn:
            def answered_by(self, actor: Actor) -> bool:
                page = actor.ability_to(BrowseTheWeb).page
                df = page.locator('[data-testid="stDataFrame"]').first
                return df.locator(f'text="{column_name}"').is_visible()
        return _HasColumn()

    @staticmethod
    def source_name() -> "Answerable[str]":
        """Return the data source name from the Source metric."""
        class _SourceName:
            def answered_by(self, actor: Actor) -> str:
                page = actor.ability_to(BrowseTheWeb).page
                streamlit = actor.ability_to(InteractWithStreamlit)
                return streamlit.get_metric_value(page, "Source")
        return _SourceName()

    @staticmethod
    def memory_usage() -> "Answerable[str]":
        """Return the memory usage from the Memory metric."""
        class _MemoryUsage:
            def answered_by(self, actor: Actor) -> str:
                page = actor.ability_to(BrowseTheWeb).page
                streamlit = actor.ability_to(InteractWithStreamlit)
                return streamlit.get_metric_value(page, "Memory")
        return _MemoryUsage()

    @staticmethod
    def missing_values_count() -> "Answerable[int]":
        """Return the missing values count from the metric."""
        class _MissingValues:
            def answered_by(self, actor: Actor) -> int:
                page = actor.ability_to(BrowseTheWeb).page
                streamlit = actor.ability_to(InteractWithStreamlit)
                value = streamlit.get_metric_value(page, "Missing Values")
                return int(value.replace(",", ""))
        return _MissingValues()
```

### 6.3 Plot Display Questions

```python
# tests/e2e/questions/plot_display.py
class ThePlot:
    """Questions about rendered plot visualizations."""

    @staticmethod
    def is_visible() -> "Answerable[bool]":
        """Check if a Plotly or Matplotlib chart is visible."""
        class _PlotVisible:
            def answered_by(self, actor: Actor) -> bool:
                page = actor.ability_to(BrowseTheWeb).page
                plotly = page.locator('[data-testid="stPlotlyChart"]')
                matplotlib = page.locator('[data-testid="stImage"]')
                return plotly.is_visible() or matplotlib.is_visible()
        return _PlotVisible()

    @staticmethod
    def has_legend() -> "Answerable[bool]":
        """Check if the plot contains a visible legend element."""
        class _HasLegend:
            def answered_by(self, actor: Actor) -> bool:
                page = actor.ability_to(BrowseTheWeb).page
                return page.locator(".legend").is_visible()
        return _HasLegend()

    @staticmethod
    def current_type() -> "Answerable[str]":
        """Return the selected plot type from the Plot Type selectbox."""
        class _PlotType:
            def answered_by(self, actor: Actor) -> str:
                page = actor.ability_to(BrowseTheWeb).page
                sb = page.locator(
                    '[data-testid="stSelectbox"]:has-text("Plot Type")'
                )
                return sb.locator(
                    '[data-testid="stSelectboxValue"]'
                ).inner_text()
        return _PlotType()

    @staticmethod
    def pipeline_step_count() -> "Answerable[int]":
        """Return the number of shaper steps in the pipeline editor."""
        class _StepCount:
            def answered_by(self, actor: Actor) -> int:
                page = actor.ability_to(BrowseTheWeb).page
                steps = page.locator(
                    '[data-testid="stExpander"]:has-text("Step")'
                )
                return steps.count()
        return _StepCount()

    @staticmethod
    def rendering_engine() -> "Answerable[str]":
        """Return the currently active rendering engine name."""
        class _Engine:
            def answered_by(self, actor: Actor) -> str:
                page = actor.ability_to(BrowseTheWeb).page
                active = page.locator(
                    '[data-testid="stPills"] button[aria-pressed="true"]'
                )
                return active.inner_text()
        return _Engine()

class ThePlotSelector:
    """Questions about the plot selector widget."""

    @staticmethod
    def available_plots() -> "Answerable[list[str]]":
        """Return the list of plot names in the selector dropdown."""
        class _AvailablePlots:
            def answered_by(self, actor: Actor) -> list[str]:
                page = actor.ability_to(BrowseTheWeb).page
                selectbox = page.locator('[data-testid="stSelectbox"]').first
                selectbox.click()
                options = page.locator('[role="option"]').all()
                names = [opt.inner_text() for opt in options]
                page.keyboard.press("Escape")
                return names
        return _AvailablePlots()

    @staticmethod
    def selected_plot_name() -> "Answerable[str]":
        """Return the name of the currently selected plot."""
        class _SelectedName:
            def answered_by(self, actor: Actor) -> str:
                page = actor.ability_to(BrowseTheWeb).page
                return page.locator(
                    '[data-testid="stSelectbox"] '
                    '[data-testid="stSelectboxValue"]'
                ).first.inner_text()
        return _SelectedName()
```

### 6.4 Portfolio Questions

```python
# tests/e2e/questions/portfolio.py
class ThePortfolio:
    """Questions about portfolio management state."""

    @staticmethod
    def saved_portfolio_names() -> "Answerable[list[str]]":
        """Return names of saved portfolios in the management section."""
        class _SavedNames:
            def answered_by(self, actor: Actor) -> list[str]:
                page = actor.ability_to(BrowseTheWeb).page
                expanders = page.locator(
                    '[data-testid="stExpander"]'
                ).all()
                return [e.locator("summary").inner_text() for e in expanders]
        return _SavedNames()

    @staticmethod
    def has_portfolio(name: str) -> "Answerable[bool]":
        """Check if a portfolio with the given name exists."""
        class _HasPortfolio:
            def answered_by(self, actor: Actor) -> bool:
                page = actor.ability_to(BrowseTheWeb).page
                expander = page.locator(
                    f'[data-testid="stExpander"]:has-text("{name}")'
                )
                return expander.is_visible()
        return _HasPortfolio()

    @staticmethod
    def load_dropdown_options() -> "Answerable[list[str]]":
        """Return portfolio names available in the load dropdown."""
        class _LoadOptions:
            def answered_by(self, actor: Actor) -> list[str]:
                page = actor.ability_to(BrowseTheWeb).page
                selectbox = page.locator(
                    '[data-testid="stSelectbox"]:has-text("Select Portfolio")'
                )
                selectbox.click()
                options = page.locator('[role="option"]').all()
                names = [o.inner_text() for o in options]
                page.keyboard.press("Escape")
                return names
        return _LoadOptions()

    @staticmethod
    def no_portfolios_warning_shown() -> "Answerable[bool]":
        """Check if the 'No portfolios found' warning is displayed."""
        class _NoPortfoliosWarning:
            def answered_by(self, actor: Actor) -> bool:
                page = actor.ability_to(BrowseTheWeb).page
                warning = page.locator(
                    '[data-testid="stWarning"]:has-text("No portfolios found")'
                )
                return warning.is_visible()
        return _NoPortfoliosWarning()
```

---

## 7. Feature Files (Gherkin) for Data Source Page

The Data Source page provides three data ingestion modes managed by `DataSourcePage.render()`:
parser-based ingestion (via `DataSourceComponents.render_parser_config()`), CSV upload mode,
and loading from the recent CSV pool (via `DataSourceComponents.render_csv_pool()`).

```gherkin
# tests/e2e/features/data_source.feature
Feature: Data Source Management
  As a DataAnalyst
  I want to load simulation data from various sources
  So that I can analyze gem5 output in the RING-5 platform

  Background:
    Given the RING-5 application is running
    And I am on the "Data Source" page

  # --- CSV Pool Loading ---

  Scenario: Load CSV from recent files pool
    Given the CSV pool contains at least one file
    When I select "Load from Recent" as the data source
    And I click "Load" on the first CSV file
    Then the data should be loaded into the session
    And the Rows metric should show a positive number
    And the Columns metric should show a positive number
    And the Source metric should display the filename

  Scenario: Preview CSV file before loading
    Given the CSV pool contains at least one file
    When I select "Load from Recent" as the data source
    And I click "Preview" on the first CSV file
    Then a dataframe preview should be displayed with 5 rows

  Scenario: Delete CSV from pool
    Given the CSV pool contains at least one file
    When I select "Load from Recent" as the data source
    And I click "Delete" on the first CSV file
    Then a toast notification should confirm the deletion
    And the file should no longer appear in the pool

  Scenario: Empty CSV pool shows warning
    Given the CSV pool is empty
    When I select "Load from Recent" as the data source
    Then a warning message about no CSV files should be displayed

  # --- Parser Configuration ---

  Scenario: Configure and run stats parser
    Given I have gem5 stats files at "/test/data/stats"
    When I select "Parse gem5 Stats Files" as the data source
    And I set the stats directory to "/test/data/stats"
    And I set the file pattern to "stats.txt"
    And I add a scalar variable "simTicks"
    And I click the Parse button
    Then the parsing dialog should show progress
    And the parsing should complete successfully
    And data should be loaded with the parsed results

  Scenario: Switch simulator backend
    When I select "Parse gem5 Stats Files" as the data source
    And I select the "sniper" simulator backend
    Then the parser configuration should update for Sniper
    And the parse button label should reflect the Sniper simulator

  Scenario: Quick scan discovers variables
    Given I have gem5 stats files at "/test/data/stats"
    When I select "Parse gem5 Stats Files" as the data source
    And I set the stats directory to "/test/data/stats"
    And I trigger a Quick Scan
    Then the scan should complete with discovered variables
    And a success message should show the variable count

  Scenario: Deep scan checks all files
    Given I have gem5 stats files at "/test/data/stats"
    When I enable "Deep Scan"
    And I trigger a Quick Scan
    Then the scan status should show scanning all files
    And the scan should complete with discovered variables

  Scenario: Add variable manually
    When I select "Parse gem5 Stats Files" as the data source
    And I open the Add Variable dialog
    And I select "Manual Entry" as the method
    And I enter "simTicks" as the variable name
    And I select "scalar" as the variable type
    And I click "Add to Configuration"
    Then the variable should appear in the configuration list

  Scenario: Add variable from scan results
    Given a Quick Scan has been completed with results
    When I open the Add Variable dialog
    And I select "Search Scanned Variables" as the method
    And I search for "simTicks"
    And I select the matching variable
    And I click "Add to Configuration"
    Then the variable should appear in the configuration list

  Scenario: Prevent duplicate variable names
    Given the variable "simTicks" is already in the configuration
    When I attempt to add another variable named "simTicks"
    Then a warning about duplicate names should be displayed

  Scenario: Change parsing strategy
    When I select "Parse gem5 Stats Files" as the data source
    And I change the ingestion strategy
    Then the strategy selection should update
    And the configuration preview should reflect the new strategy

  # --- CSV Upload Mode ---

  Scenario: Select CSV upload mode
    When I select "I already have CSV data" as the data source
    Then a success message should confirm CSV mode is active
```

---

## 8. Feature Files (Gherkin) for Data Managers Page

The Data Managers page organizes transformations across seven tabs managed by
`show_data_managers_page()`, with four sub-managers (`SeedsReducerManager`,
`OutlierRemoverManager`, `PreprocessorManager`, `MixerManager`) each following
a preview-then-confirm workflow pattern.

```gherkin
# tests/e2e/features/data_managers.feature
Feature: Data Managers and Transformations
  As a DataAnalyst
  I want to transform and clean my loaded data
  So that I can prepare it for meaningful visualization

  Background:
    Given the RING-5 application is running
    And simulation data with multiple seeds is loaded
    And I am on the "Data Managers" page

  # --- Summary Tab ---

  Scenario: View dataset summary
    When I switch to the "Summary" tab
    Then I should see the Rows metric with the correct count
    And I should see the Columns metric with the correct count
    And I should see the Memory usage metric
    And I should see the Missing Values metric
    And a data preview with up to 20 rows should be displayed
    And numeric column statistics should be displayed
    And categorical column summaries should be displayed

  # --- Data Visualization Tab ---

  Scenario: Search data across all columns
    When I switch to the "Data Visualization" tab
    And I search for "benchmark_alpha" in "All Columns"
    Then the filtered data should show only matching rows
    And an info message should report the match count

  Scenario: Search data in a specific column
    When I switch to the "Data Visualization" tab
    And I search for "100" in column "simTicks"
    Then the filtered data should show rows where simTicks contains "100"

  Scenario: Paginate through large datasets
    When I switch to the "Data Visualization" tab
    And I set rows per page to 20
    And I navigate to page 2
    Then rows 21 through 40 should be displayed
    And the page indicator should show "Page 2"

  Scenario: Select specific columns for display
    When I switch to the "Data Visualization" tab
    And I select columns "simTicks" and "benchmark" for display
    Then only those two columns should appear in the data table

  Scenario: Download filtered data as CSV
    When I switch to the "Data Visualization" tab
    And I apply a search filter
    And I click "Download Current View as CSV"
    Then a CSV download should be initiated with the filtered data

  # --- Seeds Reducer Tab ---

  Scenario: Apply seeds reduction with default settings
    When I switch to the "Seeds Reducer" tab
    And the reduction column defaults to "random_seed"
    And I click "Apply Seeds Reducer"
    Then a preview should show reduced row count
    And a confirmation button should appear
    When I click "Confirm and Apply Seeds Reducer"
    Then the active data should be updated with reduced rows
    And a toast notification should confirm the operation
    And .sd columns should be created for numeric columns

  Scenario: Seeds reducer with custom column selection
    When I switch to the "Seeds Reducer" tab
    And I select "iteration" as the column to reduce over
    And I select specific categorical columns for grouping
    And I select specific numeric columns for statistics
    And I click "Apply Seeds Reducer"
    Then the preview should reflect the custom configuration

  Scenario: Seeds reducer records operation in history
    When I apply the Seeds Reducer successfully
    And I switch to the "Operations History" tab
    Then the history should contain a "Seeds Reduction" entry

  # --- Outlier Remover Tab ---

  Scenario: Remove outliers from a numeric column
    When I switch to the "Outlier Remover" tab
    And I select "simTicks" as the column to check for outliers
    And I click "Apply Outlier Remover"
    Then a preview should show the number of removed rows
    And the removal percentage should be displayed
    And original, filtered, and removed row counts should be shown
    When I click "Confirm and Apply Outlier Remover"
    Then the active data should exclude the outlier rows
    And a toast notification should confirm the operation

  Scenario: Outlier remover shows current distribution
    When I switch to the "Outlier Remover" tab
    And I select "simTicks" as the column to check for outliers
    Then the Min, Q3, Max, and Mean metrics should be displayed

  Scenario: Outlier remover with custom grouping
    When I switch to the "Outlier Remover" tab
    And I select grouping columns excluding seed-like columns
    And I apply the outlier remover
    Then outliers should be removed within each group independently

  # --- Preprocessor Tab ---

  Scenario: Create a derived column using division
    When I switch to the "Preprocessor" tab
    And I select "instructions" as Source Column 1
    And I select "Division" as the Operation
    And I select "cycles" as Source Column 2
    Then the default column name should be "instructions_per_cycles"
    When I click "Preview Result"
    Then the preview should show the new column with computed values
    And column statistics should be displayed
    When I click "Confirm and Add Column to Dataset"
    Then "instructions_per_cycles" should appear in the active dataset

  Scenario: Create a summed column
    When I switch to the "Preprocessor" tab
    And I select "user_time" as Source Column 1
    And I select "Sum" as the Operation
    And I select "system_time" as Source Column 2
    And I set the new column name to "total_time"
    And I click "Preview Result"
    Then the preview should show "total_time" with summed values

  Scenario: Custom column name overrides default
    When I provide a custom name "IPC" for the new column
    And I complete the preprocessor operation
    Then the column should be named "IPC" in the dataset

  # --- Mixer Tab ---

  Scenario: Sum multiple numeric columns
    When I switch to the "Mixer" tab
    And I select "Numerical Operations" as the mixer mode
    And I select columns "col_a" and "col_b" to merge
    And I select "Sum" as the operation
    And I set the new column name to "total_ab"
    And I click "Preview Merge"
    Then the preview should show "total_ab" with summed values
    When I click "Confirm and Merge"
    Then "total_ab" should be added to the active dataset

  Scenario: Mixer propagates standard deviation
    Given the data contains ".sd" columns from a previous seeds reduction
    When I switch to the "Mixer" tab
    And I sum columns that have associated ".sd" columns
    Then the merged result should include a propagated ".sd" column
    And the SD should be calculated as sqrt(sd1^2 + sd2^2)

  Scenario: Concatenate configuration columns
    When I switch to the "Mixer" tab
    And I select "Configuration Merge" as the mixer mode
    And I select columns "benchmark" and "config_id" to merge
    And I select "Concatenate" as the operation
    And I set the separator to "-"
    And I click "Preview Merge"
    Then the preview should show concatenated string values

  Scenario: Mean operation with SD propagation
    When I sum columns using "Mean (Average)"
    Then the SD propagation should divide by N

  # --- Operations History Tab ---

  Scenario: View complete operations history
    Given I have applied Seeds Reducer, Outlier Remover, and Preprocessor
    When I switch to the "Operations History" tab
    Then all three operations should appear in chronological order
    And each entry should show source columns, dest columns, and timestamp

  Scenario: Load operation from history
    Given the operations history contains a previous Seeds Reduction
    When I click "Load" on the Seeds Reduction entry
    And I switch to the "Seeds Reducer" tab
    Then the Seeds Reducer should be pre-populated with the saved configuration

  Scenario: Delete operation from history
    When I switch to the "Operations History" tab
    And I click "Delete" on a history entry
    Then the entry should be removed from the history

  # --- No Data Guard ---

  Scenario: Data Managers page without loaded data
    Given no data is currently loaded
    When I navigate to the "Data Managers" page
    Then a warning should indicate no data is loaded
    And all transformation tabs should be inaccessible
```

---

## 9. Feature Files (Gherkin) for Manage Plots Page

The Manage Plots page composes three controllers via dependency injection:
`PlotCreationController`, `PipelineController`, and `PlotRenderController`.
Each renders as a distinct section on the page.

```gherkin
# tests/e2e/features/manage_plots.feature
Feature: Plot Management and Visualization
  As a DataAnalyst
  I want to create, configure, and render data visualizations
  So that I can analyze simulation results graphically

  Background:
    Given the RING-5 application is running
    And simulation data is loaded and available
    And I am on the "Manage Plots" page

  # --- Plot Creation ---

  Scenario: Create a new bar plot
    When I enter "Performance Comparison" as the plot name
    And I select "bar" as the plot type
    And I click "Create Plot"
    Then the plot "Performance Comparison" should appear in the selector
    And it should be automatically selected

  Scenario: Create multiple plots
    When I create a plot named "Plot A" of type "bar"
    And I create a plot named "Plot B" of type "line"
    And I create a plot named "Plot C" of type "scatter"
    Then the plot selector should contain all three plots

  Scenario: Default plot name increments counter
    When I create a plot without specifying a name
    Then the plot name should default to "Plot 1"
    When I create another plot without specifying a name
    Then the plot name should default to "Plot 2"

  Scenario: No plots warning message
    Given no plots have been created
    Then a warning message should indicate no plots exist

  # --- Plot Selection and Controls ---

  Scenario: Select a different plot
    Given plots "Alpha" and "Beta" exist
    When I select "Beta" from the plot selector
    Then "Beta" should become the active plot
    And the pipeline and config should update for "Beta"

  Scenario: Rename a plot
    Given a plot named "Old Name" exists and is selected
    When I change the plot name to "New Name"
    Then the plot selector should show "New Name"

  Scenario: Delete a plot
    Given plots "Keep" and "Remove" exist
    And "Remove" is selected
    When I click "Delete"
    Then "Remove" should no longer appear in the selector
    And "Keep" should still exist

  Scenario: Duplicate a plot
    Given a plot "Original" exists with a configured pipeline
    And "Original" is selected
    When I click "Duplicate"
    Then a copy of "Original" should appear in the selector
    And the copy should have the same pipeline configuration

  # --- Pipeline Management ---

  Scenario: Add a shaper to the pipeline
    Given a plot exists and is selected
    When I select "Normalizer" from the transformation dropdown
    And I click "Add"
    Then the pipeline should contain one step
    And the step should be labeled "Normalizer"

  Scenario: Add multiple shapers to the pipeline
    When I add a "Filter" shaper
    And I add a "Normalizer" shaper
    And I add a "Sorter" shaper
    Then the pipeline should contain 3 steps in order

  Scenario: Remove a shaper from the pipeline
    Given the pipeline contains a "Filter" step
    When I click delete on the "Filter" step
    Then the pipeline should no longer contain "Filter"

  Scenario: Reorder pipeline steps
    Given the pipeline contains steps ["Filter", "Normalizer", "Sorter"]
    When I move "Normalizer" up
    Then the pipeline order should be ["Normalizer", "Filter", "Sorter"]

  Scenario: Finalize the pipeline
    Given the pipeline contains configured shaper steps
    When I click "Finalize"
    Then processed data should be generated
    And a success message should show the processed row count

  Scenario: Pipeline without data shows warning
    Given no data is loaded
    When I view the pipeline section
    Then a warning about missing data should be displayed

  # --- Visualization and Rendering ---

  Scenario: Render a plot after pipeline finalization
    Given a plot has finalized pipeline data
    When the visualization section loads
    Then a chart should be visible on the page
    And the plot type selector should show the current type

  Scenario: Change plot type preserves data
    Given a bar plot is rendered
    When I change the plot type to "line"
    Then the chart should re-render as a line plot
    And the data should be preserved

  Scenario: Toggle advanced settings
    Given a plot is rendered
    When I toggle "Show advanced settings"
    Then additional configuration options should appear

  Scenario: Switch rendering engine to Matplotlib
    Given a plot is rendered with Plotly
    When I switch the rendering engine to "Matplotlib"
    Then the chart should re-render using Matplotlib
    And the engine selector should show Matplotlib as active

  Scenario: Switch rendering engine to Plotly
    Given a plot is rendered with Matplotlib
    When I switch the rendering engine to "Plotly"
    Then the chart should re-render as an interactive Plotly chart

  Scenario: Auto-refresh on config change
    Given auto-refresh is enabled
    When I modify a plot configuration parameter
    Then the chart should automatically regenerate

  Scenario: Manual refresh when auto-refresh is off
    Given auto-refresh is disabled
    And I have modified the plot configuration
    When I click the refresh button
    Then the chart should regenerate with the new config
```

---

## 10. Feature Files (Gherkin) for Portfolio Page

The Portfolio page is rendered by `show_portfolio_page()` which wraps the
`_portfolio_fragment()` function. It provides a two-column layout (Save/Load)
and a Manage Saved Portfolios section with per-portfolio expanders and delete buttons.

```gherkin
# tests/e2e/features/portfolio.feature
Feature: Portfolio Management
  As a PortfolioManager
  I want to save and restore complete analysis sessions
  So that I can preserve and share my work

  Background:
    Given the RING-5 application is running
    And I am on the "Save/Load Portfolio" page

  # --- Save Portfolio ---

  Scenario: Save current session as a portfolio
    Given data is loaded and plots are configured
    When I enter "experiment_2024" as the portfolio name
    And I click "Save Portfolio"
    Then a toast notification should confirm the save
    And "experiment_2024" should appear in the management section

  Scenario: Save with default portfolio name
    Given data is loaded
    When I click "Save Portfolio" without changing the name
    Then a portfolio named "my_portfolio" should be saved

  Scenario: Overwrite existing portfolio
    Given a portfolio "analysis_v1" already exists
    When I save a new portfolio with the same name "analysis_v1"
    Then the portfolio should be updated with the current session

  # --- Load Portfolio ---

  Scenario: Load a saved portfolio
    Given a portfolio "saved_work" exists with data and plots
    When I select "saved_work" from the load dropdown
    And I click "Load Portfolio"
    Then a toast notification should confirm the load
    And the session should be restored with the saved data
    And all saved plots should be available

  Scenario: Verify state restoration after loading
    Given a portfolio with 3 plots and transformed data exists
    When I load the portfolio
    And I navigate to "Data Managers"
    Then the data row count should match the saved state
    When I navigate to "Manage Plots"
    Then all 3 plots should be available in the selector

  Scenario: Load portfolio dropdown shows all saved portfolios
    Given portfolios "alpha", "beta", and "gamma" exist
    When I view the Load Portfolio section
    Then the dropdown should contain "alpha", "beta", and "gamma"

  # --- Manage Saved Portfolios ---

  Scenario: Delete a saved portfolio
    Given a portfolio "temporary_work" exists
    When I expand the "temporary_work" entry in the management section
    And I click "Delete"
    Then a toast notification should confirm the deletion
    And "temporary_work" should no longer appear in the list

  Scenario: No portfolios displays warning
    Given no portfolios have been saved
    Then a warning should indicate no portfolios are found
    And the user should be prompted to save one first

  # --- Cross-Page State Integrity ---

  Scenario: Portfolio preserves complete state across pages
    Given I have loaded data with 500 rows
    And I have created 2 plots with configured pipelines
    And I have applied Seeds Reducer and Preprocessor operations
    When I save the portfolio as "full_state_test"
    And I reset the application
    And I load the portfolio "full_state_test"
    Then the data should have the transformed row count
    And both plots should be available with their pipeline configs
    And the data header metrics should match the saved state

  Scenario: Save portfolio preserves CSV path
    Given data was loaded from a specific CSV file
    When I save and reload the portfolio
    Then the Source metric should still show the original filename
```

---

## 11. Test Data Builder Pattern

Test data builders provide fluent interfaces for constructing test fixtures with sensible
defaults. They follow the Builder pattern adapted to Python `dataclass` idioms, enabling
tests to specify only the attributes relevant to their scenario.

### 11.1 CSV Data Builder

```python
# tests/e2e/builders/csv_data_builder.py
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class CSVDataBuilder:
    """Fluent builder for test CSV datasets.

    Produces DataFrames that mirror the structure of gem5 simulator output:
    categorical columns (benchmark, config_id, random_seed) and numeric
    columns (simTicks, instructions, cycles, etc.).
    """
    _rows: int = 100
    _benchmarks: list[str] = field(
        default_factory=lambda: ["alpha", "beta", "gamma"]
    )
    _configs: list[str] = field(
        default_factory=lambda: ["baseline", "optimized"]
    )
    _seeds: list[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])
    _numeric_columns: dict[str, tuple[float, float]] = field(
        default_factory=lambda: {
            "simTicks": (1e6, 1e9),
            "instructions": (1e4, 1e7),
            "cycles": (1e5, 1e8),
        }
    )
    _include_outliers: bool = False
    _include_missing: bool = False

    def with_rows(self, n: int) -> "CSVDataBuilder":
        self._rows = n
        return self

    def with_benchmarks(self, names: list[str]) -> "CSVDataBuilder":
        self._benchmarks = names
        return self

    def with_configs(self, names: list[str]) -> "CSVDataBuilder":
        self._configs = names
        return self

    def with_seeds(self, seeds: list[int]) -> "CSVDataBuilder":
        self._seeds = seeds
        return self

    def with_numeric_column(
        self, name: str, low: float, high: float
    ) -> "CSVDataBuilder":
        self._numeric_columns[name] = (low, high)
        return self

    def with_outliers(self) -> "CSVDataBuilder":
        self._include_outliers = True
        return self

    def with_missing_values(self) -> "CSVDataBuilder":
        self._include_missing = True
        return self

    def build(self) -> pd.DataFrame:
        """Construct the DataFrame."""
        rng = np.random.default_rng(42)
        rows = []
        for _ in range(self._rows):
            row = {
                "benchmark": rng.choice(self._benchmarks),
                "config_id": rng.choice(self._configs),
                "random_seed": rng.choice(self._seeds),
            }
            for col_name, (low, high) in self._numeric_columns.items():
                row[col_name] = rng.uniform(low, high)
            rows.append(row)
        df = pd.DataFrame(rows)
        if self._include_outliers:
            outlier_idx = rng.choice(len(df), size=max(1, len(df) // 20))
            for col_name in self._numeric_columns:
                df.loc[outlier_idx, col_name] *= 100
        if self._include_missing:
            for col_name in self._numeric_columns:
                mask = rng.random(len(df)) < 0.05
                df.loc[mask, col_name] = np.nan
        return df

    def build_and_save(self, path: Path) -> Path:
        """Build the DataFrame and save as CSV."""
        df = self.build()
        df.to_csv(path, index=False)
        return path
```

### 11.2 Plot Config Builder

```python
# tests/e2e/builders/plot_config_builder.py
from dataclasses import dataclass, field

@dataclass
class PlotConfigBuilder:
    """Build plot configuration dicts matching the PlotConfig TypedDict."""
    _plot_type: str = "bar"
    _x_column: str = "benchmark"
    _y_column: str = "simTicks"
    _group_by: str | None = "config_id"
    _title: str = "Test Plot"
    _show_legend: bool = True
    _extra: dict = field(default_factory=dict)

    def of_type(self, plot_type: str) -> "PlotConfigBuilder":
        self._plot_type = plot_type
        return self

    def with_axes(self, x: str, y: str) -> "PlotConfigBuilder":
        self._x_column = x
        self._y_column = y
        return self

    def grouped_by(self, column: str) -> "PlotConfigBuilder":
        self._group_by = column
        return self

    def titled(self, title: str) -> "PlotConfigBuilder":
        self._title = title
        return self

    def without_legend(self) -> "PlotConfigBuilder":
        self._show_legend = False
        return self

    def with_option(self, key: str, value: object) -> "PlotConfigBuilder":
        self._extra[key] = value
        return self

    def build(self) -> dict:
        config = {
            "plot_type": self._plot_type,
            "x_column": self._x_column,
            "y_column": self._y_column,
            "group_by": self._group_by,
            "title": self._title,
            "show_legend": self._show_legend,
        }
        config.update(self._extra)
        return config
```

### 11.3 Variable Config Builder

```python
# tests/e2e/builders/variable_config_builder.py
from dataclasses import dataclass, field
import uuid

@dataclass
class VariableConfigBuilder:
    """Build ParseVariableConfig dicts for parser test scenarios."""
    _name: str = "simTicks"
    _type: str = "scalar"
    _entries: list[str] = field(default_factory=list)
    _repeat: int = 1
    _min_val: int | None = None
    _max_val: int | None = None

    def named(self, name: str) -> "VariableConfigBuilder":
        self._name = name
        return self

    def as_scalar(self) -> "VariableConfigBuilder":
        self._type = "scalar"
        return self

    def as_vector(self, entries: list[str]) -> "VariableConfigBuilder":
        self._type = "vector"
        self._entries = entries
        return self

    def as_distribution(
        self, min_val: int, max_val: int
    ) -> "VariableConfigBuilder":
        self._type = "distribution"
        self._min_val = min_val
        self._max_val = max_val
        return self

    def as_configuration(self) -> "VariableConfigBuilder":
        self._type = "configuration"
        return self

    def with_repeat(self, n: int) -> "VariableConfigBuilder":
        self._repeat = n
        return self

    def build(self) -> dict:
        config = {
            "name": self._name,
            "type": self._type,
            "_id": str(uuid.uuid4()),
        }
        if self._type == "vector" and self._entries:
            config["vectorEntries"] = self._entries
        if self._type == "distribution":
            if self._min_val is not None:
                config["distMin"] = self._min_val
            if self._max_val is not None:
                config["distMax"] = self._max_val
        if self._repeat > 1:
            config["repeat"] = str(self._repeat)
        return config
```

### 11.4 Usage in Test Scenarios

```python
# Example: conftest.py fixtures using builders
import pytest

@pytest.fixture
def simulation_data():
    """Standard simulation dataset for most test scenarios."""
    return (
        CSVDataBuilder()
        .with_rows(200)
        .with_benchmarks(["alpha", "beta", "gamma", "delta"])
        .with_configs(["baseline", "optimized", "turbo"])
        .with_seeds([1, 2, 3, 4, 5])
        .with_numeric_column("simTicks", 1e6, 1e9)
        .with_numeric_column("instructions", 1e4, 1e7)
        .with_numeric_column("cycles", 1e5, 1e8)
        .build()
    )

@pytest.fixture
def data_with_outliers():
    """Dataset with intentional outliers for outlier removal testing."""
    return CSVDataBuilder().with_rows(500).with_outliers().build()

@pytest.fixture
def bar_plot_config():
    """Standard bar plot configuration."""
    return (
        PlotConfigBuilder()
        .of_type("bar")
        .with_axes("benchmark", "simTicks")
        .grouped_by("config_id")
        .titled("Benchmark Comparison")
        .build()
    )
```

---

## 12. Living Documentation Strategy

Living documentation transforms test execution artifacts into always-current, stakeholder-
readable documentation. The Serenity BDD approach generates rich HTML reports from test
metadata, screenshots, and step descriptions.

### 12.1 Report Architecture

```
living_docs/
  output/
    index.html                    # Dashboard with feature overview
    features/
      data_source.html            # Per-feature pages
      data_managers.html
      manage_plots.html
      portfolio.html
    screenshots/
      data_source/                # Step-level screenshots per scenario
      data_managers/
      manage_plots/
      portfolio/
    capabilities/
      data_ingestion.html         # Capability-grouped views
      data_transformation.html
      visualization.html
      session_management.html
    requirements/
      coverage_matrix.html        # Feature -> Scenario -> Status map
```

### 12.2 Screenshot Capture Strategy

Screenshots are captured at meaningful points during test execution using pytest hooks
and the `BrowseTheWeb` ability:

```python
# tests/e2e/living_docs/screenshot_hook.py
import pytest
from pathlib import Path
from datetime import datetime

class ScreenshotCollector:
    """Captures screenshots at key moments during test execution."""

    def __init__(self, output_dir: Path) -> None:
        self._dir = output_dir
        self._step_counter = 0
        self._current_scenario = ""

    def on_scenario_start(self, scenario_name: str) -> None:
        self._current_scenario = scenario_name.replace(" ", "_").lower()
        self._step_counter = 0
        (self._dir / self._current_scenario).mkdir(parents=True, exist_ok=True)

    def capture_step(self, page, step_description: str) -> Path:
        """Capture a screenshot for a Given/When/Then step."""
        self._step_counter += 1
        filename = f"{self._step_counter:03d}_{step_description[:50]}.png"
        filepath = self._dir / self._current_scenario / filename
        page.screenshot(path=str(filepath), full_page=True)
        return filepath

    def capture_error(self, page, error_description: str) -> Path:
        """Capture a screenshot on test failure."""
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"ERROR_{timestamp}_{error_description[:30]}.png"
        filepath = self._dir / self._current_scenario / filename
        page.screenshot(path=str(filepath), full_page=True)
        return filepath
```

### 12.3 Report Generator

The report generator transforms pytest-bdd execution results and captured screenshots
into a navigable HTML report following the Serenity living documentation model:

```python
# tests/e2e/living_docs/report_generator.py
from dataclasses import dataclass, field
from pathlib import Path
import json

@dataclass
class ScenarioResult:
    """Result of a single scenario execution."""
    feature: str
    scenario: str
    status: str  # "passed", "failed", "skipped"
    steps: list[dict] = field(default_factory=list)
    screenshots: list[Path] = field(default_factory=list)
    duration_ms: float = 0.0
    error: str | None = None

@dataclass
class FeatureReport:
    """Aggregated report for a feature file."""
    name: str
    description: str
    scenarios: list[ScenarioResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if not self.scenarios:
            return 0.0
        passed = sum(1 for s in self.scenarios if s.status == "passed")
        return passed / len(self.scenarios) * 100

class LivingDocumentationGenerator:
    """Generate Serenity-style living documentation from test results.

    Reads pytest-bdd JSON output and captured screenshots to produce
    a navigable HTML site with:
    - Feature overview dashboard
    - Per-feature scenario lists with pass/fail status
    - Step-by-step screenshots for each scenario
    - Capability-grouped views (cross-cutting concerns)
    - Requirements coverage matrix
    """

    def __init__(self, results_dir: Path, output_dir: Path) -> None:
        self._results_dir = results_dir
        self._output_dir = output_dir
        self._features: list[FeatureReport] = []

    def collect_results(self) -> None:
        """Parse pytest-bdd JSON results and match with screenshots."""
        results_file = self._results_dir / "results.json"
        if results_file.exists():
            data = json.loads(results_file.read_text())
            for feature_data in data.get("features", []):
                feature = FeatureReport(
                    name=feature_data["name"],
                    description=feature_data.get("description", ""),
                )
                for scenario_data in feature_data.get("scenarios", []):
                    scenario = ScenarioResult(
                        feature=feature.name,
                        scenario=scenario_data["name"],
                        status=scenario_data["status"],
                        duration_ms=scenario_data.get("duration", 0),
                    )
                    scenario_dir = (
                        self._results_dir
                        / "screenshots"
                        / scenario.scenario.replace(" ", "_").lower()
                    )
                    if scenario_dir.exists():
                        scenario.screenshots = sorted(scenario_dir.glob("*.png"))
                    feature.scenarios.append(scenario)
                self._features.append(feature)

    def generate(self) -> Path:
        """Generate the complete living documentation site."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._generate_index()
        for feature in self._features:
            self._generate_feature_page(feature)
        self._generate_coverage_matrix()
        return self._output_dir / "index.html"

    def _generate_index(self) -> None:
        """Generate the top-level dashboard."""
        total = sum(len(f.scenarios) for f in self._features)
        passed = sum(
            1
            for f in self._features
            for s in f.scenarios
            if s.status == "passed"
        )
        # HTML generation with embedded CSS (template-based in practice)
        pass

    def _generate_feature_page(self, feature: FeatureReport) -> None:
        """Generate a page for a single feature with scenario details."""
        pass

    def _generate_coverage_matrix(self) -> None:
        """Generate a requirements coverage matrix."""
        pass
```

### 12.4 Capability Mapping

Features are grouped into business capabilities for stakeholder-oriented views:

| Capability | Features | Scenarios |
|---|---|---|
| **Data Ingestion** | Data Source | CSV Pool, Parser Config, Variable Scanning, Parsing |
| **Data Transformation** | Data Managers | Seeds Reducer, Outlier Remover, Preprocessor, Mixer |
| **Visualization** | Manage Plots | Plot Creation, Pipeline, Rendering, Engine Switching |
| **Session Management** | Portfolio | Save, Load, Delete, State Restoration |
| **Navigation** | Cross-cutting | Sidebar Navigation, Reset, Clear |

### 12.5 Integration with CI/CD

The living documentation generation integrates into the CI pipeline as a post-test step:

```yaml
# .github/workflows/e2e.yml (excerpt)
- name: Run E2E Tests
  run: |
    pytest tests/e2e/ \
      --bdd-json=results/results.json \
      --screenshot-dir=results/screenshots/ \
      --headed=false

- name: Generate Living Documentation
  if: always()
  run: |
    python -m tests.e2e.living_docs.report_generator \
      --results-dir=results/ \
      --output-dir=docs/living/

- name: Publish Living Documentation
  if: always()
  uses: actions/upload-artifact@v4
  with:
    name: living-documentation
    path: docs/living/
```

---

## 13. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

| Task | Description | Dependencies |
|---|---|---|
| **1.1** Set up `tests/e2e/` directory structure | Create the full hierarchy from Section 2.3 | None |
| **1.2** Implement `Actor` base class and protocols | `Performable`, `Answerable`, `Ability`, `Expectation` | None |
| **1.3** Implement `BrowseTheWeb` ability | Playwright `Page` wrapper with `wait_for_streamlit()` | 1.1 |
| **1.4** Implement `InteractWithStreamlit` ability | All widget interaction methods from Section 4.2 | 1.3 |
| **1.5** Implement `AccessFileSystem` ability | File fixture creation and download verification | 1.1 |
| **1.6** Create persona factory functions | `create_data_analyst()`, `create_researcher()`, etc. | 1.2, 1.3, 1.4 |
| **1.7** Implement `NavigateTo` and sidebar tasks | Cross-page navigation verified against 5-page structure | 1.4 |
| **1.8** Set up `pytest-bdd` with conftest | Fixtures for actor creation, app URL, test data dir | 1.1-1.7 |

### Phase 2: Data Source Coverage (Week 3)

| Task | Description | Dependencies |
|---|---|---|
| **2.1** Implement Data Source tasks | `SelectDataSourceMode`, `LoadCSVFromPool`, `ConfigureParser`, etc. | Phase 1 |
| **2.2** Implement Data Source questions | Navigation and data table questions | Phase 1 |
| **2.3** Write `data_source.feature` Gherkin file | All scenarios from Section 7 | 2.1, 2.2 |
| **2.4** Implement step definitions | `pytest-bdd` step implementations connecting feature to tasks/questions | 2.1, 2.2, 2.3 |
| **2.5** Create `CSVDataBuilder` | Test data builder for CSV fixtures | Phase 1 |
| **2.6** Create `VariableConfigBuilder` | Variable configuration builders | Phase 1 |

### Phase 3: Data Managers Coverage (Week 4-5)

| Task | Description | Dependencies |
|---|---|---|
| **3.1** Implement Data Managers tasks | All four sub-manager tasks + tab switching | Phase 1 |
| **3.2** Implement Data Managers questions | Metrics, data table, transformation result questions | Phase 1 |
| **3.3** Write `data_managers.feature` Gherkin file | All scenarios from Section 8 | 3.1, 3.2 |
| **3.4** Implement step definitions | Connect all seven tabs to task/question objects | 3.1, 3.2, 3.3 |
| **3.5** Build test fixtures for transformations | Datasets with seeds, outliers, multiple numeric columns | 2.5 |

### Phase 4: Manage Plots Coverage (Week 6-7)

| Task | Description | Dependencies |
|---|---|---|
| **4.1** Implement Plot lifecycle tasks | `CreatePlot`, `SelectPlot`, `RenamePlot`, `DeleteCurrentPlot`, etc. | Phase 1 |
| **4.2** Implement Pipeline tasks | `AddShaperToPipeline`, `FinalizePipeline`, reordering | Phase 1 |
| **4.3** Implement Visualization tasks | `ChangePlotType`, `ToggleAdvancedSettings`, `SwitchRenderingEngine` | Phase 1 |
| **4.4** Implement Plot questions | `ThePlot.is_visible()`, `ThePlotSelector`, pipeline step count, etc. | Phase 1 |
| **4.5** Write `manage_plots.feature` Gherkin file | All scenarios from Section 9 | 4.1-4.4 |
| **4.6** Implement step definitions | Full plot lifecycle + pipeline + rendering coverage | 4.1-4.5 |
| **4.7** Create `PlotConfigBuilder` | Plot configuration builders for test fixtures | Phase 1 |

### Phase 5: Portfolio Coverage (Week 8)

| Task | Description | Dependencies |
|---|---|---|
| **5.1** Implement Portfolio tasks | `SavePortfolio`, `LoadPortfolio`, `DeletePortfolio` | Phase 1 |
| **5.2** Implement Portfolio questions | `ThePortfolio` question set | Phase 1 |
| **5.3** Write `portfolio.feature` Gherkin file | All scenarios from Section 10 | 5.1, 5.2 |
| **5.4** Implement step definitions | Save/load/delete + cross-page state integrity | 5.1, 5.2, 5.3 |
| **5.5** Implement `ManageTestState` ability | Direct API state injection for Given-step shortcuts | Phase 1 |

### Phase 6: Living Documentation (Week 9-10)

| Task | Description | Dependencies |
|---|---|---|
| **6.1** Implement `ScreenshotCollector` | Per-step screenshot capture with pytest hooks | Phases 2-5 |
| **6.2** Implement `LivingDocumentationGenerator` | HTML report generation from test results | 6.1 |
| **6.3** Design HTML report templates | Dashboard, feature pages, coverage matrix | 6.2 |
| **6.4** Implement capability mapping | Cross-feature grouping into business capabilities | 6.2 |
| **6.5** CI/CD integration | GitHub Actions workflow for report generation and publishing | 6.1-6.4 |
| **6.6** Documentation of documentation | How to read and maintain the living docs | 6.1-6.5 |

### Effort Estimates

| Phase | Estimated Effort | Key Deliverables |
|---|---|---|
| Phase 1: Foundation | 5-7 days | Actor, Ability, protocol infrastructure, conftest |
| Phase 2: Data Source | 4-5 days | 13 scenarios, CSV/Parser/Scanner coverage |
| Phase 3: Data Managers | 6-8 days | 18 scenarios, four sub-manager coverage |
| Phase 4: Manage Plots | 6-8 days | 19 scenarios, lifecycle/pipeline/render coverage |
| Phase 5: Portfolio | 3-4 days | 9 scenarios, state integrity validation |
| Phase 6: Living Docs | 5-7 days | Report generator, CI/CD integration |
| **Total** | **29-39 days** | **59 scenarios, full living documentation** |

### Risk Mitigation

| Risk | Mitigation |
|---|---|
| Streamlit DOM changes between versions | `InteractWithStreamlit` ability isolates all widget locators; single update point |
| Slow E2E tests blocking CI | Parallel execution via `pytest-xdist`, Given-step shortcuts via `ManageTestState` |
| Flaky tests from Streamlit rerun timing | `wait_for_streamlit()` in `BrowseTheWeb` waits for status widget to disappear |
| Screenshot diff on different resolutions | Standardized viewport size in Playwright config (1920x1080) |
| Feature file drift from code changes | Living documentation highlights stale/failing scenarios immediately |
| Complex pipeline interactions | Incremental test approach: test each shaper type independently, then compose |
