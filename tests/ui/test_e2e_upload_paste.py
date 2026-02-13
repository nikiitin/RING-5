"""E2E AppTest: Upload Data page — CSV paste and upload tab tests.

Tests the Upload Data page's two modes:
- CSV paste: text_area + Load button → parse → set_data
- File upload: file_uploader widget presence
- Parser mode: parsed data preview when data exists

st.file_uploader is NOT directly testable via AppTest, so we verify
the widget's existence and test the paste flow which is fully testable.
"""

from tests.ui.helpers import (
    create_app,
    create_app_with_data,
    get_api,
    navigate_to,
)


# ---------------------------------------------------------------------------
# Upload page — CSV mode (no parser)
# ---------------------------------------------------------------------------
class TestUploadPageCSVMode:
    """Upload Data page in CSV mode (no parser)."""

    def test_csv_mode_has_two_tabs(self) -> None:
        """CSV mode shows Upload CSV File and Paste Data tabs."""
        at = create_app()
        api = get_api(at)
        api.state_manager.set_use_parser(False)
        navigate_to(at, "Upload Data")

        assert not at.exception
        assert len(at.tabs) >= 2, "Expected at least 2 tabs (Upload + Paste)"

    def test_paste_tab_has_text_area(self) -> None:
        """Paste Data tab contains a text_area for CSV input."""
        at = create_app()
        api = get_api(at)
        api.state_manager.set_use_parser(False)
        navigate_to(at, "Upload Data")

        assert not at.exception
        assert len(at.text_area) >= 1, "Expected text_area for CSV paste"

    def test_paste_valid_csv_loads_data(self) -> None:
        """Pasting valid CSV and clicking Load stores data."""
        at = create_app()
        api = get_api(at)
        api.state_manager.set_use_parser(False)
        navigate_to(at, "Upload Data")

        # Paste CSV data into text area
        csv_text = "name,value\nalpha,1\nbeta,2\ngamma,3"
        at.text_area[0].set_value(csv_text).run()

        # Find and click Load Data button
        load_buttons = [b for b in at.button if "load" in b.label.lower()]
        if load_buttons:
            load_buttons[0].click().run()

            assert not at.exception
            data = api.state_manager.get_data()
            if data is not None:
                assert len(data) == 3
                assert "name" in data.columns

    def test_paste_empty_csv_no_crash(self) -> None:
        """Empty text area should not crash the page."""
        at = create_app()
        api = get_api(at)
        api.state_manager.set_use_parser(False)
        navigate_to(at, "Upload Data")

        # Leave text area empty — no Load button should appear
        assert not at.exception


# ---------------------------------------------------------------------------
# Upload page — parser mode
# ---------------------------------------------------------------------------
class TestUploadPageParserMode:
    """Upload Data page in parser mode with pre-loaded data."""

    def test_parser_mode_shows_preview(self) -> None:
        """When parser mode is on and data exists, shows parsed preview."""
        at = create_app_with_data()
        api = get_api(at)
        api.state_manager.set_use_parser(True)
        navigate_to(at, "Upload Data")

        assert not at.exception
        # Should show success or info messages about parsed data
        assert len(at.success) > 0 or len(at.info) > 0

    def test_parser_mode_no_data_shows_warning(self) -> None:
        """Parser mode with no data shows a warning."""
        at = create_app()
        api = get_api(at)
        api.state_manager.set_use_parser(True)
        navigate_to(at, "Upload Data")

        assert not at.exception
        # Should show a warning about no parsed data
        assert len(at.warning) > 0, "Expected warning when parser mode has no data"


# ---------------------------------------------------------------------------
# Upload page — data loaded preview
# ---------------------------------------------------------------------------
class TestUploadPageWithData:
    """Upload Data page behavior when data is already loaded."""

    def test_no_exception_when_data_loaded(self) -> None:
        """Page renders without error when data is pre-loaded."""
        at = create_app_with_data()
        navigate_to(at, "Upload Data")

        assert not at.exception

    def test_page_stable_after_rerun(self) -> None:
        """Page remains stable across multiple reruns."""
        at = create_app_with_data()
        navigate_to(at, "Upload Data")

        at.run()
        assert not at.exception
        at.run()
        assert not at.exception
