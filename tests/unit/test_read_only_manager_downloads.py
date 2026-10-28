"""Prepared manager downloads retain their result without applying or rerunning it."""

import csv
from io import StringIO
from unittest.mock import MagicMock, call, patch

import pandas as pd

from src.core.services.managers.quality_profile_service import QualityProfileService
from src.web.components.data_managers.comparison import ComparisonManager
from src.web.components.data_managers.quality_profile import QualityProfileManager
from tests.conftest import columns_side_effect


@patch("src.web.components.data_managers.comparison.st")
def test_comparison_downloads_keep_the_same_preview_without_applying_it(mock_st: MagicMock) -> None:
    source = pd.DataFrame(
        {"experiment": ["baseline", "candidate"], "workload": ["a", "a"], "ipc": [1.0, 1.5]}
    )
    preview = pd.DataFrame(
        {"workload": ["a"], "metric": ["ipc"], "outcome": ["unchanged"], "delta": [0.125]}
    )
    before = preview.copy(deep=True)
    api = MagicMock()
    api.state_manager.get_data.return_value = source
    api.has_preview.return_value = True
    api.preview_matches.return_value = True
    api.get_preview.return_value = preview
    api.managers.export_regression_results.side_effect = [
        b'{"result": "unchanged"}',
        b"<testsuite/>",
    ]
    mock_st.columns.side_effect = columns_side_effect
    mock_st.button.return_value = False
    selections = {
        "Experiment column": "experiment",
        "Baseline": "baseline",
        "Candidate": "candidate",
        "Comparison method": "Threshold",
        "Preferred direction": "Higher is better",
        "Threshold unit": "Percentage",
    }
    mock_st.selectbox.side_effect = lambda label, *_args, **_kwargs: selections[label]
    mock_st.multiselect.side_effect = lambda label, *_args, **_kwargs: (
        ["ipc"] if label == "Metrics" else ["workload"]
    )
    mock_st.number_input.return_value = 0.0

    with patch.object(ComparisonManager, "_render_regression_plot"):
        ComparisonManager(api).render()

    downloads = mock_st.download_button.call_args_list
    assert [download.args[0] for download in downloads] == [
        "Download comparison CSV",
        "Download results JSON",
        "Download JUnit XML",
    ]
    assert [download.args[1] for download in downloads] == [
        "workload,metric,outcome,delta\na,ipc,unchanged,0.125\n",
        b'{"result": "unchanged"}',
        b"<testsuite/>",
    ]
    assert all(download.kwargs["on_click"] == "ignore" for download in downloads)
    assert api.managers.export_regression_results.call_args_list == [
        call(preview, "json"),
        call(preview, "junit"),
    ]
    api.confirm_preview.assert_not_called()
    api.clear_preview.assert_not_called()
    mock_st.rerun.assert_not_called()
    pd.testing.assert_frame_equal(preview, before)


@patch("src.web.components.data_managers.quality_profile.st")
def test_quality_download_retains_the_button_generated_profile(mock_st: MagicMock) -> None:
    source = pd.DataFrame({"ipc": [1.0, None, 2.0]})
    report = QualityProfileService.profile(source, expected_types={"ipc": "numeric"})
    api = MagicMock()
    api.state_manager.get_data.return_value = source
    api.managers.profile_data.return_value = report
    mock_st.columns.side_effect = columns_side_effect
    mock_st.multiselect.side_effect = lambda label, *_args, **_kwargs: (
        ["ipc"] if label == "Expected numeric columns" else []
    )
    mock_st.button.return_value = True

    QualityProfileManager(api).render()

    api.managers.profile_data.assert_called_once_with(source, expected_types={"ipc": "numeric"})
    mock_st.download_button.assert_called_once()
    download = mock_st.download_button.call_args
    assert download.args[0] == "Download quality profile"
    assert download.kwargs["on_click"] == "ignore"
    assert download.kwargs["file_name"] == "ring5-data-quality.csv"
    rows = list(csv.DictReader(StringIO(download.args[1])))
    assert len(rows) == 1
    assert rows[0]["name"] == "ipc"
    assert rows[0]["missing"] == "1"
    assert rows[0]["expected_type"] == "numeric"
    api.update_selected_dataset.assert_not_called()
    mock_st.rerun.assert_not_called()
