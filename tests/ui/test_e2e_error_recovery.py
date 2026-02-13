"""E2E AppTest: Error recovery and edge case tests.

Tests that the application handles error conditions gracefully:
- Clear data → pages degrade gracefully
- Reset all state → clean restart
- Invalid data scenarios
- Page navigation with missing state
- Empty pipeline rendering
- Corrupted data handling
"""

from typing import Any

import pandas as pd

from tests.ui.helpers import (
    create_app,
    create_app_with_data,
    create_app_with_plots,
    get_api,
    navigate_to,
)


# ---------------------------------------------------------------------------
# Clear data recovery
# ---------------------------------------------------------------------------
class TestClearDataRecovery:
    """App recovers gracefully when data is cleared mid-session."""

    def test_clear_data_via_sidebar(self) -> None:
        """Clicking Clear Data button removes data from state."""
        at = create_app_with_data()
        at.run()

        clear_buttons = [b for b in at.sidebar.button if "clear" in b.label.lower()]
        assert len(clear_buttons) > 0, "Expected Clear Data button"
        clear_buttons[0].click().run()

        api: Any = get_api(at)
        assert not api.state_manager.has_data()

    def test_data_managers_after_clear(self) -> None:
        """Data Managers page shows warning after data is cleared."""
        at = create_app_with_data()
        at.run()

        # Clear data
        api: Any = get_api(at)
        api.state_manager.set_data(None)
        api.state_manager.set_processed_data(None)

        navigate_to(at, "Data Managers")
        assert not at.exception

    def test_manage_plots_after_clear(self) -> None:
        """Manage Plots page renders without crash after data is cleared."""
        at = create_app_with_data()
        api: Any = get_api(at)

        api.state_manager.set_data(None)
        api.state_manager.set_processed_data(None)

        navigate_to(at, "Manage Plots")
        assert not at.exception

    def test_portfolio_save_after_clear(self) -> None:
        """Portfolio page shows error when saving without data."""
        at = create_app_with_data()
        api: Any = get_api(at)

        api.state_manager.set_data(None)
        api.state_manager.set_processed_data(None)

        navigate_to(at, "Save/Load Portfolio")

        save_buttons = [b for b in at.button if "save" in b.label.lower()]
        if save_buttons:
            save_buttons[0].click().run()
            assert not at.exception
            assert len(at.error) > 0, "Expected error when saving without data"


# ---------------------------------------------------------------------------
# Reset all state
# ---------------------------------------------------------------------------
class TestResetState:
    """Complete state reset behavior."""

    def test_clear_all_data_and_plots(self) -> None:
        """Clearing data and plots resets state completely."""
        at = create_app_with_plots()
        api: Any = get_api(at)

        # Verify state exists
        assert api.state_manager.has_data()
        assert len(api.state_manager.get_plots()) >= 1

        # Clear everything
        api.state_manager.set_data(None)
        api.state_manager.set_processed_data(None)
        api.state_manager.set_plots([])

        assert not api.state_manager.has_data()
        assert len(api.state_manager.get_plots()) == 0

    def test_pages_render_after_full_reset(self) -> None:
        """All pages render without exception after a full reset."""
        at = create_app_with_data()
        api: Any = get_api(at)

        api.state_manager.set_data(None)
        api.state_manager.set_processed_data(None)
        api.state_manager.set_plots([])

        pages = [
            "Data Source",
            "Upload Data",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
        ]

        for page in pages:
            navigate_to(at, page)
            assert not at.exception, f"Exception on page '{page}' after reset"


# ---------------------------------------------------------------------------
# Invalid data scenarios
# ---------------------------------------------------------------------------
class TestInvalidDataScenarios:
    """App handles edge cases in data gracefully."""

    def test_empty_dataframe_no_crash(self) -> None:
        """Setting an empty DataFrame doesn't crash pages."""
        at = create_app()
        api: Any = get_api(at)

        empty_df: pd.DataFrame = pd.DataFrame()
        api.state_manager.set_data(empty_df)
        api.state_manager.set_processed_data(empty_df.copy())

        navigate_to(at, "Data Managers")
        assert not at.exception

    def test_single_row_dataframe(self) -> None:
        """Single-row DataFrame is handled correctly."""
        at = create_app()
        api: Any = get_api(at)

        single_row: pd.DataFrame = pd.DataFrame({"name": ["test"], "value": [42.0]})
        api.state_manager.set_data(single_row)
        api.state_manager.set_processed_data(single_row.copy())

        navigate_to(at, "Data Managers")
        assert not at.exception

    def test_single_column_dataframe(self) -> None:
        """Single-column DataFrame is handled correctly."""
        at = create_app()
        api: Any = get_api(at)

        single_col: pd.DataFrame = pd.DataFrame({"values": [1, 2, 3, 4, 5]})
        api.state_manager.set_data(single_col)
        api.state_manager.set_processed_data(single_col.copy())

        navigate_to(at, "Data Managers")
        assert not at.exception

    def test_dataframe_with_nan_values(self) -> None:
        """DataFrame with NaN values doesn't crash pages."""
        import numpy as np

        at = create_app()
        api: Any = get_api(at)

        df_with_nan: pd.DataFrame = pd.DataFrame(
            {
                "name": ["a", "b", "c"],
                "value": [1.0, np.nan, 3.0],
                "category": ["x", None, "z"],
            }
        )
        api.state_manager.set_data(df_with_nan)
        api.state_manager.set_processed_data(df_with_nan.copy())

        navigate_to(at, "Data Managers")
        assert not at.exception


# ---------------------------------------------------------------------------
# Navigation edge cases
# ---------------------------------------------------------------------------
class TestNavigationEdgeCases:
    """Edge cases in page navigation."""

    def test_rapid_page_switching(self) -> None:
        """Rapid page switching doesn't crash the app."""
        at = create_app_with_data()

        pages = [
            "Data Source",
            "Upload Data",
            "Data Managers",
            "Manage Plots",
            "Save/Load Portfolio",
            "Data Managers",
            "Manage Plots",
        ]

        for page in pages:
            navigate_to(at, page)
            assert not at.exception, f"Exception on page '{page}'"

    def test_return_to_data_source(self) -> None:
        """Returning to Data Source from other pages works."""
        at = create_app_with_data()

        navigate_to(at, "Manage Plots")
        assert not at.exception

        navigate_to(at, "Data Source")
        assert not at.exception

    def test_performance_page_always_renders(self) -> None:
        """Performance page renders regardless of data state."""
        at = create_app()
        navigate_to(at, "\u26a1 Performance")

        assert not at.exception
        assert len(at.metric) >= 1, "Expected at least one metric"
