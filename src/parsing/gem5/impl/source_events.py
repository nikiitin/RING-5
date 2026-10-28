"""Exact immutable records from the shared gem5 text decoder."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Literal, cast

from src.core.common.parsed_output_codec import unique_json_object
from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import MAX_PARSED_CELL_CHARACTERS, MAX_PARSE_RESULT_BYTES
from src.core.models.parse_failure_models import ParseDataValueError
from src.core.models.source_evidence import SourceKindEvidence, decode_source_kind_evidence

SOURCE_WIRE_READY = "READY source-events-1"


@dataclass(frozen=True)
class Measurement:
    """One literal wire value or an ordered oneline cell sequence."""

    name: str
    shape: Literal["scalar", "configuration", "entry", "oneline"]
    entry: str | None = None
    value: str | None = None
    values: tuple[str, ...] = ()
    reported_geometry: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SourceEvidence:
    """Completed source evidence and actual printed entry labels."""

    name: str
    evidence: SourceKindEvidence
    entries: tuple[str, ...]


@dataclass(frozen=True)
class SourceFailure:
    """A bounded source-local contradiction or malformed measurement."""

    name: str
    message: str


@dataclass(frozen=True)
class DumpBoundary:
    """A real dump boundary after all preceding source evidence records."""


SourceEvent = Measurement | SourceEvidence | SourceFailure | DumpBoundary


def _text(value: object, limit: int, *, empty: bool = False) -> str:
    if type(value) is not str or len(value) > limit or (not empty and not value):
        raise ParseDataValueError(
            "Source event text must have its exact bounded string representation."
        )
    return value


def _evidence(value: object) -> SourceKindEvidence:
    """Normalize the pure evidence codec's declared JSON admission errors only."""
    try:
        return decode_source_kind_evidence(value)
    except (ValueError, TypeError) as exc:
        if type(exc) not in (ValueError, TypeError):
            raise
        raise ParseDataValueError("Invalid source contract evidence.") from exc


def decode_source_event(line: str) -> SourceEvent:
    """Validate one current decoder event without guessing source kinds.

    Raises:
        ParseDataValueError: The bounded wire record has invalid fields or values.
    """
    try:
        if type(line) is not str or len(line) > MAX_PARSE_RESULT_BYTES:
            raise ParseDataValueError("Source event exceeds the wire byte budget.")
        if len(line.encode("utf-8")) > MAX_PARSE_RESULT_BYTES:
            raise ParseDataValueError("Source event exceeds the wire byte budget.")

        def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
            try:
                return unique_json_object(pairs)
            except ValueError as exc:
                if type(exc) is not ValueError:
                    raise
                raise ParseDataValueError("Duplicate source event JSON field.") from exc

        raw = json.loads(line, object_pairs_hook=object_pairs)
        if type(raw) is not dict:
            raise ParseDataValueError("Source event must be a JSON object.")
        event = raw.get("event")
        if event == "dump" and set(raw) == {"event"}:
            return DumpBoundary()
        name = _text(raw.get("name"), MAX_INPUT_LENGTH)
        if event == "source_error" and set(raw) == {"event", "name", "message"}:
            return SourceFailure(name, _text(raw["message"], 1000))
        if event == "source" and set(raw) == {"event", "name", "source_evidence", "entries"}:
            entries = raw["entries"]
            if type(entries) is not list:
                raise ParseDataValueError("Source entries require the current list container.")
            labels = tuple(_text(entry, MAX_INPUT_LENGTH) for entry in entries)
            if labels != tuple(sorted(set(labels))):
                raise ParseDataValueError(
                    "Source entries must be distinct and canonically ordered."
                )
            return SourceEvidence(
                name,
                _evidence(raw["source_evidence"]),
                labels,
            )
        if event == "measurement":
            shape = raw.get("shape")
            if shape == "oneline" and set(raw) == {
                "event",
                "name",
                "shape",
                "values",
                "reported_geometry",
            }:
                if type(raw["values"]) is not list or not raw["values"]:
                    raise ParseDataValueError("Oneline values require a non-empty ordered list.")
                geometry = raw["reported_geometry"]
                if type(geometry) is not dict or set(geometry) - {
                    "bucket_size",
                    "min_bucket",
                    "max_bucket",
                }:
                    raise ParseDataValueError("Oneline reported geometry has invalid fields.")
                return Measurement(
                    name,
                    "oneline",
                    values=tuple(
                        _text(value, MAX_PARSED_CELL_CHARACTERS) for value in raw["values"]
                    ),
                    reported_geometry=tuple(
                        (key, _text(value, MAX_PARSED_CELL_CHARACTERS))
                        for key, value in sorted(geometry.items())
                    ),
                )
            if (
                type(shape) is str
                and shape in {"scalar", "configuration", "entry"}
                and set(raw) == {"event", "name", "shape", "entry", "value"}
            ):
                entry = raw["entry"]
                if shape == "entry":
                    entry = _text(entry, MAX_INPUT_LENGTH)
                elif entry is not None:
                    raise ParseDataValueError(
                        "A point/text measurement cannot have an entry label."
                    )
                return Measurement(
                    name,
                    cast(Literal["scalar", "configuration", "entry"], shape),
                    entry,
                    _text(raw["value"], MAX_PARSED_CELL_CHARACTERS, empty=shape == "configuration"),
                )
        raise ParseDataValueError(
            "Source event requires exactly the current fields and discriminator."
        )
    except (json.JSONDecodeError, RecursionError, UnicodeEncodeError) as exc:
        if type(exc) not in (json.JSONDecodeError, RecursionError, UnicodeEncodeError):
            raise
        raise ParseDataValueError("Malformed current gem5 source event.") from exc
