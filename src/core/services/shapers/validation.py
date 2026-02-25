"""
Shaper Validation — Core-layer validation for shaper configurations.

Provides pre-flight validation for shaper configs before construction.
This replaces the web-layer ``SHAPER_REQUIRED_PARAMS`` / ``validate_shaper_config``
which incorrectly lived in ``src/web/pages/ui/shaper_config.py``.

All validation logic belongs here in the core layer. The web layer should
only catch exceptions and display user-friendly error messages.
"""

from __future__ import annotations

from src.core.models.shaper_models import ShaperStepConfig

# Required parameter names per shaper type.
# A field is "required" if the shaper cannot execute without it.
# Note: ConditionSelector and Transformer only universally require ``column``;
# additional requirements depend on the selected ``mode``.
_REQUIRED_PARAMS: dict[str, list[str]] = {
    "mean": ["groupingColumns", "meanVars"],
    "normalize": ["normalizeVars", "normalizerColumn", "normalizerValue", "groupBy"],
    "sort": ["order_dict"],
    "splitApply": ["joinColumns", "groups"],
    "columnSelector": ["columns"],
    "conditionSelector": ["column"],
    "transformer": ["column"],
    "itemSelector": ["column", "strings"],
}


def validate_shaper_config(
    shaper_type: str, config: ShaperStepConfig
) -> tuple[bool, list[str] | None]:
    """Validate whether a shaper config has all required parameters filled.

    Args:
        shaper_type: Shaper type identifier (factory registry key).
        config: Shaper configuration dict (any variant of ``ShaperStepConfig``).

    Returns:
        Tuple of ``(is_valid, missing_fields)``.
        - ``is_valid``: ``True`` if all required params present and non-empty.
        - ``missing_fields``: List of missing/empty field names, or ``None``
          if valid.
    """
    required_params = _REQUIRED_PARAMS.get(shaper_type, [])
    missing_fields: list[str] = []

    for param in required_params:
        value = config.get(param)  # type: ignore[arg-type]
        if value is None or (isinstance(value, str) and not value):
            missing_fields.append(param)
        elif isinstance(value, list) and not value:
            missing_fields.append(param)

    if missing_fields:
        return False, missing_fields

    return True, None


def get_required_params(shaper_type: str) -> list[str]:
    """Return list of required parameter names for a shaper type.

    Args:
        shaper_type: Shaper type identifier.

    Returns:
        List of required field names, empty if type is unknown.
    """
    return list(_REQUIRED_PARAMS.get(shaper_type, []))
