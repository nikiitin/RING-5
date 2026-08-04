"""Regression tests for resource-safe runtime defaults."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_streamlit_uses_polling_file_watcher() -> None:
    """Keep ``make run`` away from watchdog's thread-per-directory mode."""
    repository_root = Path(__file__).resolve().parents[2]
    config_path = repository_root / ".streamlit" / "config.toml"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))

    assert config["server"]["fileWatcherType"] == "poll"
