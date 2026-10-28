"""Canonical legend labels survive transfers and current portfolio boundaries."""

import copy
import json
from pathlib import Path
from typing import Literal

import pandas as pd
import plotly.graph_objects as go
import pytest

import ring5
from src.core.models.visualization.figure_config import FigureConfig
from src.core.services.browser_upload_service import BrowserUploadService
from src.core.services.data_services.portfolio_service import PortfolioService
from src.core.services.portfolio_bundle_service import PortfolioBundleService
from src.core.services.portfolio_integrity_service import PortfolioIntegrityService
from src.core.services.visualization.plot_transfer_service import copy_plot_content
from src.core.state.repository_state_manager import RepositoryStateManager
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.pages.ui.plotting.base_plot import BasePlot


@pytest.mark.parametrize("field", ["font_size_legend3", "font_sze_title"])
def test_unknown_typography_fields_fail_without_changing_the_source(field: str) -> None:
    payload = {"typography": {"font_size_title": 23, field: 11}}
    before = copy.deepcopy(payload)
    with pytest.raises((TypeError, ValueError), match=field):
        FigureConfig.from_dict(payload)
    assert payload == before


@pytest.mark.parametrize("field", ["legend_mappings", "legend_mappings_by_column"])
def test_unsupported_plot_state_fails_before_restoration_or_upload(
    tmp_path: Path, field: str
) -> None:
    # [test->req~ring5.portfolio.schema~1]
    state = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    original = pd.DataFrame({"benchmark": ["case"], "value": [3]})
    state.set_data(original)
    plot = PlotFactory.create_plot("bar", 1, "Original")
    plot.replace_processed_data(original)
    service = PortfolioService(state, portfolios_dir=tmp_path)
    document = json.loads(service.serialize_workspace(original, [plot], {}, 2))
    document["plots"][0][field] = {"value": "Unsupported"}
    document["integrity_manifest"] = PortfolioIntegrityService.create_manifest(document)
    raw = json.dumps(document, allow_nan=False).encode()

    with pytest.raises(ValueError, match="plot.*field|Plot.*field"):
        PlotFactory.from_dict(document["plots"][0])
    with pytest.raises(ValueError, match="plot.*field|Plot.*field"):
        state.restore_session(document)
    retained = state.get_data()
    assert isinstance(retained, pd.DataFrame)
    pd.testing.assert_frame_equal(retained, original)

    path = tmp_path / "invalid.json"
    path.write_bytes(raw)
    with pytest.raises(ValueError, match="plot.*field|Plot.*field"):
        service.load_portfolio("invalid")
    assert path.read_bytes() == raw
    with pytest.raises(ValueError, match="plot.*field|Plot.*field"):
        PortfolioBundleService.create("invalid", raw)
    destination = tmp_path / "uploads"
    with pytest.raises(ValueError, match="plot.*field|Plot.*field"):
        BrowserUploadService.inspect("invalid.json", "application/json", raw, destination)
    assert not destination.exists()


@pytest.mark.parametrize("engine", ["plotly", "matplotlib"])
def test_legend_labels_survive_configuration_copy_and_portfolio_replay(
    engine: Literal["plotly", "matplotlib"],
) -> None:
    # [test->req~ring5.figure.ordering-renaming~2]
    table = ring5.Table.from_rows(
        [
            {"benchmark": "case", "variant": "A", "value": 2},
            {"benchmark": "case", "variant": "B", "value": 4},
        ]
    )
    with ring5.Session() as session:
        source = session.create_plot(
            "bar",
            data=table,
            config={
                "x": "benchmark",
                "y": "value",
                "color": "variant",
                "show_legend": True,
                "legend_labels": {"A": "Alpha", "B": "Beta"},
            },
        )
        target = session.create_plot(
            "bar", data=table, config={"x": "benchmark", "y": "value", "color": "variant"}
        )
        copy_plot_content(source, target, "configuration")
        source_config = source.config
        source_config["legend_labels"]["A"] = "Changed"
        source.config = source_config
        assert source.config["legend_labels"]["A"] == "Changed"
        assert target.config["legend_labels"] == {"A": "Alpha", "B": "Beta"}
        raw = PortfolioService(session.api.state_manager).serialize_workspace(
            table.frame, [target], {}, 2
        )

    restored = RepositoryStateManager(plot_deserializer=PlotFactory.from_dict)
    assert restored.restore_session(json.loads(raw)).complete
    plot = restored.get_plots()[0]
    assert isinstance(plot, BasePlot)
    with ring5.Session() as session:
        figure = session.render(plot, engine=engine)
    if isinstance(figure, go.Figure):
        names = []
        for trace in figure.data:
            assert isinstance(trace, go.Bar)
            names.append(trace.name)
        assert names == ["Alpha", "Beta"]
    else:
        legend = figure.axes[0].get_legend()
        assert legend is not None
        assert [text.get_text() for text in legend.get_texts()] == ["Alpha", "Beta"]
