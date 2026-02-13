"""E2E AppTest: Portfolio (Save/Load) page tests.

Tests the portfolio save, load, delete, and pipeline template workflows:
- Save portfolio with data loaded
- Load portfolio restores state
- Delete portfolio removes it
- No-data save shows error
- Empty state shows appropriate warnings
- Pipeline template section renders
"""

from typing import Any, List

from tests.ui.helpers import (
    create_app,
    create_app_with_data,
    create_app_with_plots,
    get_api,
    navigate_to,
)


# ---------------------------------------------------------------------------
# Portfolio page — rendering
# ---------------------------------------------------------------------------
class TestPortfolioPageRendering:
    """Portfolio page renders correctly in various states."""

    def test_page_renders_without_data(self) -> None:
        """Portfolio page renders without error when no data is loaded."""
        at = create_app()
        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception

    def test_page_renders_with_data(self) -> None:
        """Portfolio page renders without error when data is loaded."""
        at = create_app_with_data()
        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception

    def test_save_name_input_present(self) -> None:
        """Save section has a text_input for portfolio name."""
        at = create_app_with_data()
        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception
        name_inputs = [
            t for t in at.text_input if "portfolio" in t.label.lower() or "name" in t.label.lower()
        ]
        assert len(name_inputs) >= 1, "Expected portfolio name text input"

    def test_save_button_present(self) -> None:
        """Save Portfolio button is present."""
        at = create_app_with_data()
        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception
        save_buttons = [b for b in at.button if "save" in b.label.lower()]
        assert len(save_buttons) >= 1, "Expected Save Portfolio button"

    def test_no_portfolios_shows_warning(self) -> None:
        """When no portfolios exist, shows a warning in load section."""
        at = create_app()
        api: Any = get_api(at)

        # Ensure no portfolios exist by clearing any leftovers
        for name in api.data_services.list_portfolios():
            api.data_services.delete_portfolio(name)

        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception
        # Should show some kind of "no portfolios" message
        warnings = [w for w in at.warning if "no portfolio" in w.value.lower()]
        assert len(warnings) >= 1, "Expected 'no portfolios' warning"


# ---------------------------------------------------------------------------
# Portfolio save/load via API
# ---------------------------------------------------------------------------
class TestPortfolioSaveLoad:
    """Portfolio save and load operations via the API."""

    def test_save_portfolio_via_api(self) -> None:
        """Saving a portfolio via API stores it successfully."""
        at = create_app_with_data()
        api: Any = get_api(at)

        api.data_services.save_portfolio(
            name="e2e_test_portfolio",
            data=api.state_manager.get_data(),
            plots=[],
            config={},
            plot_counter=0,
        )

        portfolios: List[str] = api.data_services.list_portfolios()
        assert "e2e_test_portfolio" in portfolios

        # Cleanup
        api.data_services.delete_portfolio("e2e_test_portfolio")

    def test_load_portfolio_restores_data(self) -> None:
        """Loading a saved portfolio restores the data."""
        at = create_app_with_data()
        api: Any = get_api(at)

        original_data = api.state_manager.get_data()
        api.data_services.save_portfolio(
            name="e2e_restore_test",
            data=original_data,
            plots=[],
            config={},
            plot_counter=0,
        )

        # Clear state
        api.state_manager.set_data(None)
        assert not api.state_manager.has_data()

        # Load portfolio
        portfolio_data = api.data_services.load_portfolio("e2e_restore_test")
        api.state_manager.restore_session(portfolio_data)

        # Verify data is restored
        restored = api.state_manager.get_data()
        assert restored is not None
        assert len(restored) == len(original_data)

        # Cleanup
        api.data_services.delete_portfolio("e2e_restore_test")

    def test_delete_portfolio_removes_it(self) -> None:
        """Deleting a portfolio removes it from the list."""
        at = create_app_with_data()
        api: Any = get_api(at)

        api.data_services.save_portfolio(
            name="e2e_delete_test",
            data=api.state_manager.get_data(),
            plots=[],
            config={},
            plot_counter=0,
        )
        assert "e2e_delete_test" in api.data_services.list_portfolios()

        api.data_services.delete_portfolio("e2e_delete_test")
        assert "e2e_delete_test" not in api.data_services.list_portfolios()

    def test_save_empty_name_raises(self) -> None:
        """Saving with empty name raises ValueError."""
        import pytest

        at = create_app_with_data()
        api: Any = get_api(at)

        with pytest.raises(ValueError):
            api.data_services.save_portfolio(
                name="",
                data=api.state_manager.get_data(),
                plots=[],
                config={},
                plot_counter=0,
            )

    def test_load_nonexistent_raises(self) -> None:
        """Loading a nonexistent portfolio raises FileNotFoundError."""
        import pytest

        at = create_app_with_data()
        api: Any = get_api(at)

        with pytest.raises(FileNotFoundError):
            api.data_services.load_portfolio("nonexistent_portfolio_xyz123")


# ---------------------------------------------------------------------------
# Portfolio page — save via UI
# ---------------------------------------------------------------------------
class TestPortfolioSaveViaUI:
    """Test save flow through AppTest UI interaction."""

    def test_save_button_click_with_data(self) -> None:
        """Clicking Save Portfolio with data loaded should succeed."""
        at = create_app_with_data()
        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception
        save_buttons = [b for b in at.button if "save" in b.label.lower()]
        if save_buttons:
            save_buttons[0].click().run()
            assert not at.exception

            # Verify portfolio was saved
            api: Any = get_api(at)
            portfolios = api.data_services.list_portfolios()
            # Should have at least one portfolio saved
            assert len(portfolios) >= 1

            # Cleanup: delete the portfolio we just saved
            for p in portfolios:
                if "my_portfolio" in p or "portfolio" in p.lower():
                    api.data_services.delete_portfolio(p)

    def test_save_no_data_shows_error(self) -> None:
        """Clicking Save with no data shows an error message."""
        at = create_app()
        navigate_to(at, "Save/Load Portfolio")

        save_buttons = [b for b in at.button if "save" in b.label.lower()]
        if save_buttons:
            save_buttons[0].click().run()
            assert not at.exception
            # Should show error about no data
            assert len(at.error) > 0, "Expected error when saving without data"


# ---------------------------------------------------------------------------
# Portfolio — pipeline templates
# ---------------------------------------------------------------------------
class TestPortfolioPipelineTemplates:
    """Pipeline template section on the portfolio page."""

    def test_pipeline_section_renders_with_plots(self) -> None:
        """Pipeline template section renders when plots exist."""
        at = create_app_with_plots()
        navigate_to(at, "Save/Load Portfolio")

        assert not at.exception

    def test_page_stable_across_reruns(self) -> None:
        """Portfolio page remains stable across multiple reruns."""
        at = create_app_with_data()
        navigate_to(at, "Save/Load Portfolio")

        for _ in range(3):
            at.run()
            assert not at.exception
