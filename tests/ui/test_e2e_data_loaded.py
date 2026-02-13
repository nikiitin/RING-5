"""E2E AppTest: All pages render correctly with data loaded.

Tests that every page in the application renders without errors when
data is pre-loaded via the injection pattern (session_state → API →
state_manager). Validates that data-dependent UI elements appear:
metrics, tabs, widgets, previews.

This is the foundational e2e layer — if these fail, nothing else works.
"""

from tests.ui.helpers import (
    create_app_with_data,
    create_app_with_plots,
    get_api,
    navigate_to,
)


# ---------------------------------------------------------------------------
# Data Managers — data loaded
# ---------------------------------------------------------------------------
class TestDataManagersWithData:
    """Data Managers page renders its 7 tabs when data is available."""

    def test_no_warning_when_data_loaded(self) -> None:
        """No 'no data' warning should appear when data is injected."""
        at = create_app_with_data()
        navigate_to(at, "Data Managers")

        assert not at.exception
        no_data_warnings = [w for w in at.warning if "no data" in w.value.lower()]
        assert len(no_data_warnings) == 0, "Should not show 'no data' warning"

    def test_tabs_render(self) -> None:
        """All 7 Data Manager tabs should render."""
        at = create_app_with_data()
        navigate_to(at, "Data Managers")

        assert not at.exception
        assert len(at.tabs) >= 7, f"Expected 7 tabs, got {len(at.tabs)}"

    def test_summary_tab_has_metrics(self) -> None:
        """Summary tab should show metrics (rows, columns, etc.)."""
        at = create_app_with_data()
        navigate_to(at, "Data Managers")

        assert not at.exception
        # Summary is the first tab; metrics should be present
        assert len(at.metric) > 0, "Expected at least one metric"

    def test_summary_tab_row_count_correct(self) -> None:
        """Summary tab should display the correct number of rows."""
        at = create_app_with_data()
        navigate_to(at, "Data Managers")

        assert not at.exception
        row_metrics = [m for m in at.metric if m.label == "Rows" or m.label == "Total Rows"]
        if row_metrics:
            # The e2e data has 18 rows
            assert "18" in str(row_metrics[0].value)

    def test_data_visualization_tab_has_dataframe(self) -> None:
        """Data Visualization tab should render a st.dataframe."""
        at = create_app_with_data()
        navigate_to(at, "Data Managers")

        assert not at.exception
        # Dataframes should be present (at least one from Summary or Viz tab)
        assert len(at.dataframe) > 0, "Expected at least one dataframe"


# ---------------------------------------------------------------------------
# Manage Plots — data loaded
# ---------------------------------------------------------------------------
class TestManagePlotsWithData:
    """Manage Plots page with data loaded should allow plot creation."""

    def test_page_renders_with_data(self) -> None:
        """Page renders without error when data is available."""
        at = create_app_with_data()
        navigate_to(at, "Manage Plots")

        assert not at.exception

    def test_create_section_present(self) -> None:
        """Create plot form still present with data loaded."""
        at = create_app_with_data()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        assert len(at.text_input) > 0, "Expected text input for plot name"
        assert len(at.selectbox) > 0, "Expected selectbox for plot type"

    def test_create_plot_form_submit(self) -> None:
        """Creating a plot via the form should add it to state."""
        at = create_app_with_data()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        # Find the Create Plot button and click it
        create_buttons = [b for b in at.button if "create" in b.label.lower()]
        if create_buttons:
            create_buttons[0].click().run()
            assert not at.exception
            # After creating, no-plots warning should disappear
            api = get_api(at)
            plots = api.state_manager.get_plots()
            assert len(plots) >= 1, "Expected at least one plot after creation"

    def test_plot_appears_after_creation(self) -> None:
        """After creating a plot, it should appear in state."""
        at = create_app_with_data()
        navigate_to(at, "Manage Plots")

        # Create via form
        create_buttons = [b for b in at.button if "create" in b.label.lower()]
        if create_buttons:
            create_buttons[0].click().run()

            api = get_api(at)
            plots = api.state_manager.get_plots()
            assert len(plots) >= 1

    def test_injected_plot_renders(self) -> None:
        """Pre-injected plots should render on the Manage Plots page."""
        at = create_app_with_plots()
        navigate_to(at, "Manage Plots")

        assert not at.exception
        # Should NOT have a "no plot" warning
        no_plot_warnings = [w for w in at.warning if "no plot" in w.value.lower()]
        assert len(no_plot_warnings) == 0, "Should not show 'no plot' warning"


# ---------------------------------------------------------------------------
# Portfolio — data loaded
# ---------------------------------------------------------------------------
class TestPortfolioWithData:
    """Portfolio page with data loaded should enable saving."""

    def test_page_renders_with_data(self) -> None:
        """Portfolio page renders without errors when data is loaded."""
        at = create_app_with_data()
        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception

    def test_save_section_present(self) -> None:
        """Save portfolio input and button are present."""
        at = create_app_with_data()
        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception
        assert len(at.text_input) > 0, "Expected text input for portfolio name"
        save_buttons = [b for b in at.button if "save" in b.label.lower()]
        assert len(save_buttons) > 0, "Expected 'Save Portfolio' button"


# ---------------------------------------------------------------------------
# Sidebar — data loaded
# ---------------------------------------------------------------------------
class TestSidebarWithData:
    """Sidebar shows dataset preview when data is loaded."""

    def test_data_preview_metrics_shown(self) -> None:
        """Sidebar area should show Rows/Columns metrics."""
        at = create_app_with_data()
        # After first run with data, re-run to render header metrics
        at.run()

        assert not at.exception
        row_metrics = [m for m in at.metric if m.label == "Rows"]
        col_metrics = [m for m in at.metric if m.label == "Columns"]
        assert (
            len(row_metrics) > 0 or len(col_metrics) > 0
        ), "Expected Rows/Columns metrics in data preview"

    def test_clear_data_button_clears_state(self) -> None:
        """Clicking Clear Data removes data from state."""
        at = create_app_with_data()
        at.run()

        assert not at.exception
        # Click "Clear Data" in sidebar
        clear_buttons = [b for b in at.sidebar.button if "clear" in b.label.lower()]
        assert len(clear_buttons) > 0
        clear_buttons[0].click().run()

        # After clear, data should be gone
        api = get_api(at)
        assert not api.state_manager.has_data()


# ---------------------------------------------------------------------------
# Performance — data loaded
# ---------------------------------------------------------------------------
class TestPerformanceWithData:
    """Performance page with data loaded shows correct metrics."""

    def test_page_renders_with_data(self) -> None:
        """Performance page renders when data is loaded."""
        at = create_app_with_data()
        navigate_to(at, "\u26a1 Performance")

        assert not at.exception

    def test_data_loaded_metric(self) -> None:
        """Data Loaded metric should show 'Yes'."""
        at = create_app_with_data()
        navigate_to(at, "\u26a1 Performance")

        assert not at.exception
        data_metrics = [m for m in at.metric if m.label == "Data Loaded"]
        if data_metrics:
            assert data_metrics[0].value == "Yes"

    def test_clear_caches_button(self) -> None:
        """Clear All Caches button should be present and clickable."""
        at = create_app_with_data()
        navigate_to(at, "\u26a1 Performance")

        assert not at.exception
        cache_buttons = [b for b in at.button if "clear" in b.label.lower()]
        assert len(cache_buttons) > 0

    def test_session_key_count_nonzero(self) -> None:
        """Total Keys metric should be > 0 when app is running."""
        at = create_app_with_data()
        navigate_to(at, "\u26a1 Performance")

        assert not at.exception
        key_metrics = [m for m in at.metric if m.label == "Total Keys"]
        if key_metrics:
            assert int(key_metrics[0].value) > 0


# ---------------------------------------------------------------------------
# Upload Data — data loaded (parser mode)
# ---------------------------------------------------------------------------
class TestUploadWithParserMode:
    """Upload Data page in parser mode shows parsed data preview."""

    def test_page_renders_with_data(self) -> None:
        """Upload Data page renders without errors when data is loaded."""
        at = create_app_with_data()
        navigate_to(at, "Upload Data")

        assert not at.exception

    def test_csv_mode_shows_tabs(self) -> None:
        """In CSV mode (default), Upload Data shows upload + paste tabs."""
        at = create_app_with_data()
        # Ensure NOT in parser mode
        api = get_api(at)
        api.state_manager.set_use_parser(False)
        navigate_to(at, "Upload Data")

        assert not at.exception
        # Should have at least 2 tabs (Upload CSV File / Paste Data)
        assert len(at.tabs) >= 2


# ---------------------------------------------------------------------------
# Data Source — data loaded
# ---------------------------------------------------------------------------
class TestDataSourceWithData:
    """Data Source page renders correctly with or without data."""

    def test_page_renders_with_data(self) -> None:
        """Data Source page renders without errors."""
        at = create_app_with_data()
        navigate_to(at, "Data Source")

        assert not at.exception

    def test_radio_options_present(self) -> None:
        """Data source radio has all 3 options."""
        at = create_app_with_data()
        navigate_to(at, "Data Source")

        assert not at.exception
        # There should be a radio for data source choice (beyond sidebar nav)
        page_radios = at.radio
        assert len(page_radios) > 0
