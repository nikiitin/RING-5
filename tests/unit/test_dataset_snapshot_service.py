"""Exactness, integrity, and lifecycle tests for reusable dataset snapshots."""

import json
from pathlib import Path
from unittest.mock import patch
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
import pandas as pd
import pytest

from src.core.models import ColumnSemantics, DatasetSemantics
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
