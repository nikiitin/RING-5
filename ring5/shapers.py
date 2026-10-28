"""Public extension contract for registered pipeline shapers.

Implement a Shaper with an exact ShaperDefinition and register it before running
its configuration through Session.shape or Session.shape_submit. Built-in
operations are selected by their registered configuration identifiers.
"""

from __future__ import annotations

from ring5.errors import PipelineError
from src.core.services.shapers.definition import ShaperDefinition
from src.core.services.shapers.shaper import Shaper


def available_shaper_types() -> tuple[str, ...]:
    # [impl->req~ring5.api.registry-discovery~1]
    """Return every registered pipeline shaper identifier."""
    from src.core.services.shapers.factory import ShaperFactory

    return tuple(ShaperFactory.get_available_types())


def register_shaper(definition: ShaperDefinition) -> None:
    """Register one current plugin definition for pipeline construction.

    Args:
        definition: Strategy, exact TypedDict configuration, label and validator.

    Raises:
        PipelineError: Definition is malformed or duplicates an existing registration.
    """
    from src.core.services.shapers.factory import ShaperFactory

    try:
        ShaperFactory.register(definition)
    except (TypeError, ValueError) as exc:
        raise PipelineError(str(exc)) from exc


__all__ = ["Shaper", "ShaperDefinition", "register_shaper", "available_shaper_types"]
