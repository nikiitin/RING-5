"""Factory ↔ UI contract for shapers.

Every shaper that is registered and reachable in the "Add transformation"
dropdown must have a UI config renderer — otherwise a user can select a
transform that silently does nothing.
"""

import pandas as pd

from src.core.services.shapers.factory import ShaperFactory


def test_every_dropdown_shaper_has_a_ui_renderer() -> None:
    from src.web.pages.ui.shaper_config import CONFIG_DISPATCH

    # get_display_name_map() values are the shaper types shown in the dropdown.
    selectable = set(ShaperFactory.get_display_name_map().values())
    missing = selectable - set(CONFIG_DISPATCH)
    assert not missing, f"Registered, selectable shapers with no UI config renderer: {missing}"
    # And no renderer for a type that isn't selectable (dead dispatch entry).
    assert not (set(CONFIG_DISPATCH) - selectable)


def test_item_selector_config_executes() -> None:
    # The config shape the itemSelector UI produces must drive the shaper.
    df = pd.DataFrame({"bench": ["a", "b", "c"], "v": [1, 2, 3]})
    cfg = {"type": "itemSelector", "column": "bench", "strings": ["a", "c"], "mode": "exact"}
    shaper = ShaperFactory.create_shaper("itemSelector", cfg)  # type: ignore[arg-type]
    out = shaper(df)
    assert sorted(out["bench"].tolist()) == ["a", "c"]


def test_plugin_configuration_survives_an_editor_without_a_renderer(monkeypatch) -> None:
    from unittest.mock import MagicMock
    from src.web.pages.ui.shaper_config import configure_shaper
    from src.web.components.shapers.split_apply_config import SplitApplyConfig, _init_dispatch

    monkeypatch.setattr("src.web.pages.ui.shaper_config.st", MagicMock())
    monkeypatch.setattr("src.web.components.shapers.split_apply_config.st", MagicMock())
    config = {"type": "externalPlugin", "custom": {"value": 3}}
    result = configure_shaper(
        "externalPlugin", pd.DataFrame({"v": [1]}), 1, config, display_names={}, owner_id=0
    )
    assert result == config
    assert result is not config
    _init_dispatch()
    nested = SplitApplyConfig._render_sub_step(
        pd.DataFrame({"v": [1]}),
        config,
        "plugin",
        0,
        ShaperFactory.get_display_name_map(),
    )
    assert nested == config


def test_metadata_discovery_and_default_editor_order_are_distinct() -> None:
    from src.core.services.shapers.shapers_impl import DefaultShapersAPI

    facade = DefaultShapersAPI()
    assert facade.get_available_shaper_types()[0] == "mean"
    names = facade.get_shaper_display_names()
    assert list(names.items())[:4] == [
        ("Column Selector", "columnSelector"),
        ("Sort", "sort"),
        ("Mean Calculator", "mean"),
        ("Normalize", "normalize"),
    ]
