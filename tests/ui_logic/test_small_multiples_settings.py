"""Behavioral tests for the human-first small-multiples controls."""

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

import pandas as pd


@patch("src.web.components.plotting.settings.small_multiples_settings.st")
def test_disabled_small_multiples_returns_only_the_opt_in(mock_st: MagicMock) -> None:
    from src.web.components.plotting.settings.small_multiples_settings import (
        SmallMultiplesSettingsComponent,
    )

    mock_st.toggle.return_value = False
    result = SmallMultiplesSettingsComponent(4).render({}, pd.DataFrame({"arch": ["x", "a"]}))

    assert result == {"small_multiples_enabled": False}


@patch("src.web.components.plotting.settings.small_multiples_settings.st")
def test_enabled_controls_report_panel_count_and_shared_scales(mock_st: MagicMock) -> None:
    # [test->req~ring5.plots.small-multiples~1]
    from src.web.components.plotting.settings.small_multiples_settings import (
        SmallMultiplesSettingsComponent,
    )

    data = pd.DataFrame(
        {
            "architecture": ["x86", "arm", "x86", "arm"],
            "mode": ["fast", "fast", "safe", "safe"],
            "value": [1.0, 2.0, 3.0, 4.0],
        }
    )
    mock_st.toggle.return_value = True
    mock_st.multiselect.return_value = ["architecture", "mode"]
    mock_st.number_input.side_effect = [2, 280]
    mock_st.columns.return_value = [nullcontext(), nullcontext(), nullcontext()]
    mock_st.checkbox.side_effect = [True, True, False]

    result = SmallMultiplesSettingsComponent(9).render({}, data)

    assert result == {
        "small_multiples_enabled": True,
        "small_multiples_by": ["architecture", "mode"],
        "small_multiples_columns": 2,
        "small_multiples_shared_xaxes": True,
        "small_multiples_shared_yaxes": True,
        "small_multiples_shared_legend": False,
        "small_multiples_panel_height": 280,
    }
    mock_st.caption.assert_called_once_with(
        "4 panels, ordered by their first appearance in the data."
    )
