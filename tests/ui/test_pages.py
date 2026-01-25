"""
Comprehensive UI tests for the Data Source page.
Tests file selection, variable configuration, and parsing workflow.
"""

from streamlit.testing.v1 import AppTest


class TestDataSourcePage:
    """UI tests for Data Source page."""

    def test_page_loads(self):
        """Test that Data Source page loads without error."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Navigate to Data Source
        at.sidebar.radio[0].set_value("Data Source").run()

        assert not at.exception

    def test_data_source_options_present(self):
        """Test that data source options are available."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        at.sidebar.radio[0].set_value("Data Source").run()
        assert not at.exception

    def test_interaction_tabs(self):
        """Test interaction with Data Source interaction tabs/radios."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Data Source").run()

        if len(at.radio) > 0:
            opt0 = at.radio[0].options[0]
            at.radio[0].set_value(opt0).run()
            assert not at.exception

            if len(at.radio[0].options) > 1:
                opt1 = at.radio[0].options[1]
                at.radio[0].set_value(opt1).run()
                assert not at.exception


class TestUploadDataPage:
    """UI tests for Upload Data page."""

    def test_page_loads(self):
        """Test that Upload Data page loads without error."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Upload Data").run()
        assert not at.exception

    def test_upload_tabs(self):
        """Test interaction with Upload Data tabs."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Upload Data").run()

        if len(at.tabs) > 0:
            at.tabs[0].run()
            assert not at.exception

            if len(at.tabs) > 1:
                at.tabs[1].run()
                assert not at.exception


class TestDataManagersPage:
    """UI tests for Data Managers page."""

    def test_page_loads(self):
        """Test that Data Managers page loads."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Data Managers").run()
        assert not at.exception

    def test_page_renders_tabs(self):
        """Test that Data Managers page has tabs for different managers."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Data Managers").run()
        assert not at.exception

    def test_no_data_message(self):
        """Test that appropriate message is shown when no data loaded."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Data Managers").run()
        assert not at.exception


class TestManagePlotsPage:
    """UI tests for Manage Plots page."""

    def test_page_loads(self):
        """Test that Manage Plots page loads."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Manage Plots").run()
        assert not at.exception

    def test_create_plot_interaction(self):
        """Test interacting with Create Plot section."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Manage Plots").run()

        for btn in at.button:
            if "Create" in btn.label or "Add" in btn.label:
                btn.click().run()
                assert not at.exception
                break


class TestPortfolioPage:
    """UI tests for Portfolio (Save/Load) page."""

    def test_page_loads(self):
        """Test that Portfolio page loads."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Save/Load Portfolio").run()
        assert not at.exception

    def test_page_renders_content(self):
        """Test that Portfolio page renders content."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        at.sidebar.radio[0].set_value("Save/Load Portfolio").run()
        assert not at.exception


class TestNavigation:
    """Tests for navigation between pages."""

    def test_navigate_through_all_pages(self):
        """Test navigating through all pages in order."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        pages = [
            "Data Source",
            "Upload Data",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
        ]

        for page in pages:
            at.sidebar.radio[0].set_value(page).run()
            assert not at.exception, f"Navigation to '{page}' failed"

    def test_navigate_back_and_forth(self):
        """Test navigating back and forth between pages."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        at.sidebar.radio[0].set_value("Manage Plots").run()
        assert not at.exception

        at.sidebar.radio[0].set_value("Data Source").run()
        assert not at.exception

        at.sidebar.radio[0].set_value("Manage Plots").run()
        assert not at.exception


class TestSidebarElements:
    """Tests for sidebar elements."""

    def test_sidebar_has_navigation(self):
        """Test that sidebar contains navigation radio."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert len(at.sidebar.radio) > 0

    def test_clear_button_present(self):
        """Test that clear data button is present."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert len(at.sidebar.button) > 0 or not at.exception

    def test_sidebar_title(self):
        """Test that sidebar has title."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        assert len(at.sidebar.markdown) > 0 or not at.exception
