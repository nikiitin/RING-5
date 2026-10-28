"""Validate the installed tutorial resource at the same document boundary."""

import gzip
import json
from pathlib import Path

import pytest

from src.core.services import example_portfolio_service as examples


def test_resource_loads_are_independent_and_integrity_checked() -> None:
    first = examples.load_example_portfolio()
    first["config"]["description"] = "caller edit"
    second = examples.load_example_portfolio()
    assert second["config"]["description"] != "caller edit"
    assert len(second["plots"]) == 17
    assert second["loaded_origin"] is None
    assert not second["use_parser"]


@pytest.mark.parametrize("invalid", ["not-json", "[]", "corrupt", "retired"])
def test_invalid_bundled_documents_fail_clearly(
    invalid: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = examples.load_example_portfolio()
    if invalid == "corrupt":
        value["config"]["description"] = "changed without updating checksums"
        content = json.dumps(value)
    elif invalid == "retired":
        value["schema_version"] = 12
        content = json.dumps(value)
    else:
        content = invalid
    directory = tmp_path / "resources"
    directory.mkdir()
    (directory / "example-portfolio.json.gz").write_bytes(gzip.compress(content.encode()))
    monkeypatch.setattr(examples, "files", lambda package: tmp_path)
    with pytest.raises(ValueError):
        examples.load_example_portfolio()


@pytest.mark.parametrize("invalid", ["truncated", "deflate"])
def test_invalid_compression_uses_the_resource_error_contract(
    invalid: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    compressed = gzip.compress(b"{}")
    if invalid == "truncated":
        compressed = compressed[:-4]
    else:
        compressed = compressed[:10] + b"\xff" + compressed[11:]
    directory = tmp_path / "resources"
    directory.mkdir()
    (directory / "example-portfolio.json.gz").write_bytes(compressed)
    monkeypatch.setattr(examples, "files", lambda package: tmp_path)
    with pytest.raises(ValueError, match="compression is invalid"):
        examples.load_example_portfolio()
    import ring5

    with ring5.Session() as session:
        with pytest.raises(ring5.PortfolioError, match="compression is invalid"):
            session.load_example_portfolio()
