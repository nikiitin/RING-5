"""Real export settings reach the published artifact and shared byte producer."""

from io import BytesIO
from typing import Any, cast
from unittest.mock import MagicMock

import matplotlib as mpl
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
import pytest
from streamlit.testing.v1 import AppTest

import ring5
from src.core.models.visualization.export_options import TEX_SYSTEMS
from src.web.pages.ui.plotting.download_section import render_download_section

_APP = """
import streamlit as st
from src.web.components.plotting.settings.advanced_settings import AdvancedSettingsComponent
from src.web.components.plotting.settings.engine_settings import EngineSettingsComponent
from src.web.rendering.engine_manager import EngineManager
st.session_state[EngineManager.STATE_KEY] = "matplotlib"
st.session_state["emitted"] = AdvancedSettingsComponent(7, "bar").render(
    {}, render_engine_fn=EngineSettingsComponent(7, "bar").render
)
"""


@pytest.mark.parametrize("compiler", TEX_SYSTEMS)
def test_compiler_widget_reaches_actual_pgf_request_without_inert_controls(
    compiler: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    # [test->req~ring5.figure.matplotlib-tex-system~1]
    app = AppTest.from_string(_APP).run()
    assert not app.exception
    app.selectbox(key="plot.7.widgets.appearance.tex_system").select(compiler).run()
    assert not app.exception
    emitted = app.session_state["emitted"]
    assert emitted["tex_system"] == compiler
    assert not {"download_format", "enable_editable", "latex_extra_preamble"} & emitted.keys()
    assert not {"Default Download Format", "Enable Interactive Editing"} & {
        widget.label for widget in [*app.selectbox, *app.checkbox]
    }
    assert emitted["export_scale"] == 1

    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table.from_rows([{"kind": "a", "value": 3.0}, {"kind": "b", "value": 4.0}]),
            config={"x": "kind", "y": "value", **emitted},
        )
        figure = session.render(plot, engine="matplotlib")
        assert isinstance(figure, Figure)
        calls: list[dict[str, Any]] = []

        def savefig(buffer: BytesIO, **kwargs: Any) -> None:
            calls.append(kwargs)
            assert mpl.rcParams["pgf.texsystem"] == compiler
            assert mpl.rcParams["pgf.preamble"] == ""
            assert [cast(Rectangle, bar).get_height() for bar in figure.axes[0].patches] == [3, 4]
            buffer.write(b"Actual widget compiler request")

        monkeypatch.setattr(figure, "savefig", savefig)
        mock_st = MagicMock()
        mock_st.pills.return_value = "pgf"
        mock_st.download_button.return_value = False
        monkeypatch.setattr("src.web.pages.ui.plotting.download_section.st", mock_st)
        render_download_section(plot.plot_id, "Measured", plot.render_artifact)
        assert calls == [{"format": "pgf", "backend": "pgf"}]
        assert mock_st.download_button.call_args.kwargs["data"] == b"Actual widget compiler request"
        assert mock_st.download_button.call_args.kwargs["file_name"] == "Measured.pgf"
