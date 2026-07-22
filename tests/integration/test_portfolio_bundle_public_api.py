"""Public portable analysis bundle workflow."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

import ring5
from src.core.services.data_services.path_service import PathService

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_portfolios")]


def test_export_inspect_read_and_restore_portable_bundle(
    portfolios_dir: Path,
    tmp_path: Path,
) -> None:
    # [test->req~ring5.portfolio.portable-bundles~1]
    snapshots = tmp_path / "snapshots"
    snapshots.mkdir()
    data = pd.DataFrame({"benchmark": ["alpha", "beta"], "ipc": [1.25, 1.5]})
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots):
        with ring5.Session() as session:
            session.api.state_manager.set_data(data)
            session.save_dataset_snapshot("exact-data")
            session.save_portfolio("paper-a")
            payload = session.export_portfolio_bundle(
                "paper-a",
                snapshot_name="exact-data",
                results={"figures/ipc.svg": b"<svg/>", "report.html": b"<html/>"},
                signing_key="shared transfer secret",
                signing_key_id="lab-transfer",
            )

            inspected = session.inspect_portfolio_bundle(payload)
            contents = session.read_portfolio_bundle(
                payload,
                signing_key="shared transfer secret",
                require_signature=True,
            )
            session.api.state_manager.set_data(pd.DataFrame({"changed": [1]}))
            restored = session.restore_portfolio_bundle(
                payload,
                signing_key="shared transfer secret",
                require_signature=True,
            )

            assert isinstance(inspected, ring5.PortfolioBundleInfo)
            assert inspected.portfolio_integrity.status == "signature-unverified"
            assert isinstance(contents, ring5.PortfolioBundleContents)
            assert isinstance(contents.info.artifacts[0], ring5.PortfolioBundleArtifact)
            assert isinstance(contents.results[0], ring5.PortfolioBundleResult)
            assert contents.info.portfolio_integrity.status == "signature-valid"
            assert contents.info.dataset_snapshot is not None
            assert contents.info.result_names == ("figures/ipc.svg", "report.html")
            assert restored.complete
            pd.testing.assert_frame_equal(
                session.api.state_manager.get_data().reset_index(drop=True),
                data,
                check_dtype=False,
            )


def test_portable_bundle_errors_use_public_portfolio_error(
    portfolios_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # [test->req~ring5.portfolio.portable-bundles~1]
    with ring5.Session() as session:
        with pytest.raises(ring5.PortfolioError, match="could not be created"):
            session.export_portfolio_bundle("missing")
        with pytest.raises(ring5.PortfolioError, match="could not be inspected"):
            session.inspect_portfolio_bundle(b"not a bundle")
        with pytest.raises(ring5.PortfolioError, match="could not be read"):
            session.read_portfolio_bundle(b"not a bundle")

        session.save_portfolio("restore-error")
        payload = session.export_portfolio_bundle("restore-error")
        monkeypatch.setattr(
            session.api.state_manager,
            "restore_session",
            lambda _portfolio: (_ for _ in ()).throw(ValueError("invalid state")),
        )
        with pytest.raises(ring5.PortfolioError, match="could not be restored"):
            session.restore_portfolio_bundle(payload)
