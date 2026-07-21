"""Analysis-recipe Streamlit component tests."""

from __future__ import annotations

from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from src.core.models import AnalysisRecipe, AnalysisRecipeInfo, RecipePlot, RecipeSource


@patch("src.web.components.analysis_recipe_component.st")
def test_capture_parameterizes_source_and_saves_without_overwrite(mock_st: MagicMock) -> None:
    # [test->req~ring5.portfolio.analysis-recipes~1]
    from src.web.components.analysis_recipe_component import AnalysisRecipeComponent

    api = MagicMock()
    base = AnalysisRecipe(
        name="Paper recipe",
        description="Reviewed",
        source=RecipeSource(kind="csv", path="/data/results.csv"),
        plots=(
            RecipePlot(
                name="IPC bars",
                plot_type="bar",
                config={"x": "benchmark", "y": "ipc"},
            ),
        ),
    )
    final = AnalysisRecipe(
        name=base.name,
        description=base.description,
        source=RecipeSource(kind="csv", path="{{source_path}}"),
        parameters=(),
        plots=base.plots,
    )
    api.data_services.capture_analysis_recipe.side_effect = [base, final]
    mock_st.session_state = {}
    mock_st.expander.return_value = nullcontext()
    mock_st.tabs.return_value = [nullcontext(), nullcontext(), nullcontext()]
    mock_st.text_input.side_effect = lambda label, **_kwargs: (
        "Paper recipe" if label == "Recipe name" else ""
    )
    mock_st.text_area.return_value = "Reviewed"
    mock_st.checkbox.side_effect = lambda label, **_kwargs: label.startswith("Make the source")
    mock_st.button.side_effect = lambda label, **_kwargs: label == "Save analysis recipe"
    api.data_services.list_analysis_recipes.return_value = ()

    AnalysisRecipeComponent.render(api)

    second = api.data_services.capture_analysis_recipe.call_args_list[1]
    assert second.kwargs["source"].path == "{{source_path}}"
    assert second.kwargs["parameters"][0].name == "source_path"
    assert second.kwargs["parameters"][0].type == "path"
    assert second.kwargs["parameters"][0].default == "/data/results.csv"
    api.data_services.save_analysis_recipe.assert_called_once_with(final, overwrite=False)
    assert mock_st.session_state["analysis_recipe_feedback"] == (
        "Saved analysis recipe Paper recipe."
    )
    mock_st.rerun.assert_called_once()


@patch("src.web.components.analysis_recipe_component.st")
def test_saved_recipe_shows_counts_and_portable_automation_downloads(mock_st: MagicMock) -> None:
    # [test->req~ring5.automation.script-notebook-export~1]
    from src.web.components.analysis_recipe_component import AnalysisRecipeComponent

    api = MagicMock()
    recipe = AnalysisRecipe(
        name="Saved",
        source=RecipeSource(kind="csv", path="data.csv"),
    )
    api.data_services.list_analysis_recipes.return_value = (
        AnalysisRecipeInfo("Saved", "", "/recipes/saved.json", 1.0, 0, 0, 0, 0),
    )
    api.data_services.load_analysis_recipe.return_value = recipe
    api.data_services.export_analysis_recipe.return_value = b"{}"
    api.data_services.export_analysis_recipe_script.return_value = b"print('recipe')\n"
    api.data_services.export_analysis_recipe_notebook.return_value = b'{"nbformat": 4}\n'
    mock_st.session_state = {}
    mock_st.expander.return_value = nullcontext()
    mock_st.tabs.return_value = [nullcontext(), nullcontext(), nullcontext()]
    mock_st.text_input.return_value = "Unused"
    mock_st.text_area.return_value = ""
    mock_st.checkbox.return_value = False
    mock_st.button.return_value = False
    mock_st.selectbox.return_value = "Saved"

    AnalysisRecipeComponent.render(api)

    api.data_services.load_analysis_recipe.assert_called_once_with("Saved")
    calls = mock_st.download_button.call_args_list
    assert [call.args[0] for call in calls] == [
        "Download recipe JSON",
        "Download Python script",
        "Download Jupyter notebook",
    ]
    assert [call.kwargs["data"] for call in calls] == [
        b"{}",
        b"print('recipe')\n",
        b'{"nbformat": 4}\n',
    ]
    assert [call.kwargs["file_name"] for call in calls] == [
        "Saved.ring5-recipe.json",
        "Saved.py",
        "Saved.ipynb",
    ]
    assert all(call.kwargs["on_click"] == "ignore" for call in calls)
