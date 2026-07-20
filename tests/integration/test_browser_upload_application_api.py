"""Application-boundary tests for browser upload confirmation."""

from __future__ import annotations

import json

from src.core.application_api import ApplicationAPI


def test_upload_is_non_mutating_until_confirmed_load_or_restore() -> None:
    # [test->req~ring5.ingestion.browser-upload~1]
    api = ApplicationAPI()
    try:
        upload = api.inspect_browser_upload(
            "measurements.csv",
            "text/csv",
            b"benchmark,ipc\nalpha,1.25\n",
        )
        assert api.state_manager.get_data() is None
        assert upload.import_path is not None
        preview = api.preview_import(upload.import_path)
        assert api.state_manager.get_data() is None

        loaded = api.load_import_preview(preview)
        assert loaded.to_dict("records") == [{"benchmark": "alpha", "ipc": 1.25}]

        portfolio_bytes = json.dumps(
            {
                "schema_version": 3,
                "data_csv": "benchmark,ipc\nbeta,2.5\n",
                "plots": [],
                "plot_counter": 0,
                "config": {},
                "parse_variables": [],
                "use_parser": False,
            }
        ).encode()
        portfolio = api.inspect_browser_upload(
            "analysis.json",
            "application/json",
            portfolio_bytes,
        )
        assert api.state_manager.get_data() is not None
        assert api.state_manager.get_data().iloc[0]["benchmark"] == "alpha"

        report = api.restore_browser_portfolio(portfolio)
        assert report.complete is True
        assert api.state_manager.get_data() is not None
        assert api.state_manager.get_data().iloc[0]["benchmark"] == "beta"
    finally:
        api.state_manager.clear_data()
