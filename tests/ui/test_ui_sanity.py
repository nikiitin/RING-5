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
        """Test that navigation sidebar has nav buttons."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        nav_labels = [b.label for b in at.sidebar.button]
        assert any("Data Source" in label for label in nav_labels)
        assert any("Manage Plots" in label for label in nav_labels)

    def test_manage_plots_page_load(self):
        """Test loading the Manage Plots page."""
        at = AppTest.from_file(_APP_PATH, default_timeout=10)
        at.run()

        at.session_state["_nav_page"] = "Manage Plots"
        at.run()

        assert not at.exception
        assert len(at.markdown) > 0 or len(at.header) > 0  # Verify content exists
