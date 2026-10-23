"""Application-boundary remote source review tests."""

from __future__ import annotations

from src.core.application_api import ApplicationAPI
from src.core.models import HttpSource, RemoteDownload, RemoteSourcePolicy
from src.core.services.remote_source_service import RemoteSourceService


class _Adapter:
    def fetch(self, source: object, policy: RemoteSourcePolicy) -> RemoteDownload:
        assert isinstance(source, HttpSource)
        assert policy.allowed_hosts == ("data.example",)
        return RemoteDownload(
            adapter="http",
            display_uri="https://data.example/results.csv",
            file_name="results.csv",
            content_type="text/csv",
            content=b"benchmark,ipc\nalpha,1.25\n",
        )


def test_remote_download_is_staged_for_review_before_load() -> None:
    # [test->req~ring5.ingestion.remote-sources~1]
    api = ApplicationAPI(remote_source_service=RemoteSourceService({"http": _Adapter()}))
    try:
        upload = api.fetch_remote_source(
            HttpSource("https://data.example/results.csv"),
            RemoteSourcePolicy(("data.example",)),
        )

        assert api.state_manager.get_data() is None
        assert upload.origin_display == "https://data.example/results.csv"
        assert upload.import_path is not None
        preview = api.preview_import(upload.import_path)
        assert api.state_manager.get_data() is None

        data = api.load_import_preview(preview)
        assert data.to_dict("records") == [{"benchmark": "alpha", "ipc": 1.25}]
    finally:
        api.state_manager.clear_data()


def test_remote_bundle_uses_the_verified_browser_upload_boundary(tmp_path, monkeypatch) -> None:
    from src.core.services.data_services.portfolio_service import PortfolioService
    from src.core.services.data_services.path_service import PathService
    from src.core.services.portfolio_bundle_service import PortfolioBundleService
    from src.core.services.remote_source_service import _safe_file_name

    monkeypatch.setenv("RING5_DATA_DIR", str(tmp_path))
    PathService.reset_caches()
    source_api = ApplicationAPI()
    try:
        portfolio = PortfolioService(source_api.state_manager).serialize_workspace(None, [], {}, 0)
        bundle = PortfolioBundleService.create("paper", portfolio)
    finally:
        source_api.close()

    class BundleAdapter:
        def fetch(self, source, policy):
            name = _safe_file_name(source.file_name, "paper.ring5-bundle")
            return RemoteDownload(
                adapter="http",
                display_uri=source.url,
                file_name=name,
                content_type="application/zip",
                content=bundle,
            )

    api = ApplicationAPI(remote_source_service=RemoteSourceService({"http": BundleAdapter()}))
    try:
        upload = api.fetch_remote_source(
            HttpSource("https://data.example/paper.ring5-bundle"),
            RemoteSourcePolicy(("data.example",)),
        )
        assert upload.kind == "bundle"
        assert upload.origin_display == "https://data.example/paper.ring5-bundle"
        assert api.state_manager.get_data() is None
        report = api.restore_browser_portfolio_bundle(upload)
        assert report.complete
    finally:
        api.state_manager.clear_data()
        api.close()
        PathService.reset_caches()
