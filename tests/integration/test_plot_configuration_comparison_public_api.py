"""Public API coverage for plot configuration comparison."""

from __future__ import annotations

import pandas as pd
import pytest

import ring5

pytestmark = pytest.mark.public_api


def test_public_comparison_accepts_plot_objects_and_ids_without_mutation() -> None:
    # [test->req~ring5.plots.configuration-comparison~1]
    data = pd.DataFrame({"benchmark": ["A"], "ipc": [1.0]})
    with ring5.Session() as session:
        source = session.create_plot(
            "bar",
            data=data,
            config={"x": "benchmark", "y": "ipc", "title": "Source"},
            name="Source",
        )
        destination = session.create_plot(
            "bar",
            data=data.copy(),
            config={"x": "benchmark", "y": "ipc", "title": "Destination"},
            name="Destination",
        )

        result = session.compare_plot_configurations(source, destination)
        assert isinstance(result, ring5.PlotConfigurationComparison)
        assert isinstance(result.differences[0], ring5.ConfigurationDifference)
        assert result.differences[0].path == "title"
        assert result.can_replace
        assert source.config["title"] == "Source"
        assert destination.config["title"] == "Destination"

        reverse = session.compare_plot_configurations(
            destination.plot_id,
            source.plot_id,
        )
        assert reverse.source_name == "Destination"


def test_public_comparison_reports_typed_reference_errors() -> None:
    data = pd.DataFrame({"x": ["A"], "y": [1.0]})
    with ring5.Session() as session:
        plot = session.create_plot("bar", data=data, config={"x": "x", "y": "y"})
        with pytest.raises(ring5.DataValidationError, match="unknown plot IDs"):
            session.compare_plot_configurations(999, plot)
        with pytest.raises(ring5.DataValidationError, match="two different plots"):
            session.compare_plot_configurations(plot, plot)
