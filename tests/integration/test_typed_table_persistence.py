"""One exact table representation across every portfolio persistence boundary."""

import copy
import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from tests.helpers.tables import scientific_frames
from src.core.common.content_identity import frame_signature
from src.core.services.autosave_recovery_service import AutosaveRecoveryService
from src.core.services.browser_upload_service import BrowserUploadService
from src.core.services.data_services.dataset_snapshot_service import DatasetSnapshotService
from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.common.typed_table_codec import TypedTableCodec
from src.core.services.portfolio_bundle_service import PortfolioBundleService
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.fixture
def storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for method, directory in (
        ("get_dataset_snapshots_dir", "snapshots"),
        ("get_recovery_drafts_dir", "recovery"),
    ):
        path = tmp_path / directory
        path.mkdir()
        monkeypatch.setattr(PathService, method, lambda path=path: path)
    return tmp_path


def _assert_frame(actual: pd.DataFrame | None, expected: pd.DataFrame) -> None:
    pd.testing.assert_frame_equal(actual, expected)
    assert frame_signature(actual) == frame_signature(expected)


@pytest.mark.parametrize("frame", scientific_frames(), ids=lambda f: str(f.dtypes.tolist()))
def test_every_container_round_trips_the_same_typed_frames(
    storage: Path, frame: pd.DataFrame
) -> None:
    state = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    state.set_data(frame)
    plot = PlotFactory.create_plot("bar", 0, "typed")
    source = pd.DataFrame({"source_only": ["original", "rows"]})
    plot.replace_source_data(source)
    plot.replace_processed_data(frame)
    state.set_plots([plot])
    state.set_plot_counter(1)
    service = PortfolioService(state, portfolios_dir=storage / "portfolios")
    service.save_portfolio("typed", frame, [plot], {}, 1, signing_key="secret")
    loaded = service.load_portfolio("typed", signing_key="secret", require_signature=True)
    _assert_frame(TypedTableCodec.decode(loaded["data"]), frame)

    target = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    assert target.restore_session(loaded).complete
    _assert_frame(target.get_data(), frame)
    restored_plot = target.get_plots()[0]
    _assert_frame(restored_plot.source_data, source)
    _assert_frame(restored_plot.processed_data, frame)

    revision = service.list_portfolio_revisions("typed")[0]
    retained = service.load_portfolio_revision("typed", revision.revision_id)
    _assert_frame(TypedTableCodec.decode(retained["data"]), frame)

    saved = DatasetSnapshotService.save_snapshot("typed", frame, source_dataset="source")
    _, snapshot_frame = DatasetSnapshotService.load_snapshot("typed")
    _assert_frame(snapshot_frame, frame)
    assert saved.fingerprint == frame_signature(frame)

    payload = service.export_portfolio_bytes("typed")
    bundle = PortfolioBundleService.create(
        "typed",
        payload,
        dataset_snapshot=("typed", DatasetSnapshotService.export_snapshot("typed")),
    )
    contents = PortfolioBundleService.read(bundle, signing_key="secret", require_signature=True)
    _assert_frame(TypedTableCodec.decode(contents.portfolio["data"]), frame)

    upload = BrowserUploadService.inspect(
        "typed.json",
        "application/json",
        payload,
        storage / "uploads",
    )
    assert upload.portfolio_has_data
    uploaded = BrowserUploadService.load_portfolio(
        upload, signing_key="secret", require_signature=True
    )
    _assert_frame(TypedTableCodec.decode(uploaded["data"]), frame)

    capture = AutosaveRecoveryService.capture(state, "typed-owner")
    assert capture is not None
    recovery = AutosaveRecoveryService.load("typed-owner", capture.draft.draft_id)
    _assert_frame(TypedTableCodec.decode(recovery["data"]), frame)


def test_rejected_frames_leave_files_revisions_drafts_and_workspace_unchanged(
    storage: Path,
) -> None:
    original = pd.DataFrame({"value": pd.Series([1, None], dtype="Int64")})
    state = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    state.set_data(original)
    service = PortfolioService(state, portfolios_dir=storage / "portfolios")
    service.save_portfolio("kept", original, [], {}, 0)
    path = storage / "portfolios" / "kept.json"
    before = path.read_bytes()
    revisions = service.list_portfolio_revisions("kept")
    invalid = original.copy()
    invalid.attrs = {"unsupported": object()}
    with pytest.raises(ValueError):
        service.save_portfolio("kept", invalid, [], {}, 0)
    assert path.read_bytes() == before
    assert service.list_portfolio_revisions("kept") == revisions

    malformed = json.loads(before)
    malformed["data"]["index"]["step"] = 0
    malformed["integrity_manifest"] = PortfolioIntegrityService.create_manifest(malformed)
    with pytest.raises(ValueError, match="typed table"):
        state.restore_session(malformed)
    _assert_frame(state.get_data(), original)
    with pytest.raises(ValueError):
        BrowserUploadService.inspect(
            "bad.json", "application/json", json.dumps(malformed).encode(), storage / "rejected"
        )
    assert not list((storage / "rejected").rglob("*"))

    state.set_data(invalid)
    with pytest.raises(ValueError):
        AutosaveRecoveryService.capture(state, "rejected-owner")
    assert AutosaveRecoveryService.list_drafts("rejected-owner") == ()


@pytest.mark.parametrize("field", ["data", "source_data", "processed_data"])
def test_typed_table_tampering_is_covered_by_integrity_sections(field: str) -> None:
    state = RepositoryStateManager()
    plot = PlotFactory.create_plot("bar", 0, "typed")
    plot.replace_source_data(pd.DataFrame({"x": [1]}))
    plot.replace_processed_data(pd.DataFrame({"x": [2]}))
    original = json.loads(
        PortfolioService(state).serialize_workspace(
            pd.DataFrame({"x": [3]}), [plot], {}, 1, signing_key="secret"
        )
    )
    changed = copy.deepcopy(original)
    table: dict[str, Any] = changed["data"] if field == "data" else changed["plots"][0][field]
    table["values"][0][0] += 1
    report = PortfolioIntegrityService.verify(changed, signing_key="secret")
    assert report.status == "modified"
    expected_section = "inputs" if field == "data" else "outputs"
    assert any(
        section.name == expected_section and not section.matches for section in report.sections
    )


def test_public_portfolio_replay_renders_typed_tables_with_both_engines(
    storage: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import matplotlib.pyplot as plt
    import ring5

    portfolios = storage / "public-portfolios"
    portfolios.mkdir()
    monkeypatch.setattr(PathService, "get_portfolios_dir", lambda: portfolios)
    data = pd.DataFrame({"label": ["a", "b"], "value": pd.Series([2, 4], dtype="Int64")})
    data.index = pd.Index([10, 20], name="run")
    with ring5.Session() as session:
        session.plot("bar", data=data, config=ring5.FigureSpec(x="label", y_columns=["value"]))
        session.save_portfolio("typed-replay")
    with ring5.Session() as restored:
        assert restored.load_portfolio("typed-replay").complete
        plot = restored.plots[0]
        _assert_frame(plot.processed_data, data)
        plotly = restored.render(plot, engine="plotly")
        assert list(plotly.data[0].y) == [2, 4]
        matplotlib = restored.render(plot, engine="matplotlib")
        assert sorted(patch.get_height() for patch in matplotlib.axes[0].patches) == [2, 4]
        plt.close(matplotlib)


@pytest.mark.parametrize("field", ["data_csv", "data_semantics", "processed_semantics"])
def test_current_portfolio_rejects_retired_table_keys_without_rewriting(
    storage: Path, field: str
) -> None:
    state = RepositoryStateManager()
    plot = PlotFactory.create_plot("bar", 0, "typed")
    service = PortfolioService(state, portfolios_dir=storage / "strict-portfolios")
    service.save_portfolio("current", pd.DataFrame({"x": [1]}), [plot], {}, 1)
    path = storage / "strict-portfolios" / "current.json"
    document = json.loads(path.read_bytes())
    target = document["plots"][0] if field == "processed_semantics" else document
    target[field] = "x\n1\n" if field == "data_csv" else {}
    document["integrity_manifest"] = PortfolioIntegrityService.create_manifest(document)
    raw = json.dumps(document).encode()
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="current typed"):
        service.load_portfolio("current")
    assert path.read_bytes() == raw
