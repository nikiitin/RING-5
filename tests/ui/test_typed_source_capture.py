"""The real recipe UI captures reviewed import policy and executed shaping once."""

from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest


def _capture_app(source_path: str, shaped: bool) -> None:
    import streamlit as st
    from dataclasses import replace

    import ring5
    from src.web.components.analysis_recipe_component import AnalysisRecipeComponent

    if "typed_capture_session" not in st.session_state:
        session = ring5.Session()
        options = ring5.ImportOptions(
            encoding="utf-8",
            delimiter=";",
            header_row=2,
            trim_whitespace=False,
            null_values=("MISSING",),
            column_types=(
                ring5.ImportColumnCorrection("label", "text"),
                ring5.ImportColumnCorrection("value", "integer"),
            ),
        )
        session.load_import(
            session.preview_import(
                source_path,
                encoding=options.encoding,
                delimiter=options.delimiter,
                header_row=options.header_row,
                trim_whitespace=options.trim_whitespace,
                null_values=options.null_values,
                column_types={
                    correction.column: correction.import_as for correction in options.column_types
                },
            )
        )
        if shaped:
            recipe = session.capture_analysis_recipe("base")
            session.run_analysis_recipe(
                replace(
                    recipe,
                    transformations=(
                        {
                            "type": "deriveColumn",
                            "dest": "value",
                            "op": "scalar",
                            "sources": ["value"],
                            "scalar": 1.0,
                            "scalar_op": "+",
                        },
                    ),
                )
            )
        st.session_state["typed_capture_session"] = session
    workspace = st.session_state["typed_capture_session"]
    AnalysisRecipeComponent.render(workspace.api)


@pytest.mark.parametrize("shaped", [False, True])
def test_reviewed_import_ui_parameterizes_actual_policy_and_replays_exact_frame(
    tmp_path: Path,
    shaped: bool,
) -> None:
    path = tmp_path / "reviewed.csv"
    path.write_text(
        "ignored\nlabel;value\nNA;1\nnan;2\n;3\n001;4\nμ;5\n  whitespace  ;6\n95%;7\nreject;bad\n",
        encoding="utf-8",
    )
    app = AppTest.from_function(_capture_app, args=(str(path), shaped)).run()
    assert not app.exception
    workspace = app.session_state["typed_capture_session"]
    try:
        expected = workspace.api.state_manager.get_data()
        app.text_input(key="analysis_recipe_name").set_value("reviewed_ui").run()
        app.button(key="analysis_recipe_save").click().run()
        assert not app.exception
        assert not app.error
        recipe = workspace.load_analysis_recipe("reviewed_ui")
        assert recipe.source.path == "{{source_path}}"
        assert recipe.parameters[0].default == str(path)
        assert recipe.source.csv_policy.options.trim_whitespace is False
        assert recipe.source.csv_policy.options.null_values == ("MISSING",)
        assert len(recipe.transformations) == int(shaped)
        workspace.api.state_manager.set_parse_variables(
            [{"name": "value", "type": "configuration", "params": {"source_type": "configuration"}}]
        )
        workspace.run_analysis_recipe(recipe)
        pd.testing.assert_frame_equal(workspace.api.state_manager.get_data(), expected)
        assert workspace.api.state_manager.get_data()["label"].tolist() == [
            "NA",
            "nan",
            "",
            "001",
            "μ",
            "  whitespace  ",
            "95%",
        ]
        assert workspace.api.state_manager.get_data()["value"].tolist() == [
            number + int(shaped) for number in range(1, 8)
        ]
    finally:
        workspace.close()
