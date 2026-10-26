"""Public and recipe admission publish only the current canonical label input."""

from typing import Any

import pandas as pd
import pytest

import ring5
from src.core.models.recipe_models import AnalysisRecipe, RecipeParameter, RecipePlot, RecipeSource
from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService
from src.web.pages.ui.plotting.plot_factory import PlotFactory


@pytest.mark.parametrize("typed", [False, True])
def test_public_plot_rejects_retired_nested_name_before_publication(typed: bool) -> None:
    config: dict[str, Any] = {
        "x": "x",
        "y": "y",
        "series_styles": {"y": {"name": "Shown"}},
    }
    with ring5.Session() as session:
        if typed:
            with pytest.raises(ValueError, match="Use legend_labels"):
                ring5.FigureSpec(extra=config)
        else:
            with pytest.raises(ring5.DataValidationError, match="Use legend_labels"):
                session.create_plot(
                    "bar", data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]})), config=config
                )
        assert not session.plots


def test_invalid_label_update_preserves_existing_configuration_and_plot_identity() -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]})),
            config={"x": "x", "y": "y", "legend_labels": {"y": "Shown"}},
        )
        before = plot.config
        with pytest.raises(ValueError, match="legend_labels must map text"):
            plot.config = {**before, "legend_labels": {"y": 7}}
        assert plot.config == before
        assert session.plots == [plot]


def test_restore_rejects_retired_nested_name_at_the_existing_admission_owner() -> None:
    with ring5.Session() as session:
        plot = session.create_plot(
            "bar",
            data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [3.0]})),
            config={"x": "x", "y": "y"},
        )
        payload = plot.to_dict()
    payload["config"]["series_styles"] = {"raw": {"name": "Shown"}}
    with pytest.raises(ValueError, match="Use legend_labels"):
        PlotFactory.from_dict(payload)


def _recipe(*, numeric: bool = False, retired: bool = False) -> AnalysisRecipe:
    return AnalysisRecipe(
        name="Canonical labels",
        parameters=(
            RecipeParameter(
                "label", "number" if numeric else "string", default=2 if numeric else "Shown"
            ),
        ),
        source=RecipeSource(kind="csv", path="data.csv"),
        plots=(
            RecipePlot(
                name="Bars",
                plot_type="bar",
                config=(
                    {"series_styles": {"raw": {"name": "{{label}}"}}}
                    if retired
                    else {"legend_labels": {"raw": "{{label}}"}}
                ),
            ),
        ),
    )


def test_recipe_labels_materialize_once_and_preserve_the_template() -> None:
    template = _recipe()
    restored = AnalysisRecipeService.loads(AnalysisRecipeService.dumps(template))
    concrete = AnalysisRecipeService.materialize(restored, {"label": "001"})
    assert concrete.plots[0].config["legend_labels"] == {"raw": "001"}
    assert restored.plots[0].config["legend_labels"] == {"raw": "{{label}}"}


def test_recipe_key_and_materialized_value_admission_have_distinct_boundaries() -> None:
    with pytest.raises(ValueError, match="Use legend_labels"):
        AnalysisRecipeService.dumps(_recipe(retired=True))
    template = _recipe(numeric=True)
    AnalysisRecipeService.dumps(template)
    with pytest.raises(ValueError, match="legend_labels must map text"):
        AnalysisRecipeService.materialize(template, {})
