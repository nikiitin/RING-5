"""Public portfolio revision listing, comparison, and restoration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

import ring5
from src.core.services.portfolio_migrator import PortfolioVersionError as CoreVersionError

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_portfolios")]


def test_portfolio_revisions_compare_and_restore(portfolios_dir: Path) -> None:
    # [test->req~ring5.portfolio.history-diff~1]
    data = pd.DataFrame({"category": ["A", "B"], "value": [1.0, 2.0]})
    with ring5.Session() as session:
        session.api.state_manager.set_data(data)
        plot = session.create_plot(
            "bar",
            data=data,
            config={"x": "category", "y": "value", "title": "Baseline"},
            name="Baseline bars",
        )
        session.save_portfolio("revision_study")

        plot.name = "Reviewed bars"
        plot.config = {
            "x": "category",
            "y": "value",
            "title": "Reviewed",
            "line_width": 4,
        }
        plot.pipeline = [{"type": "sort", "order_dict": {"category": ["B", "A"]}}]
        session.save_portfolio("revision_study", overwrite=True)

        revisions = session.list_portfolio_revisions("revision_study")
        difference = session.compare_portfolio_revisions(
            "revision_study",
            revisions[0].revision_id,
            revisions[1].revision_id,
        )
        report = session.restore_portfolio_revision(
            "revision_study",
            revisions[0].revision_id,
        )

        assert len(revisions) == 2
        assert isinstance(revisions[0], ring5.PortfolioRevisionInfo)
        assert revisions[1].active
        assert isinstance(difference, ring5.PortfolioDiff)
        assert all(isinstance(entry, ring5.PortfolioDiffEntry) for entry in difference.entries)
        assert {entry.section for entry in difference.entries} >= {
            "pipelines",
            "plots",
            "figure_settings",
        }
        assert difference.change_count == len(difference.entries)
        assert report.complete
        assert session.plots[0].name == "Baseline bars"


def test_portfolio_revision_errors_use_public_types(
    portfolios_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [test->req~ring5.portfolio.history-diff~1]
    with ring5.Session() as session:
        session.save_portfolio("errors")
        revision = session.list_portfolio_revisions("errors")[0]

        with pytest.raises(ring5.PortfolioError, match="64 lowercase"):
            session.restore_portfolio_revision("errors", "bad")
        with pytest.raises(ring5.PortfolioError, match="was not found"):
            session.restore_portfolio_revision("errors", "f" * 64)
        with pytest.raises(ring5.PortfolioError, match="was not found"):
            session.compare_portfolio_revisions("errors", "f" * 64, revision.revision_id)

        def fail_compare_version(_name: str, _before: str, _after: str) -> Any:
            raise CoreVersionError("future comparison")

        monkeypatch.setattr(
            session.api.data_services,
            "compare_portfolio_revisions",
            fail_compare_version,
        )
        with pytest.raises(ring5.PortfolioVersionError, match="future comparison"):
            session.compare_portfolio_revisions(
                "errors", revision.revision_id, revision.revision_id
            )

        def fail_compare_storage(_name: str, _before: str, _after: str) -> Any:
            raise OSError("comparison unavailable")

        monkeypatch.setattr(
            session.api.data_services,
            "compare_portfolio_revisions",
            fail_compare_storage,
        )
        with pytest.raises(ring5.PortfolioError, match="could not be compared"):
            session.compare_portfolio_revisions(
                "errors", revision.revision_id, revision.revision_id
            )

        def fail_history(_name: str) -> Any:
            raise OSError("history unavailable")

        monkeypatch.setattr(
            session.api.data_services,
            "list_portfolio_revisions",
            fail_history,
        )
        with pytest.raises(ring5.PortfolioError, match="history.*could not be read"):
            session.list_portfolio_revisions("errors")

        def fail_version(_name: str, _revision: str) -> Any:
            raise CoreVersionError("future revision")

        monkeypatch.setattr(
            session.api.data_services,
            "load_portfolio_revision",
            fail_version,
        )
        with pytest.raises(ring5.PortfolioVersionError, match="future revision"):
            session.restore_portfolio_revision("errors", revision.revision_id)

        def fail_restore(_data: Any) -> Any:
            raise ValueError("invalid restored state")

        monkeypatch.setattr(
            session.api.data_services,
            "load_portfolio_revision",
            lambda _name, _revision: {"schema_version": 3, "plots": []},
        )
        monkeypatch.setattr(session.api.state_manager, "restore_session", fail_restore)
        with pytest.raises(ring5.PortfolioError, match="could not be restored"):
            session.restore_portfolio_revision("errors", revision.revision_id)
