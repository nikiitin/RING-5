"""Current writer round trips and public rejection before state publication."""

import json
from pathlib import Path

import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_portfolios")]


@pytest.mark.parametrize("version", [None, 1, 2, 3, 4, 5, 7, "6", 6.0, True])
def test_obsolete_schema_is_rejected_before_state_changes(portfolios_dir: Path, version) -> None:
    # [test->req~ring5.portfolio.schema~1]
    with ring5.Session() as session:
        session.save_portfolio("current")
        document = json.loads((portfolios_dir / "current.json").read_text())
        if version is None:
            document.pop("schema_version")
        else:
            document["schema_version"] = version
        target = portfolios_dir / "rejected.json"
        payload = json.dumps(document)
        target.write_text(payload)
        session.api.state_manager.set_config({"review_marker": "preserve"})
        with pytest.raises(ring5.PortfolioVersionError):
            session.load_portfolio("rejected")
        with pytest.raises(ring5.PortfolioVersionError):
            session.verify_portfolio("rejected")
        assert session.api.state_manager.get_config()["review_marker"] == "preserve"
        assert target.read_text() == payload


def test_current_writer_round_trip_retains_provenance(portfolios_dir: Path) -> None:
    with ring5.Session() as session:
        session.save_portfolio("current")
        document = json.loads((portfolios_dir / "current.json").read_text())
        assert document["schema_version"] == 6
        assert document["parser_strategy"] == "simple"
        assert document["simulator"] == "gem5"
        assert document["environment_metadata"]
        assert document["integrity_manifest"]
        assert session.load_portfolio("current").complete
        assert session.verify_portfolio("current").safe_to_restore
