"""Defensive parser-variable identity normalization."""

from copy import deepcopy
import uuid

from src.core.models.data_models import ParseVariableConfig


def normalize_variable_ids(variables: list[ParseVariableConfig]) -> list[ParseVariableConfig]:
    """Copy variable configurations and assign nonempty, session-unique IDs."""
    copied = deepcopy(variables)
    seen: set[str] = set()
    for variable in copied:
        if not isinstance(variable, dict):
            raise TypeError("Parse variable entries must be dictionaries.")
        identifier = variable.get("_id")
        if not isinstance(identifier, str) or not identifier.strip() or identifier in seen:
            identifier = str(uuid.uuid4())
            variable["_id"] = identifier
        seen.add(identifier)
    return copied
