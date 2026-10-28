"""One-shot recipe notices preserve the expander's browser identity."""

from streamlit.testing.v1 import AppTest

_SCRIPT = """
from unittest.mock import MagicMock

from src.web.components.analysis_recipe_component import AnalysisRecipeComponent

api = MagicMock()
api.data_services.list_analysis_recipes.return_value = ()
AnalysisRecipeComponent.render(api)
"""


def _recipe_expander_position(app: AppTest) -> int:
    expander = app.expander[0]
    assert expander.label == "Analysis recipes"
    return next(index for index, element in app.main.children.items() if element is expander)


def test_consuming_recipe_feedback_preserves_expander_position_and_pending_input() -> None:
    app = AppTest.from_string(_SCRIPT, default_timeout=15).run()
    assert not app.exception
    position = _recipe_expander_position(app)
    app.text_input(key="analysis_recipe_name").set_value("Pending analysis").run()
    assert not app.exception
    assert not app.success

    app.session_state["analysis_recipe_feedback"] = "Saved analysis recipe Original."
    app.run()

    assert not app.exception
    assert [notice.value for notice in app.success] == ["Saved analysis recipe Original."]
    assert _recipe_expander_position(app) == position
    assert app.text_input(key="analysis_recipe_name").value == "Pending analysis"
    assert "analysis_recipe_feedback" not in app.session_state

    app.run()

    assert not app.exception
    assert not app.success
    assert _recipe_expander_position(app) == position
    assert app.text_input(key="analysis_recipe_name").value == "Pending analysis"
