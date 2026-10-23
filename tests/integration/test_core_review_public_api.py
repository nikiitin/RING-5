"""Public operation boundaries for core-review regressions."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import ring5
from ring5 import _portfolio

pytestmark = pytest.mark.public_api


def test_malformed_pipeline_and_theme_raise_typed_public_errors() -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.PipelineError) as failure:
            session.shape(pd.DataFrame({"x": [1]}), [None])
        assert failure.value.step_index == 0
        with pytest.raises(ring5.DataValidationError):
            session.apply_accessible_theme({"marker_size": "bad"}, "line")


def test_close_releases_session_parse_orchestrator_workspace() -> None:
    session = ring5.Session()
    service = session.api._get_parse_job_service()
    workspace = service.session_dir
    assert workspace.exists()
    session.close()
    assert not workspace.exists()
    session.close()


def test_portfolio_export_allocates_every_collision_without_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class ReplaySession:
        plots = [
            SimpleNamespace(name=name, plot_id=identifier)
            for identifier, name in enumerate(["a_2", "a", "a", "A"])
        ]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def load_portfolio(self, name):
            return SimpleNamespace(plots_skipped=[])

        def render(self, plot, *, engine):
            return str(plot.plot_id)

        def export(self, figure, path, **kwargs):
            Path(path).write_text(figure)
            return path

    monkeypatch.setattr(_portfolio, "Session", ReplaySession)
    written = _portfolio.render_portfolio("test", str(tmp_path))
    assert len({Path(path).name.casefold() for path in written}) == 4
    assert [Path(path).read_text() for path in written] == ["0", "1", "2", "3"]
