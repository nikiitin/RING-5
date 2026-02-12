from pathlib import Path

from streamlit.testing.v1 import AppTest

_APP_PATH = str(Path(__file__).parents[2] / "app.py")


class TestUISanity:
    """Sanity checks for the Streamlit UI."""

    def test_app_startup(self):
        """Test that the app starts without error."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        assert not at.exception

        assert len(at.markdown) > 0 or len(at.title) > 0  # Verify content exists

    def test_navigation_sidebar(self):
        """Test that navigation sidebar is present."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        assert len(at.sidebar.radio) > 0
        nav = at.sidebar.radio[0]
        assert "Data Source" in nav.options
        assert "Manage Plots" in nav.options

    def test_manage_plots_page_load(self):
        """Test loading the Manage Plots page."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        at.sidebar.radio[0].set_value("Manage Plots").run()

        assert not at.exception
        assert len(at.markdown) > 0 or len(at.header) > 0  # Verify content exists
