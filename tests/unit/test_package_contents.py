"""Tests for distribution runtime-file validation."""

from pathlib import Path

import pytest

from scripts import check_package_contents


def test_missing_runtime_files_reports_only_absent_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(check_package_contents, "RUNTIME_FILES", frozenset({"a", "b"}))

    assert check_package_contents.missing_runtime_files({"a", "extra"}) == ["b"]


def test_find_single_rejects_stale_artifacts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(check_package_contents, "DIST_DIR", tmp_path)
    (tmp_path / "one.whl").touch()
    (tmp_path / "two.whl").touch()

    with pytest.raises(ValueError, match="found 2"):
        check_package_contents.find_single("*.whl")
