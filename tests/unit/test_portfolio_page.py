"""Tests for portfolio page actions and error states."""

from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd


def _make_col_mock() -> MagicMock:
    col = MagicMock()
    col.__enter__ = MagicMock(return_value=col)
    col.__exit__ = MagicMock(return_value=False)
    return col


def _columns_side_effect(n: int) -> list:
    return [_make_col_mock() for _ in range(n)]


class TestShowPortfolioPage:
    """Tests for show_portfolio_page."""

    @patch("src.web.pages.portfolio.st")
    def test_save_no_data(self, mock_st: MagicMock) -> None:
        # [test->req~ring5.portfolio.save~1]
        """Save button with no data saves config-only portfolio."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = []

        mock_st.fragment.side_effect = lambda func: func
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        # Portfolio save now succeeds even without data (config-only save)
        api.data_services.save_portfolio.assert_called()
        mock_st.toast.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_save_success(self, mock_st: MagicMock) -> None:
        """Save portfolio with data succeeds."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = True
        api.state_manager.get_data.return_value = pd.DataFrame({"a": [1]})
        api.state_manager.get_plots.return_value = []
        api.state_manager.get_config.return_value = {}
        api.state_manager.get_plot_counter.return_value = 0
        api.state_manager.get_csv_path.return_value = None
        api.state_manager.get_parse_variables.return_value = None
        api.data_services.list_portfolios.return_value = []

        mock_st.fragment.side_effect = lambda func: func
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.text_input.return_value = "test_portfolio"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        api.data_services.save_portfolio.assert_called_once()

    @patch("src.web.pages.portfolio.st")
    def test_save_exception(self, mock_st: MagicMock) -> None:
        """Save portfolio exception is handled."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = True
        api.state_manager.get_data.return_value = pd.DataFrame({"a": [1]})
        api.data_services.save_portfolio.side_effect = IOError("disk full")
        api.data_services.list_portfolios.return_value = []
        api.state_manager.get_plots.return_value = []

        mock_st.fragment.side_effect = lambda func: func
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        mock_st.exception.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_load_portfolio(self, mock_st: MagicMock) -> None:
        """Load portfolio triggers restore_session."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = ["p1"]
        api.data_services.load_portfolio.return_value = {"data": {"a": [1]}}
        mock_st.fragment.side_effect = lambda func: func
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.selectbox.return_value = "p1"
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        api.state_manager.restore_session.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_load_portfolio_error(self, mock_st: MagicMock) -> None:
        """Load portfolio error is handled."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = ["p1"]
        api.data_services.load_portfolio.side_effect = ValueError("corrupt")
        mock_st.fragment.side_effect = lambda func: func
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = True
        mock_st.selectbox.return_value = "p1"
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        mock_st.exception.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_no_portfolios_warning(self, mock_st: MagicMock) -> None:
        """No portfolios shows warning."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = []

        mock_st.fragment.side_effect = lambda func: func
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.return_value = False
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        # At least one warning or info was called
        assert mock_st.warning.called or mock_st.info.called

    @patch("src.web.pages.portfolio.st")
    def test_delete_portfolio(self, mock_st: MagicMock) -> None:
        # [test->req~ring5.portfolio.manage~1]
        """Delete button triggers delete_portfolio."""
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.has_data.return_value = False
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = ["p1"]
        mock_st.fragment.side_effect = lambda func: func
        mock_st.columns.side_effect = _columns_side_effect

        def button_side_effect(label: Any, on_click: Any = None, **kwargs: Any) -> int:

            if on_click:
                on_click()
            return True

        mock_st.button.side_effect = button_side_effect
        mock_st.selectbox.return_value = "p1"
        mock_st.text_input.return_value = "test"

        exp = MagicMock()
        exp.__enter__ = MagicMock(return_value=exp)
        exp.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = exp

        show_portfolio_page(api)

        api.data_services.delete_portfolio.assert_called()

    @patch("src.web.pages.portfolio.st")
    def test_incomplete_restore_is_reported(self, mock_st: MagicMock) -> None:
        # [test->req~ring5.portfolio.partial-report~1]
        """The web page reports skipped restore content before rerunning."""
        from src.core.models import RestoreReport
        from src.web.pages.portfolio import show_portfolio_page

        api = MagicMock()
        api.state_manager.get_plots.return_value = []
        api.data_services.list_portfolios.return_value = ["damaged"]
        api.data_services.load_portfolio.return_value = {}
        api.state_manager.restore_session.return_value = RestoreReport(
            data_error="invalid CSV",
            plots_skipped=["plot-a: unknown plot type"],
            parse_variables_skipped=2,
        )
        mock_st.fragment.side_effect = lambda func: func
        mock_st.columns.side_effect = _columns_side_effect
        mock_st.button.side_effect = lambda label, **_kwargs: label == "Load Portfolio"
        mock_st.selectbox.return_value = "damaged"
        mock_st.text_input.return_value = "unused"
        expander = MagicMock()
        expander.__enter__ = MagicMock(return_value=expander)
        expander.__exit__ = MagicMock(return_value=False)
        mock_st.expander.return_value = expander

        show_portfolio_page(api)

        messages = [str(call.args[0]) for call in mock_st.toast.call_args_list]
        assert any("Restore incomplete" in message for message in messages)
        assert any("unknown plot type" in message for message in messages)

    # NOTE: test_save_pipeline and test_apply_pipeline removed —
    # Pipeline save/load is no longer part of the page.


class TestPortfolioEnvironment:
    """Tests for the pre-restore reproducibility comparison."""

    @patch("src.web.pages.portfolio.EnvironmentMetadataService.compare")
    @patch("src.web.pages.portfolio.st")
    def test_environment_comparison_is_human_first(
        self, mock_st: MagicMock, mock_compare: MagicMock
    ) -> None:
        # [test->req~ring5.portfolio.environment-metadata~1]
        from src.core.models import (
            EnvironmentComparison,
            EnvironmentDifference,
            EnvironmentMetadata,
        )
        from src.web.pages.portfolio import _render_environment_comparison

        metadata = EnvironmentMetadata(
            format_version=1,
            ring5_version="1.0.0",
            python_version="3.12.9",
            python_implementation="CPython",
            operating_system="Linux 6.8",
            architecture="x86_64",
        )
        mock_compare.return_value = EnvironmentComparison(
            recorded=metadata,
            current=metadata,
            differences=(EnvironmentDifference("Runtime", "RING-5", "1.0.0", "1.0.0", "match"),),
        )
        expander = _make_col_mock()
        mock_st.expander.return_value = expander
        api = MagicMock()
        api.data_services.load_portfolio.return_value = {"environment_metadata": metadata.to_dict()}

        _render_environment_comparison(api, "paper")

        mock_st.success.assert_called_once_with(
            "Saved environment matches this RING-5 runtime exactly."
        )
        rows = mock_st.dataframe.call_args.args[0]
        assert rows == [
            {
                "Area": "Runtime",
                "Component": "RING-5",
                "Saved": "1.0.0",
                "Current": "1.0.0",
                "Status": "Match",
            }
        ]

    @patch("src.web.pages.portfolio.st")
    def test_environment_status_distinguishes_legacy_and_changed(self, mock_st: MagicMock) -> None:
        from src.core.models import (
            EnvironmentComparison,
            EnvironmentDifference,
            EnvironmentMetadata,
        )
        from src.web.pages.portfolio import _render_environment_status

        current = EnvironmentMetadata(1, "1", "3.12", "CPython", "Linux", "x86_64")
        _render_environment_status(EnvironmentComparison(None, current, ()))
        mock_st.info.assert_called_once()

        changed = EnvironmentDifference("Runtime", "RING-5", "0.9", "1", "changed")
        _render_environment_status(EnvironmentComparison(current, current, (changed,)))
        mock_st.warning.assert_called_once_with(
            "1 saved environment value(s) differ or were not recorded."
        )

    @patch("src.web.pages.portfolio.st")
    def test_unreadable_environment_is_reported(self, mock_st: MagicMock) -> None:
        from src.web.pages.portfolio import _render_environment_comparison

        api = MagicMock()
        api.data_services.load_portfolio.side_effect = ValueError("invalid")

        _render_environment_comparison(api, "broken")

        mock_st.warning.assert_called_once_with("The saved environment could not be inspected.")


class TestPortfolioIntegrity:
    """Tests for human-readable integrity and authentication states."""

    @patch("src.web.pages.portfolio.st")
    def test_integrity_review_distinguishes_checksum_from_signature(
        self,
        mock_st: MagicMock,
    ) -> None:
        # [test->req~ring5.portfolio.signed-manifests~1]
        from src.core.models import PortfolioIntegrityReport, PortfolioIntegritySection
        from src.web.pages.portfolio import _render_integrity_review

        expander = _make_col_mock()
        mock_st.expander.return_value = expander
        mock_st.text_input.return_value = "shared secret"
        api = MagicMock()
        api.data_services.verify_portfolio.return_value = PortfolioIntegrityReport(
            status="signature-unverified",
            message="Checksums match. Signature needs its secret.",
            checksum_valid=True,
            signature_present=True,
            signature_valid=None,
            key_id="lab-key",
            sections=(
                PortfolioIntegritySection("inputs", "a" * 64, "a" * 64, True),
                PortfolioIntegritySection("configuration", "b" * 64, "b" * 64, True),
                PortfolioIntegritySection("outputs", "c" * 64, "c" * 64, True),
            ),
        )

        report, secret = _render_integrity_review(api, "paper")

        assert report is not None
        assert report.status == "signature-unverified"
        assert secret == "shared secret"
        mock_st.warning.assert_called_once_with(report.message)
        assert mock_st.dataframe.call_args.args[0] == [
            {"Content": "Inputs", "Checksum": "Matches"},
            {"Content": "Configuration", "Checksum": "Matches"},
            {"Content": "Outputs", "Checksum": "Matches"},
        ]

    @patch("src.web.pages.portfolio.st")
    def test_integrity_inspection_failure_blocks_without_details(
        self,
        mock_st: MagicMock,
    ) -> None:
        from src.web.pages.portfolio import _render_integrity_review

        api = MagicMock()
        api.data_services.verify_portfolio.side_effect = ValueError("broken")

        report, secret = _render_integrity_review(api, "paper")

        assert report is None
        assert secret is None
        mock_st.error.assert_called_once()


class TestPortablePortfolioBundle:
    """Tests for the human-first portable bundle download workflow."""

    @patch("src.web.pages.portfolio.st")
    def test_prepare_bundle_with_optional_snapshot_then_download(
        self,
        mock_st: MagicMock,
    ) -> None:
        # [test->req~ring5.portfolio.portable-bundles~1]
        from src.core.models import DatasetSnapshotInfo
        from src.web.pages.portfolio import _render_bundle_download

        expander = _make_col_mock()
        mock_st.expander.return_value = expander
        mock_st.session_state = {}
        mock_st.selectbox.return_value = "exact-data"
        mock_st.button.return_value = True
        api = MagicMock()
        api.data_services.list_dataset_snapshots.return_value = (
            DatasetSnapshotInfo(
                name="exact-data",
                source_dataset="results",
                created_at="2026-07-21T10:00:00+00:00",
                row_count=2,
                column_count=1,
                fingerprint="sha256:value",
                size_bytes=128,
                format_version=1,
            ),
        )
        api.data_services.export_portfolio_bundle.return_value = b"bundle"

        _render_bundle_download(api, "paper-a")

        api.data_services.export_portfolio_bundle.assert_called_once_with(
            "paper-a",
            snapshot_name="exact-data",
        )
        mock_st.download_button.assert_called_once()
        assert mock_st.download_button.call_args.kwargs["data"] == b"bundle"
        assert mock_st.download_button.call_args.kwargs["file_name"] == "paper-a.ring5-bundle"
