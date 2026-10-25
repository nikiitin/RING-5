"""Current plot configuration uses one key policy before state publication."""

import json
from dataclasses import replace
from unittest.mock import patch
from typing import Any, cast

import pandas as pd
import pytest

import ring5
from src.core.models.recipe_models import (
    ANALYSIS_RECIPE_SCHEMA_VERSION,
    AnalysisRecipe,
    RecipeParameter,
    RecipePlot,
    RecipeSource,
)
from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService
from src.web.pages.ui.plotting.plot_factory import PlotFactory
from src.web.rendering.config_builder import ConfigSpecBuilder

_RETIRED = (
    "dual_legend_font_size",
    "legend_xanchor",
    "legend_yanchor",
    "legend2_xanchor",
    "legend2_yanchor",
    "legend3_xanchor",
    "legend3_yanchor",
)


@pytest.mark.public_api
@pytest.mark.parametrize("key", _RETIRED)
@pytest.mark.parametrize("typed", [False, True])
def test_public_plot_rejects_retired_legend_keys_before_retaining_state(
    key: str, typed: bool
) -> None:
    # [test->req~ring5.portfolio.schema~1]
    with ring5.Session() as session:
        if typed:
            with pytest.raises(ValueError, match="Unsupported legend configuration keys"):
                ring5.FigureSpec(x="x", y_columns=["y"], extra={key: "left"})
        else:
            with pytest.raises(
                ring5.DataValidationError, match="Unsupported legend configuration keys"
            ):
                session.create_plot(
                    "bar",
                    data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [2.0]})),
                    config={"x": "x", "y": "y", key: "left"},
                )
        assert not session.plots


@pytest.mark.parametrize("key", _RETIRED)
def test_restore_and_render_reject_the_same_retired_keys_before_native_or_model_creation(
    key: str,
) -> None:
    config = {key: "left"}
    with patch.object(PlotFactory, "create_plot", side_effect=AssertionError("plot publication")):
        with pytest.raises(ValueError, match="Unsupported legend configuration keys"):
            PlotFactory.from_dict({"id": 0, "name": "Bad", "plot_type": "bar", "config": config})
    with pytest.raises(ValueError, match="Unsupported legend configuration keys"):
        ConfigSpecBuilder.from_config(config, "bar")


def _recipe(config: dict[str, Any]) -> AnalysisRecipe:
    return AnalysisRecipe(
        name="Current config",
        source=RecipeSource(kind="csv", path="data.csv"),
        plots=(RecipePlot(name="Bars", plot_type="bar", config=config),),
    )


@pytest.mark.parametrize("key", _RETIRED)
def test_recipe_rejects_retired_config_before_opening_storage(key: str) -> None:
    with patch(
        "src.core.services.data_services.analysis_recipe_service."
        "PathService.get_analysis_recipes_dir",
        side_effect=AssertionError("storage reached"),
    ):
        with pytest.raises(ValueError, match="Unsupported legend configuration keys"):
            AnalysisRecipeService.save(_recipe({key: "left"}))


def test_canonical_recipe_keys_retain_unmaterialized_values_and_one_current_version() -> None:
    recipe = replace(
        _recipe(
            {"x": "{{column}}", "legend2_anchor_x": "{{anchor}}", "legend2_font_size": "{{size}}"}
        ),
        parameters=(
            RecipeParameter("column", "string", default="x"),
            RecipeParameter("anchor", "string", default="left"),
            RecipeParameter("size", "number", default=12.5),
        ),
    )
    payload = AnalysisRecipeService.dumps(recipe)
    assert recipe.schema_version == ANALYSIS_RECIPE_SCHEMA_VERSION == 4
    assert AnalysisRecipeService.loads(payload) == recipe
    obsolete = json.loads(payload)
    obsolete["schema_version"] = ANALYSIS_RECIPE_SCHEMA_VERSION - 1
    with pytest.raises(ValueError, match="schema version"):
        AnalysisRecipeService.loads(json.dumps(obsolete))


@pytest.mark.public_api
def test_nontext_config_keys_fail_before_publication() -> None:
    with ring5.Session() as session:
        with pytest.raises(ring5.DataValidationError, match="keys must be text"):
            session.create_plot(
                "bar",
                data=ring5.Table(pd.DataFrame({"x": ["a"], "y": [2.0]})),
                config=cast(Any, {"x": "x", "y": "y", 1: "invalid"}),
            )
        assert not session.plots
