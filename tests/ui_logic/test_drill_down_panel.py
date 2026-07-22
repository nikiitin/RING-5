"""Human-first drill-down result panel tests."""

from unittest.mock import MagicMock, patch

import pandas as pd

from src.core.models.visualization.drill_down_result import DrillDownResult
from src.web.components.plotting.drill_down_panel import DrillDownPanel, point_label

_MODULE = "src.web.components.plotting.drill_down_panel"


@patch(f"{_MODULE}.st")
def test_result_panel_explains_filters_rows_and_back_action(mock_st: MagicMock) -> None:
    mock_st.container.return_value = MagicMock()
    mock_st.button.return_value = True
    result = DrillDownResult(
        2,
        (("workload", "mcf"),),
        pd.DataFrame({"seed": [0, 1], "ipc": [1.0, 1.2]}),
    )

    close = DrillDownPanel.render_result(result, "IPC · x=mcf, y=1.1")

    assert close is True
    mock_st.metric.assert_called_once_with("Matching rows", 2)
    displayed = mock_st.dataframe.call_args.args[0]
    assert displayed["seed"].tolist() == [0, 1]
    mock_st.button.assert_called_once_with(
        ":material/arrow_back: Back to full plot",
        key="plot.2.drill_down.close",
    )


def test_point_label_keeps_trace_and_coordinates_readable() -> None:
    assert point_label({"traceName": "IPC", "x": "mcf", "y": 1.2}) == ("IPC · x=mcf, y=1.2")
