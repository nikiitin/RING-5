"""Owned, bounded source request values independent of editor or filename state."""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from typing import cast

from src.core.common.parsed_output_codec import unique_json_object
from src.core.common.security_limits import (
    MAX_PARSED_CELL_CHARACTERS,
    MAX_PARSE_RESULT_BYTES,
    MAX_PARSE_VARIABLES,
    MAX_PARSE_MATRIX_CELLS,
    MAX_REGEX_CANDIDATES,
    MAX_ANALYSIS_RECIPE_DEPTH,
    MAX_PIPELINE_CONFIG_BYTES,
    MAX_PIPELINE_CONFIG_STEPS,
)
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.common.source_matching import request_scanned_variables
from src.core.common.import_options_codec import ImportOptionsCodec
from src.core.models.data_models import ScannedVariableDict
from src.core.models.parsing_models import PARSER_RESULT_VERSION, ScannedVariable, StatConfig
from src.core.models.source_context_models import (
    CsvPolicy,
    CsvSourceContext,
    InferredCsvPolicy,
    LoadedDataOrigin,
    ParserSourceContext,
    ReviewedCsvPolicy,
    SourceContext,
)


def _validate_source_json(value: object, *, byte_limit: int) -> None:
    """Admit bounded primitive metadata before ownership or escaped-text allocation."""
    active: set[int] = set()
    remaining = byte_limit
    remaining_items = 8 * MAX_PARSE_MATRIX_CELLS

    def check(item: object, depth: int) -> None:
        nonlocal remaining, remaining_items
        remaining -= 1
        remaining_items -= 1
        if remaining < 0 or remaining_items < 0 or depth > MAX_ANALYSIS_RECIPE_DEPTH:
            raise ValueError("Source request exceeds its value budget.")
        if type(item) is str:
            if len(item) > MAX_PARSED_CELL_CHARACTERS:
                raise ValueError("Source request text exceeds its character limit.")
            remaining -= len(item.encode("utf-8"))
        elif item is None or type(item) is bool:
            return
        elif type(item) is int:
            if item.bit_length() > 128:
                raise ValueError("Source request integer exceeds its value budget.")
        elif type(item) is float:
            if not math.isfinite(item):
                raise ValueError("Source request numbers must be finite.")
        elif type(item) is list or type(item) is dict:
            if id(item) in active:
                raise ValueError("Source request contains cyclic metadata.")
            active.add(id(item))
            try:
                if type(item) is dict:
                    for key, child in item.items():
                        if type(key) is not str:
                            raise TypeError("Source request keys must be text.")
                        check(key, depth + 1)
                        check(child, depth + 1)
                else:
                    assert type(item) is list
                    for child in item:
                        check(child, depth + 1)
            finally:
                active.remove(id(item))
        else:
            raise TypeError("Source request contains an unsupported value.")

    check(value, 0)


def encode_source_json(value: object, *, byte_limit: int = MAX_PARSE_RESULT_BYTES) -> str:
    """Bound primitive source metadata before encoding or allocating escaped text."""
    _validate_source_json(value, byte_limit=byte_limit)
    parts: list[str] = []
    size = 0
    encoder = json.JSONEncoder(
        ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    )
    for part in encoder.iterencode(value):
        size += len(part.encode("utf-8"))
        if size > byte_limit:
            raise ValueError("Source request exceeds its byte budget.")
        parts.append(part)
    return "".join(parts)


def _json_array(value: str, limit: int) -> list[object]:
    if type(value) is not str or len(value) > MAX_PARSE_RESULT_BYTES:
        raise ValueError("Source request requires bounded JSON text.")
    if len(value.encode("utf-8")) > MAX_PARSE_RESULT_BYTES:
        raise ValueError("Source request exceeds its byte budget.")
    try:
        result = json.loads(value, object_pairs_hook=unique_json_object)
    except (ValueError, RecursionError) as exc:
        raise ValueError("Source request contains invalid JSON.") from exc
    if type(result) is not list or len(result) > limit:
        raise ValueError("Source request requires a bounded JSON array.")
    return cast(list[object], result)


class SourceContextCodec:
    """Create immutable actual requests and decode fresh values for execution."""

    @staticmethod
    def parser(
        *,
        stats_path: str,
        stats_pattern: str,
        strategy_type: str,
        variables: Sequence[StatConfig],
        scanned_variables: Sequence[ScannedVariableDict],
        simulator: str | None,
        scan_limit: int | None,
        strict: bool,
        parser_contract_version: str = str(PARSER_RESULT_VERSION),
        metadata_byte_limit: int = MAX_PARSE_RESULT_BYTES,
    ) -> ParserSourceContext:
        """Own executable arguments and complete relevant discovery records.

        Editor discovery remains independent. Only records needed by a literal
        source or numeric pattern enter the immutable execution/replay snapshot.
        """
        if (
            type(metadata_byte_limit) is not int
            or not 0 < metadata_byte_limit <= MAX_PARSE_RESULT_BYTES
        ):
            raise ValueError("Source metadata byte limit must be a positive bounded integer.")
        configs = StatConfigCodec.validate_many(variables)
        if len(scanned_variables) > MAX_REGEX_CANDIDATES:
            raise ValueError("Source scanner metadata exceeds its variable budget.")
        _validate_source_json(list(scanned_variables), byte_limit=MAX_PARSE_RESULT_BYTES)
        retained = request_scanned_variables(configs, scanned_variables)
        source = ParserSourceContext(
            stats_path,
            stats_pattern,
            strategy_type,
            encode_source_json(
                [StatConfigCodec.to_payload(config) for config in configs],
                byte_limit=metadata_byte_limit,
            ),
            encode_source_json(
                retained,
                byte_limit=metadata_byte_limit,
            ),
            simulator,
            parser_contract_version,
            scan_limit,
            strict,
        )
        SourceContextCodec.scanned_payloads(source)
        return source

    @staticmethod
    def variables(source: ParserSourceContext) -> list[StatConfig]:
        """Decode fresh runnable variables from the exact owned request."""
        return [
            StatConfigCodec.from_payload(value)
            for value in _json_array(source.variables_json, MAX_PARSE_VARIABLES)
        ]

    @staticmethod
    def scanned_payloads(source: ParserSourceContext) -> list[ScannedVariableDict]:
        """Decode the exact owned evidence payload without inferred geometry."""
        values = _json_array(source.scanned_variables_json, MAX_REGEX_CANDIDATES)
        for value in values:
            ScannedVariable.from_dict(cast(ScannedVariableDict, value))
        return cast(list[ScannedVariableDict], values)

    @staticmethod
    def scanned_variables(source: ParserSourceContext) -> list[ScannedVariable]:
        """Project generic execution models from the same current owned payloads."""
        return [
            ScannedVariable.from_dict(value)
            for value in SourceContextCodec.scanned_payloads(source)
        ]

    @staticmethod
    def csv_policy_payload(policy: CsvPolicy) -> dict[str, object]:
        """Encode the explicit inferred or reviewed CSV request policy."""
        if type(policy) is InferredCsvPolicy:
            return {"kind": "inferred", "configuration_columns": list(policy.configuration_columns)}
        if type(policy) is ReviewedCsvPolicy:
            return {
                "kind": "reviewed",
                "options": ImportOptionsCodec.to_payload(policy.options),
                "rejected_rows": "exclude",
            }
        raise TypeError("Unsupported CSV request policy.")

    @staticmethod
    def csv_policy_from_payload(value: object) -> CsvPolicy:
        """Decode one current CSV policy without reconstructing inferred types."""
        if type(value) is not dict:
            raise TypeError("CSV request policy must be an object.")
        if value.get("kind") == "inferred" and value.keys() == {"kind", "configuration_columns"}:
            columns = value["configuration_columns"]
            if type(columns) is not list:
                raise TypeError("CSV configuration_columns must be a list.")
            return InferredCsvPolicy(tuple(columns))
        if value.get("kind") == "reviewed" and value.keys() == {"kind", "options", "rejected_rows"}:
            if value["rejected_rows"] != "exclude":
                raise ValueError("Reviewed CSV imports require rejected_rows='exclude'.")
            return ReviewedCsvPolicy(ImportOptionsCodec.from_payload(value["options"]))
        raise ValueError("CSV request policy has unsupported fields or kind.")

    @staticmethod
    def to_payload(source: SourceContext) -> dict[str, object]:
        """Project the exact source request into a fresh current JSON value."""
        if type(source) is CsvSourceContext:
            return {
                "kind": "csv",
                "path": source.path,
                "policy": SourceContextCodec.csv_policy_payload(source.policy),
            }
        if type(source) is not ParserSourceContext:
            raise TypeError("Source context must be a current explicit request.")
        return {
            "kind": "parser",
            "stats_path": source.stats_path,
            "stats_pattern": source.stats_pattern,
            "strategy_type": source.strategy_type,
            "variables": [
                StatConfigCodec.to_payload(v) for v in SourceContextCodec.variables(source)
            ],
            "scanned_variables": SourceContextCodec.scanned_payloads(source),
            "simulator": source.simulator,
            "parser_contract_version": source.parser_contract_version,
            "scan_limit": source.scan_limit,
            "strict": source.strict,
        }

    @staticmethod
    def from_payload(value: object) -> SourceContext:
        """Validate the exact current source shape before retaining replay facts."""
        if type(value) is not dict:
            raise TypeError("Source context must be an object.")
        if value.get("kind") == "csv" and value.keys() == {"kind", "path", "policy"}:
            return CsvSourceContext(
                value["path"], SourceContextCodec.csv_policy_from_payload(value["policy"])
            )
        fields = {
            "kind",
            "stats_path",
            "stats_pattern",
            "strategy_type",
            "variables",
            "scanned_variables",
            "simulator",
            "parser_contract_version",
            "scan_limit",
            "strict",
        }
        if value.get("kind") != "parser" or value.keys() != fields:
            raise ValueError("Source context has unsupported fields or kind.")
        context = ParserSourceContext(
            value["stats_path"],
            value["stats_pattern"],
            value["strategy_type"],
            encode_source_json(value["variables"]),
            encode_source_json(value["scanned_variables"]),
            value["simulator"],
            value["parser_contract_version"],
            value["scan_limit"],
            value["strict"],
        )
        SourceContextCodec.variables(context)
        SourceContextCodec.scanned_payloads(context)
        return context

    @staticmethod
    def encode(source: SourceContext) -> str:
        """Encode bounded current request metadata for existing durable owners."""
        return encode_source_json(
            SourceContextCodec.to_payload(source), byte_limit=MAX_PARSE_RESULT_BYTES
        )

    @staticmethod
    def decode(payload: str) -> SourceContext:
        """Decode a bounded exact current source document."""
        if type(payload) is not str or len(payload.encode("utf-8")) > MAX_PARSE_RESULT_BYTES:
            raise ValueError("Source context exceeds its byte budget.")
        try:
            value = json.loads(payload, object_pairs_hook=unique_json_object)
        except (ValueError, RecursionError) as exc:
            raise ValueError("Source context contains invalid JSON.") from exc
        return SourceContextCodec.from_payload(value)

    @staticmethod
    def origin(
        source: SourceContext,
        transformations: Sequence[dict[str, object]] = (),
        *,
        complete: bool = True,
    ) -> LoadedDataOrigin:
        """Own already validated runnable steps and their actual source request."""
        source = SourceContextCodec.from_payload(SourceContextCodec.to_payload(source))
        return LoadedDataOrigin(
            source,
            encode_source_json(list(transformations), byte_limit=MAX_PIPELINE_CONFIG_BYTES),
            complete,
        )

    @staticmethod
    def transformations(origin: LoadedDataOrigin) -> list[dict[str, object]]:
        """Return fresh owned step values for canonical domain validation/execution."""
        values = _json_array(origin.transformations_json, MAX_PIPELINE_CONFIG_STEPS)
        if any(type(value) is not dict for value in values):
            raise TypeError("Loaded source transformations must be objects.")
        return cast(list[dict[str, object]], values)

    @staticmethod
    def origin_payload(origin: LoadedDataOrigin | None) -> dict[str, object] | None:
        """Project nullable frame-associated replay facts for a current portfolio."""
        if origin is None:
            return None
        if type(origin) is not LoadedDataOrigin:
            raise TypeError("Loaded origin must be a LoadedDataOrigin value.")
        return {
            "source": SourceContextCodec.to_payload(origin.source),
            "transformations": SourceContextCodec.transformations(origin),
            "complete": origin.complete,
        }

    @staticmethod
    def origin_from_payload(value: object) -> LoadedDataOrigin | None:
        """Decode ownership facts; runnable pipeline validation belongs to Domain."""
        if value is None:
            return None
        if type(value) is not dict or value.keys() != {"source", "transformations", "complete"}:
            raise ValueError("Loaded origin requires exactly the current fields.")
        transformations = value["transformations"]
        if type(transformations) is not list or len(transformations) > MAX_PIPELINE_CONFIG_STEPS:
            raise ValueError("Loaded source transformations require a bounded list.")
        origin = LoadedDataOrigin(
            SourceContextCodec.from_payload(value["source"]),
            encode_source_json(transformations, byte_limit=MAX_PIPELINE_CONFIG_BYTES),
            value["complete"],
        )
        SourceContextCodec.transformations(origin)
        return origin
