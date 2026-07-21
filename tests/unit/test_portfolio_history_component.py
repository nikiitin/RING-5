"""Human-first portfolio history component tests."""

from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from src.core.models import (
    PortfolioDiff,
    PortfolioDiffEntry,
    PortfolioRevisionInfo,
)


@patch("src.web.components.portfolio_history_component.st")
def test_lists_versions_and_renders_field_level_comparison(mock_st: MagicMock) -> None:
    # [test->req~ring5.portfolio.history-diff~1]
    from src.web.components.portfolio_history_component import PortfolioHistoryComponent

    before = PortfolioRevisionInfo(
        "Study", "a" * 64, 1, "2026-07-20T10:00:00", False, 100, "CSV", 1
    )
    after = PortfolioRevisionInfo("Study", "b" * 64, 2, "2026-07-21T10:00:00", True, 120, "CSV", 1)
    difference = PortfolioDiff(
        "Study",
        before.revision_id,
        after.revision_id,
        (PortfolioDiffEntry("figure_settings", "figure[0].raw.title", "changed", "Old", "New"),),
        (("data_sources", 0), ("pipelines", 0), ("plots", 0), ("figure_settings", 1)),
    )
    api = MagicMock()
    api.data_services.list_portfolio_revisions.return_value = (before, after)
    api.data_services.compare_portfolio_revisions.return_value = difference
    mock_st.columns.return_value = (nullcontext(), nullcontext())
    mock_st.selectbox.side_effect = [before, after]
    mock_st.button.return_value = True

    PortfolioHistoryComponent.render(api, "Study")

    api.data_services.compare_portfolio_revisions.assert_called_once_with(
        "Study", before.revision_id, after.revision_id
    )
    rows = mock_st.dataframe.call_args_list[-1].args[0]
    assert rows == [
        {
            "Area": "Figure settings",
            "Field": "figure[0].raw.title",
            "Change": "Changed",
            "Earlier": "Old",
            "Later": "New",
        }
    ]


@patch("src.web.components.portfolio_history_component.st")
def test_one_version_explains_how_to_enable_comparison(mock_st: MagicMock) -> None:
    from src.web.components.portfolio_history_component import PortfolioHistoryComponent

    api = MagicMock()
    api.data_services.list_portfolio_revisions.return_value = (
        PortfolioRevisionInfo("Study", "a" * 64, 1, "2026-07-20T10:00:00", True, 100, "CSV", 1),
    )

    PortfolioHistoryComponent.render(api, "Study")

    mock_st.info.assert_called_once_with("Save this portfolio again to compare what changed.")
    api.data_services.compare_portfolio_revisions.assert_not_called()
