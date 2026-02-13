"""Extended AppTest workflow tests — deeper UI interactions.

Tests real Streamlit rendering with AppTest, beyond basic navigation.
Covers:
    - Manage Plots page widget interactions
    - Performance page rendering, and content
    - Portfolio page empty-state behavior
    - Data Managers empty-state behavior
    - Clear data / Reset all button behavior
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

_APP_PATH = str(Path(__file__).parents[2] / "app.py")


# ---------------------------------------------------------------------------
# Manage Plots workflows
# ---------------------------------------------------------------------------
class TestManagePlotsWorkflow:
    """Deeper tests for the Manage Plots page."""

    def test_no_plots_warning_shown(self) -> None:
        """When no plots exist, a warning is displayed."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Manage Plots").run()

        assert not at.exception
        # Should have at least one warning about no plots
        warnings = [w for w in at.warning if "no plot" in w.value.lower()]
        assert len(warnings) > 0, "Expected 'no plots' warning"

    def test_create_section_has_text_input_and_selectbox(self) -> None:
        """Create section renders a text input and selectbox for type."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Manage Plots").run()

        assert not at.exception
        # Should have text inputs for plot name
        assert len(at.text_input) > 0, "Expected text input for plot name"
        # Should have selectbox for plot type
        assert len(at.selectbox) > 0, "Expected selectbox for plot type"

    def test_create_plot_button_exists(self) -> None:
        """A 'Create Plot' button is present on the page."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Manage Plots").run()

        assert not at.exception
        create_buttons = [b for b in at.button if "create" in b.label.lower()]
        assert len(create_buttons) > 0, "Expected 'Create' button"


# ---------------------------------------------------------------------------
# Performance page
# ---------------------------------------------------------------------------
class TestPerformancePage:
    """Tests for the Performance monitoring page."""

    def test_page_loads(self) -> None:
        """Performance page loads without error."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("\u26a1 Performance").run()

        assert not at.exception

    def test_page_has_metrics(self) -> None:
        """Performance page renders metric widgets."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("\u26a1 Performance").run()

        assert not at.exception
        # Should show at least one metric (cache hit rate, etc.)
        assert len(at.metric) > 0 or len(at.markdown) > 0, "Expected metrics or content"


# ---------------------------------------------------------------------------
# Portfolio page empty state
# ---------------------------------------------------------------------------
class TestPortfolioEmptyState:
    """Tests for Portfolio page when no portfolios exist."""

    def test_portfolio_page_no_crash(self) -> None:
        """Portfolio page renders cleanly with no saved portfolios."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Save/Load Portfolio").run()

        assert not at.exception

    def test_portfolio_has_save_section(self) -> None:
        """Portfolio page has save form elements."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Save/Load Portfolio").run()

        assert not at.exception
        # Should have at least one text input for portfolio name
        has_text_input = len(at.text_input) > 0
        has_buttons = len(at.button) > 0
        assert has_text_input or has_buttons, "Expected save inputs or buttons"


# ---------------------------------------------------------------------------
# Data Managers empty state
# ---------------------------------------------------------------------------
class TestDataManagersEmptyState:
    """Tests for Data Managers page when no data is loaded."""

    def test_no_data_shows_warning(self) -> None:
        """When no data loaded, Data Managers shows appropriate message."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Data Managers").run()

        assert not at.exception
        # Should show a warning or info about needing data
        has_warning = len(at.warning) > 0
        has_error = len(at.error) > 0
        has_info = len(at.info) > 0
        assert has_warning or has_error or has_info, "Expected data-needed message"


# ---------------------------------------------------------------------------
# Sidebar action buttons
# ---------------------------------------------------------------------------
class TestSidebarActions:
    """Tests for sidebar action buttons."""

    def test_clear_data_button_exists(self) -> None:
        """Clear Data button is present in sidebar."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        clear_buttons = [b for b in at.sidebar.button if "clear" in b.label.lower()]
        assert len(clear_buttons) > 0, "Expected 'Clear Data' button"

    def test_reset_all_button_exists(self) -> None:
        """Reset All button is present in sidebar."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        reset_buttons = [b for b in at.sidebar.button if "reset" in b.label.lower()]
        assert len(reset_buttons) > 0, "Expected 'Reset All' button"

    def test_navigation_options_complete(self) -> None:
        """All expected navigation options are present."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        nav = at.sidebar.radio[0]
        expected = [
            "Data Source",
            "Upload Data",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
        ]
        for page in expected:
            assert page in nav.options, f"Missing nav option: {page}"


# ---------------------------------------------------------------------------
# App header and initial state
# ---------------------------------------------------------------------------
class TestAppInitialState:
    """Tests for application initial state."""

    def test_app_header_present(self) -> None:
        """App renders a main header on startup."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        assert not at.exception
        # Check for main header in markdown (HTML)
        header_markdowns = [
            m for m in at.markdown if "ring-5" in m.value.lower() or "analyzer" in m.value.lower()
        ]
        assert len(header_markdowns) > 0, "Expected RING-5 header"

    def test_no_data_preview_on_fresh_start(self) -> None:
        """On fresh start, no data preview section is shown."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        assert not at.exception
        # On fresh start, no data is loaded, so no metrics for dataset
        # The "Rows" metric should not appear
        row_metrics = [m for m in at.metric if m.label == "Rows"]
        assert len(row_metrics) == 0, "No data preview on fresh start"
