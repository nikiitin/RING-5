"""Recipe browser helpers require persisted results after one-shot feedback expires."""

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from tests.visual.pages.portfolio_page import PortfolioPage


def test_recipe_save_waits_for_publication_and_selects_its_exact_saved_name() -> None:
    """A save completes through persisted selection, independent of transient feedback."""
    page = MagicMock()
    portfolio = PortfolioPage(page)
    name_input, save_button, scope, cycle = (MagicMock() for _ in range(4))
    events: list[str] = []
    name_input.fill.side_effect = lambda _name: events.append("name entered")
    name_input.press.side_effect = lambda _key: events.append("name committed")
    cycle.__enter__.side_effect = lambda: events.append("armed")
    save_button.click.side_effect = lambda: events.append("saved")
    cycle.__exit__.side_effect = lambda *_args: events.append("app completed")

    with (
        patch.object(portfolio, "open_analysis_recipes"),
        patch.object(
            PortfolioPage,
            "analysis_recipes_expander",
            new_callable=PropertyMock,
            return_value=scope,
        ),
        patch.object(
            PortfolioPage, "recipe_name_input", new_callable=PropertyMock, return_value=name_input
        ),
        patch.object(
            PortfolioPage, "save_recipe_button", new_callable=PropertyMock, return_value=save_button
        ),
        patch.object(portfolio, "expect_script_rerun", return_value=cycle) as observe,
        patch.object(portfolio, "select_saved_recipe") as select,
        patch("tests.visual.pages.portfolio_page.expect"),
    ):
        select.side_effect = lambda _name: events.append("persisted recipe selected")
        portfolio.save_current_as_recipe("Exact saved recipe")

    assert events == [
        "name entered",
        "name committed",
        "armed",
        "saved",
        "app completed",
        "persisted recipe selected",
    ]
    name_input.fill.assert_called_once_with("Exact saved recipe")
    name_input.press.assert_called_once_with("Enter")
    observe.assert_called_once_with()
    save_button.click.assert_called_once_with()
    select.assert_called_once_with("Exact saved recipe")
    page.wait_for_timeout.assert_not_called()


@pytest.mark.parametrize("missing_summary", [False, True])
def test_recipe_selection_requires_the_named_saved_panel_result(missing_summary: bool) -> None:
    """The client-side select value alone cannot prove which saved recipe was loaded."""
    page = MagicMock()
    portfolio = PortfolioPage(page)
    scope, tab, selectbox = (MagicMock() for _ in range(3))
    saved = scope.get_by_role.return_value
    markdown = saved.get_by_test_id.return_value
    summary = markdown.get_by_text.return_value

    with (
        patch.object(portfolio, "open_analysis_recipes"),
        patch.object(
            PortfolioPage,
            "analysis_recipes_expander",
            new_callable=PropertyMock,
            return_value=scope,
        ),
        patch.object(
            PortfolioPage, "saved_recipes_tab", new_callable=PropertyMock, return_value=tab
        ),
        patch.object(
            PortfolioPage,
            "saved_recipe_selectbox",
            new_callable=PropertyMock,
            return_value=selectbox,
        ),
        patch.object(portfolio, "_open_and_select") as choose,
        patch("tests.visual.pages.portfolio_page.expect") as expect,
    ):
        if missing_summary:
            expect.return_value.to_be_visible.side_effect = AssertionError(
                "Saved recipe is missing"
            )
            with pytest.raises(AssertionError, match="Saved recipe is missing"):
                portfolio.select_saved_recipe("Exact saved recipe")
        else:
            portfolio.select_saved_recipe("Exact saved recipe")

    tab.click.assert_called_once_with()
    choose.assert_called_once_with(selectbox, "Exact saved recipe")
    scope.get_by_role.assert_called_once_with("tabpanel", name="Saved", exact=True)
    saved.get_by_test_id.assert_called_once_with("stMarkdownContainer")
    markdown.get_by_text.assert_called_once_with("Exact saved recipe", exact=True)
    expect.assert_called_once_with(summary)
    expect.return_value.to_be_visible.assert_called_once_with(timeout=portfolio.RENDER_TIMEOUT)
    page.wait_for_timeout.assert_not_called()
