"""Own native figure snapshots without registering copied pyplot managers."""

from copy import deepcopy
from typing import Any, cast

from matplotlib.axis import Axis
from matplotlib.category import UnitData
from matplotlib.figure import Figure


def copy_matplotlib_figure(figure: Figure) -> Figure:
    """Copy artists and their figure references while leaving pyplot ownership untouched.

    Matplotlib's figure serialization normally restores a registered figure into
    pyplot. Export snapshots use that same serialization state with manager
    restoration disabled, so copying never opens a window or claims a manager.
    """
    state = figure.__getstate__()
    if not isinstance(state, dict):
        raise ValueError("Native figure serialization requires a state mapping.")
    state = state.copy()
    state.pop("_restore_to_pylab", None)
    owned = object.__new__(type(figure))
    memo: dict[int, Any] = {id(figure): owned}
    for axis in cast(list[Axis], figure.findobj(Axis)):
        units = axis.get_units()
        if type(units) is UnitData and id(units) not in memo:
            # UnitData owns an unpickleable itertools counter. Its ordered
            # categories define native positions, including shared/inset axes.
            memo[id(units)] = UnitData(list(units._mapping))
    # Matplotlib defines __setstate__ at runtime; its stubs omit this method.
    cast(Any, owned).__setstate__(deepcopy(state, memo))
    return owned
