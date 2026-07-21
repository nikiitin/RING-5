"""Public portfolio checksum and signature workflow."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.xdist_group("ring5_portfolios")]


def test_public_api_distinguishes_checksums_and_verified_signatures(
    portfolios_dir: Path,
) -> None:
    # [test->req~ring5.portfolio.signed-manifests~1]
    with ring5.Session() as session:
        session.save_portfolio("checksummed")
        checksummed = session.verify_portfolio("checksummed")

        assert isinstance(checksummed, ring5.PortfolioIntegrityReport)
        assert checksummed.status == "checksum-valid"
        assert all(
            isinstance(section, ring5.PortfolioIntegritySection) for section in checksummed.sections
        )
        assert session.load_portfolio("checksummed").complete

        session.save_portfolio(
            "signed",
            signing_key="shared research secret",
            signing_key_id="lab-2026",
        )
        unverified = session.verify_portfolio("signed")
        wrong = session.verify_portfolio("signed", signing_key="wrong secret")
        verified = session.verify_portfolio(
            "signed",
            signing_key="shared research secret",
        )

        assert unverified.status == "signature-unverified"
        assert unverified.key_id == "lab-2026"
        assert wrong.status == "signature-invalid"
        assert verified.status == "signature-valid"
        assert session.load_portfolio(
            "signed",
            signing_key="shared research secret",
            require_signature=True,
        ).complete

        with pytest.raises(ring5.PortfolioError, match="verified signature"):
            session.load_portfolio("signed", require_signature=True)
        with pytest.raises(ring5.PortfolioError, match="does not verify"):
            session.load_portfolio(
                "signed",
                signing_key="wrong secret",
                require_signature=True,
            )


def test_modified_portfolio_is_reported_and_never_restored(portfolios_dir: Path) -> None:
    # [test->req~ring5.portfolio.signed-manifests~1]
    with ring5.Session() as session:
        session.save_portfolio("modified")
        path = portfolios_dir / "modified.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        document["config"]["unexpected"] = True
        path.write_text(json.dumps(document), encoding="utf-8")

        report = session.verify_portfolio("modified")
        assert report.status == "modified"
        assert not report.safe_to_restore
        with pytest.raises(ring5.PortfolioError, match="does not match"):
            session.load_portfolio("modified")


def test_integrity_public_errors_remain_portfolio_errors(portfolios_dir: Path) -> None:
    # [test->req~ring5.portfolio.signed-manifests~1]
    with ring5.Session() as session:
        with pytest.raises(ring5.PortfolioError, match="not found"):
            session.verify_portfolio("missing")
        with pytest.raises(ring5.PortfolioError, match="could not be saved"):
            session.save_portfolio("bad-key", signing_key=b"")

        (portfolios_dir / "not-an-object.json").write_text("[]", encoding="utf-8")
        with pytest.raises(ring5.PortfolioError, match="could not be verified"):
            session.verify_portfolio("not-an-object")
