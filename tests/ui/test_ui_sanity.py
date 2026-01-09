from streamlit.testing.v1 import AppTest


class TestUISanity:
    """Sanity checks for the Streamlit UI."""

    def test_app_startup(self):
        """Test that the app starts without error."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        assert not at.exception

        # Check that the app rendered something (markdown elements should exist)
        # The title may be in markdown or other elements depending on Streamlit version
        assert len(at.markdown) > 0 or len(at.title) > 0

    def test_navigation_sidebar(self):
        """Test that navigation sidebar is present."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Check sidebar radio
        assert len(at.sidebar.radio) > 0
        nav = at.sidebar.radio[0]
        assert "Data Source" in nav.options
        assert "Manage Plots" in nav.options

    def test_manage_plots_page_load(self):
        """Test loading the Manage Plots page."""
        at = AppTest.from_file("app.py", default_timeout=10)
        at.run()

        # Navigate to Manage Plots
        at.sidebar.radio[0].set_value("Manage Plots").run()

        assert not at.exception
        # The page should have rendered without error, check that some content exists
        assert len(at.markdown) > 0 or len(at.header) > 0
