"""Shaper definitions and exact, data-independent configuration validation."""

from __future__ import annotations

import math
import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from typing import (
    Any,
    Literal,
    NotRequired,
    Required,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

from src.core.common.safe_regex import compile_bounded_regex
from src.core.common.security_limits import (
    MAX_PIPELINE_CONFIG_BYTES,
    MAX_PIPELINE_CONFIG_DEPTH,
    MAX_PIPELINE_CONFIG_STRING_LENGTH,
    MAX_PIPELINE_CONFIG_VALUE_DEPTH,
    MAX_PIPELINE_CONFIG_VALUE_ITEMS,
    MAX_PIPELINE_CONFIG_STEPS,
    MAX_SEARCH_TERM_LENGTH,
    MAX_SELECTOR_STRINGS,
)
from src.core.models.shaper_models import SplitApplyGroupConfig
from src.core.services.shapers.shaper import Shaper

ConfigValidator = Callable[[Mapping[str, Any]], None]


@dataclass(frozen=True)
class ShaperDefinition:
    """One registered strategy and its current configuration contract.

    Args:
        identifier: Exact pipeline identifier.
        implementation: Concrete strategy class, registered under one identifier.
        label: Human-readable display name.
        config_type: TypedDict with an exact required Literal ``type`` discriminator.
        validate: Data-independent semantic validator; raises TypeError or ValueError.
        display_order: Built-in editor position, or None for API-only plugins.
    """

    identifier: str
    implementation: type[Shaper]
    label: str
    config_type: type
    validate: ConfigValidator
    display_order: int | None = None

    def _validate_config(self, config: object, *, require_type: bool = False) -> None:
        """Reject unsupported fields, malformed values and invalid operation semantics."""
        _check_config(config, self.config_type, self.identifier, require_type=require_type)
        validator: Callable[[Mapping[str, Any]], object] = self.validate
        if validator(cast(Mapping[str, Any], config)) is not None:
            raise TypeError("A shaper semantic validator must return None on success.")


def validate_schema(schema: type, identifier: str) -> None:
    """Reject unsupported TypedDict annotations before publishing a definition."""
    visited: set[type] = set()

    def walk(annotation: Any, location: str, depth: int = 0) -> None:
        if depth > MAX_PIPELINE_CONFIG_VALUE_DEPTH:
            raise TypeError(f"{location}: schema nesting is too deep.")
        origin, args = get_origin(annotation), get_args(annotation)
        if annotation in (str, int, float, bool, type(None)):
            return
        if is_typeddict(annotation):
            if annotation in visited:
                return
            visited.add(annotation)
            try:
                fields = _fields(annotation)
            except (NameError, TypeError) as exc:
                raise TypeError(f"{location}: schema annotations must resolve.") from exc
            for name, field_type in fields.items():
                if name == "pipeline" and annotation is SplitApplyGroupConfig:
                    continue
                if get_origin(field_type) in (Required, NotRequired):
                    field_type = get_args(field_type)[0]
                walk(field_type, f"{location}.{name}", depth + 1)
            return
        if origin in (Union, types.UnionType):
            for option in args:
                walk(option, location, depth + 1)
            return
        if origin is Literal:
            if args and all(
                type(value) in (str, int, float, bool, type(None))
                and (type(value) is not float or math.isfinite(value))
                for value in args
            ):
                return
        elif origin is list and len(args) == 1:
            walk(args[0], f"{location}[]", depth + 1)
            return
        elif origin is dict and len(args) == 2 and args[0] is str:
            walk(args[1], f"{location}[]", depth + 1)
            return
        raise TypeError(f"{location}: unsupported schema annotation {annotation!r}.")

    walk(schema, identifier)


@dataclass
class ConfigValueBudget:
    """Aggregate admission budget shared by every top-level operation's value graph."""

    remaining_items: int = field(default_factory=lambda: MAX_PIPELINE_CONFIG_VALUE_ITEMS)
    remaining_bytes: int = field(default_factory=lambda: MAX_PIPELINE_CONFIG_BYTES)
    max_depth: int = MAX_PIPELINE_CONFIG_VALUE_DEPTH


def validate_config_values(
    value: object,
    *,
    budget: ConfigValueBudget | None = None,
    recipe_containers: bool = False,
) -> None:
    """Bound a JSON value graph before schema traversal or ownership copying.

    Operation inputs may use a mapping interface. Nested values use JSON scalars, lists
    and dictionaries. Shared values count each time they would appear
    on the wire; cycles and unsupported objects fail before copying. Recipe DTOs
    may opt into tuple sequences and nested mapping interfaces before serialization.
    """
    shared = budget if budget is not None else ConfigValueBudget()
    active: set[int] = set()

    def charge(size: int, location: str) -> None:
        shared.remaining_items -= 1
        shared.remaining_bytes -= size
        if shared.remaining_items < 0 or shared.remaining_bytes < 0:
            raise ValueError(f"{location}: configuration value budget exceeded.")

    def walk(item: object, location: str, depth: int, *, interface: bool = False) -> None:
        if depth > shared.max_depth:
            raise ValueError(f"{location}: configuration nesting is too deep.")
        if type(item) is str:
            if len(item) > MAX_PIPELINE_CONFIG_STRING_LENGTH:
                raise ValueError(
                    f"{location}: text exceeds {MAX_PIPELINE_CONFIG_STRING_LENGTH} characters."
                )
            charge(len(item.encode("utf-8")) + 2, location)
            return
        if item is None or type(item) is bool:
            charge(5, location)
            return
        if type(item) is int:
            digits_bound = (item.bit_length() * 30103) // 100000 + 2
            if digits_bound > shared.remaining_bytes:
                raise ValueError(f"{location}: configuration value budget exceeded.")
            try:
                size = len(str(item))
            except ValueError as exc:
                raise ValueError(f"{location}: integer is too large to serialize.") from exc
            charge(size, location)
            return
        if type(item) is float:
            if not math.isfinite(item):
                raise ValueError(f"{location}: numbers must be finite.")
            charge(24, location)
            return
        is_mapping = type(item) is dict or (
            (interface or recipe_containers) and isinstance(item, Mapping)
        )
        is_sequence = type(item) is list or (recipe_containers and type(item) is tuple)
        if not is_mapping and not is_sequence:
            raise TypeError(f"{location}: values must be JSON scalars, lists or objects.")
        container = cast(Any, item)
        if len(container) > shared.remaining_items:
            raise ValueError(f"{location}: configuration value budget exceeded.")
        identity = id(item)
        if identity in active:
            raise ValueError(f"{location}: cyclic configuration values are unsupported.")
        charge(2 + len(container), location)
        active.add(identity)
        try:
            if is_mapping:
                for key, child in container.items():
                    if type(key) is not str:
                        raise TypeError(f"{location}: object keys must be strings.")
                    walk(key, location, depth + 1)
                    walk(child, f"{location}.{key}", depth + 1)
            else:
                for index, child in enumerate(container):
                    walk(child, f"{location}[{index}]", depth + 1, interface=False)
        finally:
            active.remove(identity)

    walk(value, "configuration", 0, interface=True)


@lru_cache(maxsize=128)
def _fields(schema: type) -> dict[str, Any]:
    return get_type_hints(schema, include_extras=True)


def _check_config(value: object, schema: type, location: str, *, require_type: bool = True) -> None:
    if not isinstance(value, Mapping):
        raise TypeError(f"{location} must be a configuration object.")
    if any(type(key) is not str for key in value):
        raise TypeError(f"{location} configuration keys must be strings.")
    fields = _fields(schema)
    missing = [
        name
        for name, annotation in fields.items()
        if name not in value
        and (name != "type" or require_type)
        and (
            get_origin(annotation) is Required
            or (
                get_origin(annotation) is not NotRequired
                and name in cast(Any, schema).__required_keys__
            )
        )
    ]
    if missing:
        raise ValueError(f"{location}: Missing required parameters: {', '.join(missing)}.")
    unknown = set(value) - fields.keys()
    if unknown:
        raise ValueError(
            f"{location}: unsupported fields: {', '.join(map(str, sorted(unknown, key=str)))}."
        )
    for name, annotation in fields.items():
        if name not in value:
            continue
        if get_origin(annotation) in (Required, NotRequired):
            annotation = get_args(annotation)[0]
        # Nested pipelines are checked once with the shared step/depth budget.
        if name == "pipeline" and schema is SplitApplyGroupConfig:
            if not isinstance(value[name], list):
                raise TypeError(f"{location}.pipeline must be a list.")
            continue
        _check_value(value[name], annotation, f"{location}.{name}")


def _check_value(value: object, annotation: Any, location: str) -> None:
    origin, args = get_origin(annotation), get_args(annotation)
    if origin in (Union, types.UnionType):
        for option in args:
            try:
                _check_value(value, option, location)
                return
            except (TypeError, ValueError):
                continue
        raise TypeError(f"{location} has an unsupported value type.")
    if origin is Literal:
        if any(type(value) is type(option) and value == option for option in args):
            return
        raise ValueError(f"{location} must be one of {args!r}.")
    if is_typeddict(annotation):
        _check_config(value, annotation, location)
    elif origin is list:
        if not isinstance(value, list):
            raise TypeError(f"{location} must be a list.")
        for index, item in enumerate(value):
            _check_value(item, args[0], f"{location}[{index}]")
    elif origin is dict:
        if not isinstance(value, dict):
            raise TypeError(f"{location} must be a dictionary.")
        for key, item in value.items():
            _check_value(key, args[0], f"{location} key")
            _check_value(item, args[1], f"{location}[{key!r}]")
    elif annotation is float:
        if type(value) not in (int, float):
            raise TypeError(f"{location} must be a finite number.")
        try:
            finite = math.isfinite(cast(int | float, value))
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f"{location} must be a finite number.")
    elif annotation is Any:
        raise TypeError(f"{location}: shaper schemas must use explicit value types.")
    elif type(value) is not annotation:
        label = {str: "a string", bool: "a boolean", int: "an integer", type(None): "null"}.get(
            annotation, annotation.__name__
        )
        raise TypeError(f"{location} must be {label}.")


def _columns(
    config: Mapping[str, Any], *names: str, nonempty: bool = True, unique: bool = True
) -> None:
    for name in names:
        values = config[name]
        if nonempty and not values:
            raise ValueError(f"'{name}' must be a non-empty list.")
        if any(not value for value in values):
            raise ValueError(f"'{name}' must contain non-empty column names.")
        if unique and len(set(values)) != len(values):
            raise ValueError(f"'{name}' cannot contain duplicate columns.")


def _names(config: Mapping[str, Any], *names: str) -> None:
    for name in names:
        if not config[name]:
            raise ValueError(f"'{name}' must be a non-empty string.")


def validate_mean(config: Mapping[str, Any]) -> None:
    """Validate selected metrics, explicit grouping and the summary label column."""
    _columns(config, "meanVars")
    _columns(config, "groupingColumns", nonempty=False)
    _names(config, "replacingColumn")


def validate_normalize(config: Mapping[str, Any]) -> None:
    """Validate metric and grouping selections without inspecting baseline data."""
    _columns(config, "normalizeVars", "groupBy")
    _names(config, "normalizerColumn")
    if "normalizerVars" in config:
        _columns(config, "normalizerVars")


def validate_sort(config: Mapping[str, Any]) -> None:
    """Validate explicit category orders; an empty mapping is a valid identity sort."""
    for column, values in config["order_dict"].items():
        if not column:
            raise ValueError("Sort column names must be non-empty strings.")
        if len(set(values)) != len(values):
            raise ValueError(f"Sort order for '{column}' cannot contain duplicate values.")


def validate_column_selector(config: Mapping[str, Any]) -> None:
    """Validate column names; an empty projection is supported."""
    _columns(config, "columns", nonempty=False)


PREDICATE_OPERANDS = {
    "greater_than": "threshold",
    "less_than": "threshold",
    "greater_or_equal": "threshold",
    "less_or_equal": "threshold",
    "equals": "value",
    "not_equals": "value",
    "contains": "value",
    "range": "range",
    "in": "values",
}


def validate_condition(config: Mapping[str, Any]) -> None:
    """Validate the single operand selected by the explicit predicate mode."""
    _names(config, "column")
    field = PREDICATE_OPERANDS[config["mode"]]
    if set(config) & set(PREDICATE_OPERANDS.values()) != {field}:
        raise ValueError(f"'{config['mode']}' requires only the '{field}' operand.")
    if field == "range" and (len(config[field]) != 2 or config[field][0] > config[field][1]):
        raise ValueError("'range' must contain two ordered finite bounds.")
    if config["mode"] == "contains":
        value = config[field]
        if not isinstance(value, str):
            raise TypeError("'contains' requires a text 'value'.")
        if len(value) > MAX_SEARCH_TERM_LENGTH:
            raise ValueError(f"Contains values cannot exceed {MAX_SEARCH_TERM_LENGTH} characters.")


def validate_item_selector(config: Mapping[str, Any]) -> None:
    """Validate bounded literal text selection."""
    _names(config, "column")
    if len(config["strings"]) > MAX_SELECTOR_STRINGS:
        raise ValueError(f"ItemSelector accepts at most {MAX_SELECTOR_STRINGS} search strings.")
    if any(len(value) > MAX_SEARCH_TERM_LENGTH for value in config["strings"]):
        raise ValueError(f"Search strings cannot exceed {MAX_SEARCH_TERM_LENGTH} characters.")


def validate_transformer(config: Mapping[str, Any]) -> None:
    """Validate the target column and any explicit category order."""
    _names(config, "column")
    order = config.get("order")
    if order is not None and len(set(order)) != len(order):
        raise ValueError("Transformer 'order' cannot contain duplicate values.")


def validate_pivot_longer(config: Mapping[str, Any]) -> None:
    """Validate melt columns and bounded capture-group extraction options."""
    _columns(config, "id_vars", "value_vars")
    _names(config, "var_name", "value_name")
    if set(config["id_vars"]) & set(config["value_vars"]):
        raise ValueError("Pivot id_vars and value_vars cannot overlap.")
    pattern = config.get("extract_pattern")
    if pattern:
        compiled = compile_bounded_regex(pattern)
        indices = config.get("extract_group_indices", [1])
        if not indices or any(index < 0 or index > compiled.groups for index in indices):
            raise ValueError("Extraction group indices must refer to existing capture groups.")
        for key in config.get("selection_filters", {}):
            if (
                not key
                or not key.isascii()
                or not key.isdecimal()
                or (len(key) > 1 and key[0] == "0")
            ):
                raise ValueError(
                    "Selection filter keys must be canonical decimal capture-group numbers."
                )
            if len(key) > len(str(compiled.groups)) or int(key) > compiled.groups:
                raise ValueError("Selection filter keys must refer to existing capture groups.")
    elif any(config.get(name) for name in ("extract_group_indices", "selection_filters")):
        raise ValueError("Extraction groups and filters require an extract_pattern.")


def validate_pivot_wider(config: Mapping[str, Any]) -> None:
    """Validate pivot columns before the data-dependent uniqueness check."""
    _columns(config, "index")
    _names(config, "columns", "values")
    if config["columns"] in config["index"] or config["values"] in config["index"]:
        raise ValueError("Pivot columns and values cannot also be index columns.")


def validate_derive_column(config: Mapping[str, Any]) -> None:
    """Validate operands for arithmetic, concatenation and value mapping."""
    _names(config, "dest")
    _columns(config, "sources", unique=False)
    operation, sources = config["op"], config["sources"]
    if operation == "ratio" and len(sources) != 2:
        raise ValueError("DeriveColumn op 'ratio' requires exactly two 'sources' [num, den].")
    if operation in ("scalar", "map") and len(sources) != 1:
        raise ValueError(f"DeriveColumn op '{operation}' requires exactly one 'sources' column.")
    if operation == "scalar" and "scalar" not in config:
        raise ValueError("DeriveColumn op 'scalar' requires a 'scalar' value.")
    if operation == "map" and not config.get("mapping"):
        raise ValueError("DeriveColumn op 'map' requires a non-empty 'mapping'.")


def validate_group_cardinality(config: Mapping[str, Any]) -> None:
    """Validate cardinality grouping and a nonnegative exact integer count."""
    _columns(config, "groupBy")
    _names(config, "countColumn")
    if config["count"] < 0:
        raise ValueError("Group cardinality 'count' cannot be negative.")


def validate_group_predicate(config: Mapping[str, Any]) -> None:
    """Validate the baseline and predicate column selection."""
    _columns(config, "groupBy")
    _names(config, "baselineColumn", "predicateColumn")
    if config["baselineValue"] == "":
        raise ValueError("'baselineValue' must not be an empty string.")


def validate_split_apply(config: Mapping[str, Any]) -> None:
    """Validate disjoint column groups; nested steps share the registry budget."""
    _columns(config, "joinColumns")
    groups = config["groups"]
    if not 2 <= len(groups) <= 4:
        raise ValueError("SplitApply 'groups' must contain at least 2 groups and at most 4 groups.")
    seen = set(config["joinColumns"])
    for index, group in enumerate(groups):
        _columns(group, "columns")
        if seen & set(group["columns"]):
            raise ValueError(
                f"SplitApply group {index}: column appears in multiple groups or joinColumns."
            )
        seen.update(group["columns"])


@dataclass
class ValidationBudget:
    """One admission budget shared by all steps of a possibly nested pipeline."""

    steps: int = 0

    def charge(self, depth: int) -> None:
        """Reject a step that exceeds the shared count or nesting limit."""
        self.steps += 1
        if self.steps > MAX_PIPELINE_CONFIG_STEPS:
            raise ValueError(
                f"Pipeline configuration exceeds the {MAX_PIPELINE_CONFIG_STEPS}-step limit."
            )
        if depth > MAX_PIPELINE_CONFIG_DEPTH:
            raise ValueError("Pipeline configuration nesting is too deep.")


class ShaperValidationError(ValueError):
    """Invalid pipeline configuration with its top-level step location."""

    def __init__(self, message: str, *, step_index: int, shaper_type: str | None) -> None:
        self.step_index = step_index
        self.shaper_type = shaper_type
        super().__init__(message)
