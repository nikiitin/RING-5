"""Exactness, integrity, and lifecycle tests for reusable dataset snapshots."""

import json
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
import pytest

from src.core.models import ColumnSemantics, DatasetSemantics
from src.core.common.content_identity import frame_signature
from src.core.state.repositories.data_repository import DataRepository
from src.core.services.data_services.dataset_snapshot_service import DatasetSnapshotService
from src.core.services.data_services.path_service import PathService
from src.core.services.managers.semantic_metadata_service import SemanticMetadataService


@pytest.fixture
def snapshots_dir(tmp_path: Path) -> Path:
    """Provide isolated storage for snapshot service calls."""
    directory = tmp_path / "dataset_snapshots"
    directory.mkdir()
    return directory


def _representative_frame() -> pd.DataFrame:
    data = pd.DataFrame(
        {
            "nullable_integer": pd.Series([1, None], dtype="Int64"),
            "exact_float": [np.nextafter(1.0, 2.0), np.nan],
            "text": pd.Series(["α", None], dtype="string"),
            "category": pd.Categorical(
                ["fast", "slow"], categories=["fast", "slow", "unknown"], ordered=True
            ),
            "timestamp": pd.to_datetime(["2026-01-01", "2026-01-02"], utc=True),
            "duration": pd.to_timedelta([1, 2], unit="D"),
        }
    )
    data.index = pd.Index([10, 20], name="run")
    data.columns.name = "measurement"
    return data


def test_round_trip_preserves_multi_level_axes(snapshots_dir: Path) -> None:
    rows = pd.MultiIndex.from_tuples(
        [("a", 1), ("b", 2)],
        names=["benchmark", "seed"],
    )
    columns = pd.MultiIndex.from_tuples(
        [("cpu", "ipc"), ("cpu", "cycles")],
        names=["component", "metric"],
    )
    data = pd.DataFrame([[1.0, 10], [2.0, 20]], index=rows, columns=columns)
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot(
            "multi-axis",
            data,
            source_dataset="source",
        )
        _, loaded = DatasetSnapshotService.load_snapshot("multi-axis")

    pd.testing.assert_frame_equal(loaded, data)


def test_save_list_load_overwrite_and_delete_exact_snapshot(snapshots_dir: Path) -> None:
    # [test->req~ring5.data.dataset-snapshots~1]
    data = _representative_frame()
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        saved = DatasetSnapshotService.save_snapshot(
            "parsed/results",
            data,
            source_dataset="all runs",
        )
        listed = DatasetSnapshotService.list_snapshots()
        loaded_info, loaded = DatasetSnapshotService.load_snapshot("parsed/results")

        assert listed == (saved,)
        assert loaded_info == saved
        assert saved.row_count == 2
        assert saved.column_count == 6
        assert saved.fingerprint.startswith("sha256:")
        assert saved.size_bytes > 0
        pd.testing.assert_frame_equal(loaded, data)

        with pytest.raises(FileExistsError, match="already exists"):
            DatasetSnapshotService.save_snapshot(
                "parsed/results",
                data,
                source_dataset="all runs",
            )
        replaced = DatasetSnapshotService.save_snapshot(
            "parsed/results",
            data.iloc[:1],
            source_dataset="all runs",
            overwrite=True,
        )
        assert replaced.row_count == 1

        DatasetSnapshotService.delete_snapshot("parsed/results")
        assert DatasetSnapshotService.list_snapshots() == ()


def test_snapshot_retains_semantic_labels_and_units(snapshots_dir: Path) -> None:
    # [test->req~ring5.data.semantic-units~1]
    data = SemanticMetadataService.attach(
        pd.DataFrame({"latency": [1.0, 2.0]}),
        DatasetSemantics((ColumnSemantics("latency", "Mean latency", "ms"),)),
    )
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot("semantic", data, source_dataset="results")
        _, loaded = DatasetSnapshotService.load_snapshot("semantic")

    assert SemanticMetadataService.inspect(loaded) == DatasetSemantics(
        (ColumnSemantics("latency", "Mean latency", "ms"),)
    )


def test_load_rejects_checksum_and_fingerprint_tampering(snapshots_dir: Path) -> None:
    # [test->req~ring5.data.dataset-snapshots~1]
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot(
            "verified",
            pd.DataFrame({"value": [1.0]}),
            source_dataset="source",
        )
        path = next(snapshots_dir.glob("*.ring5-snapshot"))
        with ZipFile(path) as archive:
            manifest = archive.read("manifest.json")
            payload = archive.read("data.json")
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", manifest)
            archive.writestr("data.json", payload + b" ")
        with pytest.raises(ValueError, match="payload checksum"):
            DatasetSnapshotService.load_snapshot("verified")

        parsed_manifest = json.loads(manifest)
        parsed_manifest["fingerprint"] = f"sha256:{'0' * 64}"
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(parsed_manifest))
            archive.writestr("data.json", payload)
        with pytest.raises(ValueError, match="fingerprint verification"):
            DatasetSnapshotService.load_snapshot("verified")


def test_snapshot_validation_and_unreadable_catalog_entries(snapshots_dir: Path) -> None:
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        with pytest.raises(ValueError, match="non-empty"):
            DatasetSnapshotService.save_snapshot(
                "",
                pd.DataFrame({"value": [1]}),
                source_dataset="source",
            )
        with pytest.raises(FileNotFoundError, match="does not exist"):
            DatasetSnapshotService.load_snapshot("missing")

        (snapshots_dir / "broken.ring5-snapshot").write_bytes(b"not a zip")
        assert DatasetSnapshotService.list_snapshots() == ()


@pytest.mark.parametrize("empty", [False, True])
def test_snapshot_preserves_range_axes_and_canonical_lineage_identity(
    snapshots_dir: Path, empty: bool
) -> None:
    # [test->req~ring5.data.dataset-snapshots~1]
    rows = pd.RangeIndex(10, 10 if empty else 14, 2, name="run")
    columns = pd.RangeIndex(5, 9, 2, name="measurement")
    data = pd.DataFrame(index=rows, columns=columns, dtype="float64")
    data.loc[:, :] = 1.5
    repository = DataRepository()
    repository.add_dataset("source", data)
    revision = repository.get_dataset_lineage("source").revisions[0]

    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        saved = DatasetSnapshotService.save_snapshot("ranges", data, source_dataset="source")
        _, restored = DatasetSnapshotService.load_snapshot("ranges")

    assert isinstance(restored.index, pd.RangeIndex)
    assert isinstance(restored.columns, pd.RangeIndex)
    pd.testing.assert_frame_equal(restored, data)
    assert saved.fingerprint == revision.fingerprint == frame_signature(data)


def test_snapshot_preserves_explicit_empty_semantic_metadata(snapshots_dir: Path) -> None:
    data = SemanticMetadataService.attach(pd.DataFrame({"value": [1]}), DatasetSemantics())
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot("empty-semantics", data, source_dataset="source")
        _, restored = DatasetSnapshotService.load_snapshot("empty-semantics")
    assert restored.attrs == data.attrs


def test_snapshot_retains_supported_binary_and_complex_values(snapshots_dir: Path) -> None:
    data = pd.DataFrame({"value": pd.Series([b"1", complex(1, 2)], dtype=object)})
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot("typed", data, source_dataset="source")
        _, restored = DatasetSnapshotService.load_snapshot("typed")
    assert type(restored["value"].iloc[0]) is bytes
    assert type(restored["value"].iloc[1]) is complex
    assert frame_signature(restored) == frame_signature(data)


@pytest.mark.parametrize("kind", ["unsupported", "cyclic"])
def test_snapshot_rejects_unsavable_attributes_before_publication(
    snapshots_dir: Path, kind: str
) -> None:
    original = pd.DataFrame({"value": [1]})
    changed = original.copy()
    if kind == "unsupported":
        changed.attrs = {"custom": object()}
    else:
        cycle: list[object] = []
        cycle.append(cycle)
        changed.attrs = {"custom": cycle}

    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot("kept", original, source_dataset="source")
        path = next(snapshots_dir.glob("*.ring5-snapshot"))
        before = path.read_bytes()
        with pytest.raises(ValueError, match="(?i)attributes|unsupported|recursive|budget"):
            DatasetSnapshotService.save_snapshot(
                "kept", changed, source_dataset="source", overwrite=True
            )
        assert path.read_bytes() == before
        with pytest.raises(ValueError, match="(?i)attributes|unsupported|recursive|budget"):
            DatasetSnapshotService.save_snapshot("rejected", changed, source_dataset="source")
        assert list(snapshots_dir.glob("*.ring5-snapshot")) == [path]


def test_snapshot_rejects_retired_identity_format(snapshots_dir: Path) -> None:
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot(
            "current", pd.DataFrame({"value": [1]}), source_dataset="source"
        )
        path = next(snapshots_dir.glob("*.ring5-snapshot"))
        with ZipFile(path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            payload = archive.read("data.json")
        assert manifest["format_version"] == 3
        manifest["format_version"] = 2
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("data.json", payload)
        with pytest.raises(ValueError, match="Unsupported dataset snapshot version"):
            DatasetSnapshotService.load_snapshot("current")


def test_snapshot_preserves_typed_custom_attributes(snapshots_dir: Path) -> None:
    data = pd.DataFrame({"value": [1]})
    data.attrs = {"custom": {"run": np.int32(7), "values": [None, b"x", 1j]}}
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot("attrs", data, source_dataset="source")
        _, restored = DatasetSnapshotService.load_snapshot("attrs")
    assert frame_signature(restored) == frame_signature(data)
    assert type(restored.attrs["custom"]["run"]) is np.int32


@pytest.mark.parametrize("field", ["unexpected", "row_count", "column_count"])
def test_snapshot_manifest_rejects_unknown_keys_and_boolean_dimensions(
    snapshots_dir: Path, field: str
) -> None:
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot(
            "strict", pd.DataFrame({"x": [1]}), source_dataset="source"
        )
        path = next(snapshots_dir.glob("*.ring5-snapshot"))
        with ZipFile(path) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            payload = archive.read("data.json")
        manifest[field] = True
        with ZipFile(path, "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest))
            archive.writestr("data.json", payload)
        with pytest.raises(ValueError, match="manifest field"):
            DatasetSnapshotService.load_snapshot("strict")


def test_snapshot_rejects_duplicate_archive_members(snapshots_dir: Path) -> None:
    with patch.object(PathService, "get_dataset_snapshots_dir", return_value=snapshots_dir):
        DatasetSnapshotService.save_snapshot(
            "strict", pd.DataFrame({"x": [1]}), source_dataset="source"
        )
        path = next(snapshots_dir.glob("*.ring5-snapshot"))
        with ZipFile(path) as archive:
            manifest = archive.read("manifest.json")
        with ZipFile(path, "a") as archive, pytest.warns(UserWarning, match="Duplicate name"):
            archive.writestr("manifest.json", manifest)
        with pytest.raises(ValueError, match="archive members"):
            DatasetSnapshotService.load_snapshot("strict")
