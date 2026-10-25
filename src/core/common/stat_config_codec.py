"""The current runnable statistic configuration contract and UI draft projection."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import fields
import math
import re
from typing import Any, cast

from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.core.models.parsing_models import ScannedVariable, StatConfig, StatParamValue
from src.core.models.pattern_index_service import PatternIndexService

_COMMON_PARAMS = frozenset({"selected_sources", "source_type"})
_TYPE_PARAMS = {
    "scalar": frozenset(),
    "vector": frozenset({"entries", "statistics"}),
    "distribution": frozenset({"minimum", "maximum", "statistics"}),
    "histogram": frozenset({"entries", "statistics", "bins", "max_range"}),
    "configuration": frozenset({"on_empty"}),
}
_FIELDS = frozenset(field.name for field in fields(StatConfig))
_DRAFT_FIELDS = _FIELDS | {"_id"}
_PARAM_NAME = re.compile(r"[a-z][a-z0-9_]*\Z")


class StatConfigDraftIncomplete(ValueError):
    """A current editor draft is not complete enough to execute."""


class StatConfigCodec:
    """Validate one typed runnable configuration and its exact serialized shape."""

    @staticmethod
    def _text(value: object, field: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"Statistic {field} must be non-empty text.")
        return value

    @classmethod
    def _params(cls, kind: str, params: dict[str, Any]) -> dict[str, Any]:
        """Validate current option spelling and JSON field types independently of drafts."""
        allowed = _COMMON_PARAMS | _TYPE_PARAMS.get(kind, frozenset(params))
        unknown_params = set(params) - allowed
        if unknown_params:
            raise ValueError(f"Unsupported {kind} statistic options: {sorted(unknown_params)}.")
        for key, item in params.items():
            if not isinstance(key, str) or not _PARAM_NAME.fullmatch(key):
                raise ValueError("Statistic option names must be snake_case identifiers.")
            if item is not None and type(item) not in (str, int, float, bool, list):
                raise TypeError(f"Statistic option {key} has an unsupported value type.")
            if isinstance(item, list) and any(not isinstance(entry, str) for entry in item):
                raise TypeError(f"Statistic option {key} must contain text entries.")
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError(f"Statistic option {key} must be finite.")
        for key in ("entries", "statistics", "selected_sources"):
            if key in params and not isinstance(params[key], list):
                raise TypeError(f"Statistic {key} must be a list of text entries.")
        if "source_type" in params:
            source_type = params["source_type"]
            if not isinstance(source_type, str):
                raise TypeError("Statistic source_type must be text.")
            if source_type and not _PARAM_NAME.fullmatch(source_type):
                raise ValueError("Statistic source_type must be an exact backend identifier.")
        return params

    @classmethod
    def from_payload(cls, value: object) -> StatConfig:
        """Decode the complete current wire shape, rejecting retired fields.

        Args:
            value: Current JSON object emitted by :meth:`to_payload`.

        Returns:
            Independent validated runnable configuration.

        Raises:
            TypeError: The payload or a field has the wrong type.
            ValueError: Fields, values, or per-type options are invalid.
        """
        if not isinstance(value, Mapping):
            raise TypeError("A statistic configuration payload must be an object.")
        if set(value) != _FIELDS:
            missing = sorted(_FIELDS - set(value))
            unknown = sorted(set(value) - _FIELDS)
            raise ValueError(
                f"Invalid statistic configuration fields; missing={missing}, unsupported={unknown}."
            )
        name = cls._text(value["name"], "name")
        kind = cls._text(value["type"], "type")
        if not _PARAM_NAME.fullmatch(kind):
            raise ValueError("Statistic type must be an exact snake_case backend identifier.")
        source = value["source_name"]
        if source is not None:
            source = cls._text(source, "source_name")
        repeat = value["repeat"]
        if type(repeat) is not int or repeat < 1:
            raise ValueError("Statistic repeat must be a positive integer.")
        for flag in ("statistics_only", "is_regex", "keep_indices"):
            if type(value[flag]) is not bool:
                raise TypeError(f"Statistic {flag} must be a boolean.")
        raw_params = value["params"]
        if not isinstance(raw_params, dict):
            raise TypeError("Statistic params must be an object.")
        params = deepcopy(raw_params)
        params = cls._params(kind, params)
        source_type = cls._text(params.get("source_type"), "source_type")
        is_regex = value["is_regex"] or PatternIndexService.is_pattern_variable(source or name)
        if value["keep_indices"] and not PatternIndexService.is_pattern_variable(source or name):
            raise ValueError("Keeping source indices requires a numeric source pattern.")
        scalar_pattern_vector = kind == "vector" and source_type == "scalar"
        if scalar_pattern_vector:
            if not PatternIndexService.is_pattern_variable(source or name):
                raise ValueError("Scalar vector output requires a numeric source pattern.")
            if "entries" in params or params.get("statistics") or value["statistics_only"]:
                raise ValueError(
                    "Scalar pattern vector entries derive only from selected source instances."
                )
        if (
            kind == "vector"
            and source_type == "histogram"
            and any(re.fullmatch(r"-?\d+", entry) for entry in params.get("entries", []))
        ):
            raise ValueError("Histogram vector entries require inclusive range labels such as 0-0.")
        selected_sources = params.get("selected_sources")
        if selected_sources is not None:
            if not selected_sources or any(not entry for entry in selected_sources):
                raise ValueError("Selected sources must contain concrete non-empty names.")
            if len(set(selected_sources)) != len(selected_sources):
                raise ValueError("Selected source names must be unique.")
            if not is_regex:
                raise ValueError("Source selections require a numeric pattern request.")
        if kind in {"vector", "distribution", "histogram"} and value["statistics_only"]:
            if not params.get("statistics"):
                raise ValueError("Statistics-only parsing requires at least one selected summary.")
        if (
            kind == "vector"
            and not scalar_pattern_vector
            and not value["statistics_only"]
            and not params.get("entries")
        ):
            raise ValueError("Vector parsing requires selected entries.")
        if kind == "distribution" and not value["statistics_only"]:
            if not {"minimum", "maximum"}.issubset(params):
                raise ValueError("Distribution parsing requires explicit minimum and maximum.")
            minimum, maximum = params["minimum"], params["maximum"]
            if any(type(bound) not in (int, float) for bound in (minimum, maximum)):
                raise TypeError("Distribution bounds must be numbers.")
            if cast(float, minimum) > cast(float, maximum):
                raise ValueError("Distribution minimum must not exceed maximum.")
        if kind == "histogram":
            bins = params.get("bins", 0)
            if type(bins) is not int or bins < 0:
                raise ValueError("Histogram bins must be a non-negative integer.")
            maximum = params.get("max_range", 0.0)
            if type(maximum) not in (int, float) or cast(float, maximum) < 0:
                raise ValueError("Histogram max_range must be a non-negative number.")
            if bool(bins) != bool(maximum):
                raise ValueError("Histogram rebinning requires bins and max_range together.")
        if kind == "configuration":
            fallback = params.get("on_empty")
            if fallback is not None and not isinstance(fallback, str):
                raise TypeError("Configuration on_empty must be text or null.")
            params["on_empty"] = fallback or "None"
        return StatConfig(
            name=name,
            type=kind,
            repeat=repeat,
            params=cast(dict[str, StatParamValue], params),
            statistics_only=value["statistics_only"],
            is_regex=is_regex,
            keep_indices=value["keep_indices"],
            source_name=source,
        )

    @classmethod
    def validate_template_payload(
        cls, value: object, is_placeholder: Callable[[object], bool]
    ) -> None:
        """Check a recipe's current wire shape without executing unresolved operands."""
        if not isinstance(value, dict) or set(value) != _FIELDS:
            raise ValueError(
                "A recipe statistic must use the complete current configuration shape."
            )
        for field in ("name", "type"):
            cls._text(value[field], field)
        source = value["source_name"]
        if source is not None:
            cls._text(source, "source_name")
        repeat = value["repeat"]
        if not is_placeholder(repeat) and (type(repeat) is not int or repeat < 1):
            raise ValueError("Statistic repeat must be a positive integer or declared placeholder.")
        for flag in ("statistics_only", "is_regex", "keep_indices"):
            if type(value[flag]) is not bool and not is_placeholder(value[flag]):
                raise TypeError(f"Statistic {flag} must be boolean or a declared placeholder.")
        params = value["params"]
        if not isinstance(params, dict):
            raise TypeError("Statistic params must be an object.")
        source_type = params.get("source_type")
        if not is_placeholder(source_type):
            cls._text(source_type, "source_type")
            if not _PARAM_NAME.fullmatch(cast(str, source_type)):
                raise ValueError("Statistic source_type must be an exact backend identifier.")
        kind = value["type"]
        if not is_placeholder(kind) and not _PARAM_NAME.fullmatch(kind):
            raise ValueError("Statistic type must be an exact snake_case backend identifier.")
        allowed = _COMMON_PARAMS | _TYPE_PARAMS.get(kind, frozenset(params))
        if set(params) - allowed:
            raise ValueError(
                f"Unsupported {kind} statistic options: {sorted(set(params) - allowed)}."
            )
        for key, item in params.items():
            if not isinstance(key, str) or not _PARAM_NAME.fullmatch(key):
                raise ValueError("Statistic option names must be snake_case identifiers.")
            if is_placeholder(item):
                continue
            if isinstance(item, list) and any(not isinstance(entry, str) for entry in item):
                raise TypeError(f"Statistic option {key} must contain text entries.")
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError(f"Statistic option {key} must be finite.")
            if key in {"entries", "statistics", "selected_sources"}:
                if not isinstance(item, list) or any(not isinstance(entry, str) for entry in item):
                    raise TypeError(f"Statistic {key} must be a list of text entries.")
            elif key == "bins":
                if type(item) is not int:
                    raise TypeError("Histogram bins must be an integer.")
            elif key in {"minimum", "maximum", "max_range"}:
                if type(item) not in (int, float) or not math.isfinite(item):
                    raise TypeError(f"Statistic {key} must be a finite number.")
            elif key == "on_empty":
                if item is not None and not isinstance(item, str):
                    raise TypeError("Configuration on_empty must be text or null.")
            elif key == "source_type":
                cls._text(item, "source_type")
            elif item is not None and type(item) not in (str, int, float, bool, list):
                raise TypeError(f"Statistic option {key} has an unsupported value type.")

    @classmethod
    def validate(cls, config: StatConfig) -> StatConfig:
        """Own and validate a runnable value; dictionaries and duck objects are rejected."""
        if not isinstance(config, StatConfig):
            raise TypeError("Runnable parser variables must be StatConfig instances.")
        return cls.from_payload({field: getattr(config, field) for field in _FIELDS})

    @classmethod
    def to_payload(cls, config: StatConfig) -> dict[str, Any]:
        """Serialize every current field without UI identity or draft options."""
        checked = cls.validate(config)
        return {field: deepcopy(getattr(checked, field)) for field in sorted(_FIELDS)}

    @classmethod
    def from_draft(cls, draft: ParseVariableConfig) -> StatConfig:
        """Compile an editable UI draft only when it is complete enough to run."""
        draft = cls.validate_draft(draft)
        kind = draft.get("type", "")
        params = draft.get("params", {})
        if not cast(str, params.get("source_type", "")).strip():
            raise StatConfigDraftIncomplete("Declare the raw source type before parsing.")
        if "selected_sources" in params and not params["selected_sources"]:
            raise StatConfigDraftIncomplete("Select at least one concrete source before parsing.")
        if not draft.get("name", "").strip() or not kind.strip():
            raise StatConfigDraftIncomplete(
                "A statistic name and type are required before parsing."
            )
        if draft.get("keep_indices", False) and not PatternIndexService.is_pattern_variable(
            draft.get("source_name") or draft.get("name", "")
        ):
            raise StatConfigDraftIncomplete(
                "Choose a numeric pattern before keeping source indices."
            )
        source_name = draft.get("source_name")
        if source_name is not None and not source_name.strip():
            raise StatConfigDraftIncomplete("A source statistic name is required before parsing.")
        if draft.get("repeat", 1) < 1:
            raise StatConfigDraftIncomplete("Repeat must be positive before parsing.")
        if (
            kind == "vector"
            and params.get("source_type") == "scalar"
            and not PatternIndexService.is_pattern_variable(
                draft.get("source_name") or draft.get("name", "")
            )
        ):
            raise StatConfigDraftIncomplete(
                "Choose a numeric source pattern for scalar vector output."
            )
        if kind in {"vector", "distribution", "histogram"} and draft.get("statistics_only", False):
            if not params.get("statistics"):
                raise StatConfigDraftIncomplete("Select at least one summary before parsing.")
        if (
            kind == "vector"
            and not (
                params.get("source_type") == "scalar"
                and PatternIndexService.is_pattern_variable(
                    draft.get("source_name") or draft.get("name", "")
                )
            )
            and not draft.get("statistics_only", False)
            and not params.get("entries")
        ):
            raise StatConfigDraftIncomplete("Select vector entries before parsing.")
        if kind == "distribution" and not draft.get("statistics_only", False):
            if params.get("minimum") is None or params.get("maximum") is None:
                raise StatConfigDraftIncomplete("Set distribution bounds before parsing.")
            if cast(float, params["minimum"]) > cast(float, params["maximum"]):
                raise StatConfigDraftIncomplete("Order distribution bounds before parsing.")
        if kind == "histogram" and bool(params.get("bins", 0)) != bool(params.get("max_range", 0)):
            raise StatConfigDraftIncomplete("Complete histogram rebinning settings before parsing.")
        payload = {
            "name": draft.get("name"),
            "type": draft.get("type"),
            "repeat": draft.get("repeat", 1),
            "source_name": draft.get("source_name"),
            "statistics_only": draft.get("statistics_only", False),
            "is_regex": draft.get("is_regex", False),
            "keep_indices": draft.get("keep_indices", False),
            "params": deepcopy(params),
        }
        return cls.from_payload(payload)

    @classmethod
    def validate_draft(cls, value: object, *, ui_identity: bool = True) -> ParseVariableConfig:
        """Validate the current editable shape without requiring runnable semantics."""
        if not isinstance(value, dict):
            raise TypeError("A parser variable draft must be an object.")
        allowed = _DRAFT_FIELDS if ui_identity else _DRAFT_FIELDS - {"_id"}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"Unsupported parser draft fields: {sorted(unknown)}.")
        for key in ("name", "type"):
            if key in value and not isinstance(value[key], str):
                raise TypeError(f"Parser draft {key} must be text.")
        source = value.get("source_name")
        if source is not None and not isinstance(source, str):
            raise TypeError("Parser draft source_name must be text or null.")
        kind = value.get("type", "")
        if kind and not _PARAM_NAME.fullmatch(kind):
            raise ValueError("Statistic type must be an exact snake_case backend identifier.")
        if "repeat" in value and type(value["repeat"]) is not int:
            raise TypeError("Parser draft repeat must be an integer.")
        for key in ("statistics_only", "keep_indices", "is_regex"):
            if key in value and type(value[key]) is not bool:
                raise TypeError(f"Parser draft {key} must be a boolean.")
        params = value.get("params", {})
        if not isinstance(params, dict):
            raise TypeError("Parser draft params must be an object.")
        cls._params(kind, params)
        if (
            kind == "vector"
            and params.get("source_type") == "scalar"
            and (
                "entries" in params
                or params.get("statistics")
                or value.get("statistics_only", False)
            )
        ):
            raise ValueError("Scalar pattern vector entries derive only from source instances.")
        for key in ("minimum", "maximum", "max_range"):
            if key in params and params[key] is not None and type(params[key]) not in (int, float):
                raise TypeError(f"Parser draft {key} must be numeric or null.")
        if "bins" in params and type(params["bins"]) is not int:
            raise TypeError("Parser draft bins must be an integer.")
        return cast(ParseVariableConfig, deepcopy(value))

    @classmethod
    def to_snapshot(cls, draft: ParseVariableConfig) -> dict[str, Any]:
        """Persist an explicit current draft or runnable value without UI identity."""
        checked = cls.validate_draft(draft)
        try:
            configured = cls.from_draft(checked)
        except StatConfigDraftIncomplete:
            return {
                "state": "draft",
                "fields": {key: item for key, item in checked.items() if key != "_id"},
            }
        return {"state": "runnable", "config": cls.to_payload(configured)}

    @classmethod
    def from_snapshot(cls, value: object) -> ParseVariableConfig:
        """Restore only the explicit current snapshot union into editable state."""
        if not isinstance(value, dict):
            raise TypeError("A parser variable snapshot must be an object.")
        if value.get("state") == "runnable" and set(value) == {"state", "config"}:
            return cls.to_draft(cls.from_payload(value["config"]))
        if value.get("state") == "draft" and set(value) == {"state", "fields"}:
            draft = cls.validate_draft(value["fields"], ui_identity=False)
            return cast(ParseVariableConfig, {**draft, "_id": ""})
        raise ValueError(
            "A parser variable snapshot must explicitly declare draft or runnable state."
        )

    @classmethod
    def to_draft(cls, config: StatConfig, identifier: str = "") -> ParseVariableConfig:
        """Project a runnable value into editable fields with separate UI identity."""
        return cast(ParseVariableConfig, {**cls.to_payload(config), "_id": identifier})

    @classmethod
    def from_scanned(
        cls, value: ScannedVariableDict, internal_stats: frozenset[str]
    ) -> ParseVariableConfig:
        """Project current scanner metadata into an independently owned editable draft."""
        ScannedVariable.from_dict(value)
        kind = value["type"]
        params: dict[str, StatParamValue] = {"source_type": value["source_type"]}
        if kind in {"vector", "histogram"} and not (
            kind == "vector" and value["source_type"] == "scalar"
        ):
            entries = value.get("entries", [])
            params["entries"] = [entry for entry in entries if entry not in internal_stats]
            params["statistics"] = [entry for entry in entries if entry in internal_stats]
        if kind == "distribution":
            for bound in ("minimum", "maximum"):
                if bound in value:
                    params[bound] = value[bound]  # type: ignore[literal-required]
        return cls.validate_draft(
            {
                "name": value["name"],
                "type": kind,
                "params": params,
                "statistics_only": kind in {"vector", "histogram"}
                and not params.get("entries")
                and bool(params.get("statistics")),
            }
        )

    @classmethod
    def validate_many(cls, configs: Sequence[StatConfig]) -> list[StatConfig]:
        """Validate and independently own every runnable variable in order."""
        return [cls.validate(config) for config in configs]
