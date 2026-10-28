"""Failed native chart receipts retain their original timeout and bounded diagnostics."""

from unittest.mock import MagicMock

import pytest
from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from tests.helpers.browser_plot_data import read_native_plotly


@pytest.mark.parametrize("diagnostic_available", [False, True])
def test_native_timeout_preserves_failure_and_records_one_diagnostic(
    diagnostic_available: bool,
) -> None:
    """Diagnostics add context without another native wait or a replacement failure."""
    page = MagicMock()
    failure = PlaywrightTimeoutError("Requested dark figure did not finish")
    page.wait_for_function.side_effect = failure
    if diagnostic_available:
        page.evaluate.return_value = {
            "scriptState": "notRunning",
            "frames": [{"graph": {"paper_bgcolor": "#ffffff", "traces": 1}}],
        }
    else:
        page.evaluate.side_effect = PlaywrightError("Closed page " + "x" * 500)
    with pytest.raises(PlaywrightTimeoutError) as caught:
        read_native_plotly(
            page,
            "Exact figure",
            expected_trace_count=1,
            expected_layout={"paper_bgcolor": "#161a24"},
            timeout=1234,
        )
    assert caught.value is failure
    page.wait_for_function.assert_called_once()
    assert page.wait_for_function.call_args.kwargs["timeout"] == 1234
    assert page.wait_for_function.call_args.kwargs["arg"] == {
        "title": "Exact figure",
        "count": 1,
        "layout": {"paper_bgcolor": "#161a24"},
    }
    page.evaluate.assert_called_once()
    notes = failure.__notes__
    assert len(notes) == 1
    if diagnostic_available:
        assert notes[0].startswith("Native Plotly diagnostic: ")
        assert '"paper_bgcolor": "#ffffff"' in notes[0]
    else:
        assert notes[0].startswith("Native Plotly diagnostic unavailable: Error: Closed page")
        assert len(notes[0]) < 400
    script = page.evaluate.call_args.args[0]
    assert ".slice(0, 8)" in script
    assert ".slice(0, 3)" in script
    assert "_fullLayout" in script and "readyRemainingMs" in script
    page.wait_for_timeout.assert_not_called()


def test_completed_native_chart_does_not_collect_failure_diagnostics() -> None:
    """Successful native receipts keep the same snapshot and perform no extra page work."""
    page = MagicMock()
    expected = {"traces": [{"x": ["a"], "y": [2]}]}
    page.wait_for_function.return_value.json_value.return_value = expected
    assert read_native_plotly(page, "Exact figure") == expected
    page.wait_for_function.assert_called_once()
    page.evaluate.assert_not_called()
