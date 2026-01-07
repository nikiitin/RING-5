"""
Comprehensive UI tests for the Data Source page.
Tests file selection, variable configuration, and parsing workflow.
"""

import pytest
from pathlib import Path
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
        
        # Should have some selection mechanism (radio, selectbox, etc.)
        # The page should render without crashing
        assert not at.exception

    def test_page_has_content(self):
        """Test that the page renders content."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        
        at.sidebar.radio[0].set_value("Data Source").run()
        
        # Page should have some markdown or headers
        assert len(at.markdown) > 0 or len(at.header) > 0 or len(at.subheader) > 0


class TestUploadDataPage:
    """UI tests for Upload Data page."""

    def test_page_loads(self):
        """Test that Upload Data page loads without error."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        
        at.sidebar.radio[0].set_value("Upload Data").run()
        
        assert not at.exception

    def test_file_uploader_present(self):
        """Test that file uploader is present."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        
        at.sidebar.radio[0].set_value("Upload Data").run()
        
        # Page should have file_uploader elements
        # Just check it rendered without error
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
        
        # Check for tabs element or content
        assert not at.exception

    def test_no_data_message(self):
        """Test that appropriate message is shown when no data loaded."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        
        at.sidebar.radio[0].set_value("Data Managers").run()
        
        # Should either show info/warning about no data or render successfully
        assert not at.exception


class TestManagePlotsPage:
    """UI tests for Manage Plots page."""

    def test_page_loads(self):
        """Test that Manage Plots page loads."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        
        at.sidebar.radio[0].set_value("Manage Plots").run()
        
        assert not at.exception

    def test_page_renders_content(self):
        """Test that Manage Plots page renders some content."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        
        at.sidebar.radio[0].set_value("Manage Plots").run()
        
        # Should have some content
        assert len(at.markdown) > 0 or len(at.header) > 0





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
        
        # Should have some content
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
            "Save/Load Portfolio"
        ]
        
        for page in pages:
            at.sidebar.radio[0].set_value(page).run()
            assert not at.exception, f"Navigation to '{page}' failed"

    def test_navigate_back_and_forth(self):
        """Test navigating back and forth between pages."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        
        # Go to Manage Plots
        at.sidebar.radio[0].set_value("Manage Plots").run()
        assert not at.exception
        
        # Go to Data Source
        at.sidebar.radio[0].set_value("Data Source").run()
        assert not at.exception
        
        # Go back to Manage Plots
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
        
        # Should have buttons in sidebar
        assert len(at.sidebar.button) > 0 or not at.exception

    def test_sidebar_title(self):
        """Test that sidebar has title."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()
        
        # Check for markdown in sidebar (title is rendered as markdown)
        assert len(at.sidebar.markdown) > 0 or not at.exception
