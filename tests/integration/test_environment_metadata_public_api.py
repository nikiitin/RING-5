"""Public API coverage for save-time execution-environment provenance."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_portfolios")]


def test_saved_environment_is_public_and_matches_same_runtime(portfolios_dir: Path) -> None:
    # [test->req~ring5.portfolio.environment-metadata~1]
    with ring5.Session() as session:
        current = session.environment_metadata(refresh=True)
        session.save_portfolio("environment_probe")
        comparison = session.compare_portfolio_environment("environment_probe")

    document = json.loads((portfolios_dir / "environment_probe.json").read_text())
    assert document["schema_version"] == 4
    assert document["environment_metadata"] == current.to_dict()
    assert isinstance(current, ring5.EnvironmentMetadata)
    assert isinstance(comparison, ring5.EnvironmentComparison)
    assert all(isinstance(item, ring5.EnvironmentDifference) for item in comparison.differences)
    assert comparison.recorded_available is True
    assert comparison.exact_match is True
    assert comparison.changed_count == 0


def test_legacy_portfolio_environment_is_explicitly_not_recorded(
    portfolios_dir: Path,
) -> None:
    (portfolios_dir / "legacy_environment.json").write_text(
        json.dumps({"schema_version": 2, "plots": []})
    )

    with ring5.Session() as session:
        comparison = session.compare_portfolio_environment("legacy_environment")

    assert comparison.recorded_available is False
    assert comparison.exact_match is False
    assert {item.status for item in comparison.differences} == {"not-recorded"}


def test_portfolio_environment_errors_remain_in_public_error_hierarchy(
    portfolios_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (portfolios_dir / "bad_environment.json").write_text(
        json.dumps({"schema_version": 3, "environment_metadata": [], "plots": []})
    )
    (portfolios_dir / "future_environment.json").write_text(json.dumps({"schema_version": 5}))

    with ring5.Session() as session:
        with pytest.raises(ring5.PortfolioError, match="invalid environment metadata"):
            session.compare_portfolio_environment("bad_environment")
        with pytest.raises(ring5.PortfolioVersionError, match="newer than this RING-5"):
            session.compare_portfolio_environment("future_environment")
        with pytest.raises(ring5.PortfolioError, match="not found"):
            session.compare_portfolio_environment("missing_environment")

        def fail_read(_name: str) -> Any:
            raise OSError("storage unavailable")

        monkeypatch.setattr(session.api.data_services, "load_portfolio", fail_read)
        with pytest.raises(ring5.PortfolioError, match="could not be read"):
            session.compare_portfolio_environment("unreadable_environment")
