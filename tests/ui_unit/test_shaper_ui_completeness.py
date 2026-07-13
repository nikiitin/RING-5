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
