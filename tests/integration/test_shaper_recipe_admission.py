"""Recipe publication bounds value graphs before walking or copying them."""

from collections.abc import Sequence
from unittest.mock import patch

import pytest

import ring5

pytestmark = [pytest.mark.public_api, pytest.mark.timeout(2)]


def _shared_graph() -> list:
    value = ["{{column}}"]
    for _ in range(30):
        value = [value, value]
    return value


def test_capture_rejects_shared_pipeline_before_placeholder_walk_or_copy() -> None:
    with ring5.Session() as session:
        with (
            patch(
                "src.core.services.data_services.analysis_recipe_service."
                "AnalysisRecipeService._placeholder_names",
                side_effect=AssertionError("placeholder traversal reached"),
            ),
            patch(
                "src.core.services.data_services.analysis_recipe_service.copy.deepcopy",
                side_effect=AssertionError("ownership copy reached"),
            ),
            pytest.raises(ring5.RecipeError, match="value budget"),
        ):
            session.capture_analysis_recipe(
                "Bounded capture",
                source=ring5.RecipeSource(kind="csv", path="data.csv"),
                transformations=[{"type": "columnSelector", "columns": _shared_graph()}],
            )


@pytest.mark.parametrize("location", ["plot", "source"])
def test_recipe_metadata_rejects_shared_graph_before_codec_walk_or_copy(location) -> None:
    source = ring5.RecipeSource(kind="csv", path="data.csv")
    plots = ()
    if location == "plot":
        plots = (ring5.RecipePlot("Plot", "bar", {"title": _shared_graph()}),)
    else:
        source = ring5.RecipeSource(
            kind="parser", path="stats", variables=({"metadata": _shared_graph()},)
        )
    recipe = ring5.AnalysisRecipe("Bounded metadata", source, plots=plots)
    with ring5.Session() as session:
        with (
            patch(
                "src.core.services.data_services.analysis_recipe_service."
                "AnalysisRecipeService._placeholder_names",
                side_effect=AssertionError("placeholder traversal reached"),
            ),
            patch(
                "src.core.services.data_services.analysis_recipe_service.copy.deepcopy",
                side_effect=AssertionError("ownership copy reached"),
            ),
            pytest.raises(ring5.RecipeError, match="value budget"),
        ):
            session.export_analysis_recipe(recipe)


def test_capture_rejects_oversized_sequence_before_materializing_steps() -> None:
    class HugeSequence(Sequence):
        def __len__(self):
            return 10**12

        def __getitem__(self, index):
            raise AssertionError("step read before outer count admission")

    with ring5.Session() as session:
        with pytest.raises(ring5.RecipeError, match="transformation limit"):
            session.capture_analysis_recipe(
                "Bounded sequence",
                source=ring5.RecipeSource(kind="csv", path="data.csv"),
                transformations=HugeSequence(),
            )


def test_recipe_rejects_unsupported_metadata_before_deepcopy() -> None:
    class UnsupportedValue:
        def __deepcopy__(self, memo):
            raise AssertionError("unsupported value copied before admission")

    recipe = ring5.AnalysisRecipe(
        "Unsupported metadata",
        ring5.RecipeSource(kind="csv", path="data.csv"),
        plots=(ring5.RecipePlot("Plot", "bar", {"title": UnsupportedValue()}),),
    )
    with ring5.Session() as session:
        with pytest.raises(ring5.RecipeError, match="JSON scalars"):
            session.export_analysis_recipe(recipe)
