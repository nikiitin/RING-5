"""Typed parser values preserve text, ownership and atomic publication integrity."""

from __future__ import annotations

import math
from dataclasses import FrozenInstanceError, replace
from decimal import InvalidOperation, localcontext
from pathlib import Path

import pytest

from src.core.common import parsed_output_codec
from src.core.common.parsed_output_codec import (
    ParsedOutputDigest,
    encode_parsed_schema,
    read_numeric_wire,
    read_parsed_value,
    render_parsed_value,
)
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedColumn,
    ParsedFileResult,
    ParsedOutput,
    ParsedSchema,
    ParsedVariableResult,
    ParsedVariableSchema,
)
from src.core.services import parsed_output_service
from src.core.services.parsed_output_service import ParsedOutputService


def _scalar(name: str, value: float | str, *, column: str | None = None) -> ParsedVariableResult:
    kind = "number" if type(value) is float else "text"
    return ParsedVariableResult(name, kind, "scalar", (ParsedCell(column or name, kind, value),))


def _result(source: str, value: float = 1.25) -> ParsedFileResult:
    return ParsedFileResult(source, (_scalar("value", value),))


@pytest.mark.parametrize(
    "literal", ["NA", "nan", "NaN", "", "001", "1e3", "μarch", "  whitespace  ", "95%", "a\nb"]
)
def test_typed_publication_and_loading_preserve_literal_text_and_numeric_missingness(
    tmp_path: Path, literal: str
) -> None:
    result = ParsedFileResult(
        "source",
        (_scalar("label", literal), _scalar("value", 1.25), _scalar("absent", math.nan)),
        (ParsedCell("config_json", "text", '{"Case":"95% μ"}'),),
    )
    table = ParsedOutputService.resolve([result], ["label", "value", "absent"])
    output = ParsedOutputService.publish(tmp_path / "results.csv", table)
    restored = ParsedOutputService.read(output)
    assert restored.rows[0][0] == literal
    assert type(restored.rows[0][0]) is str
    assert restored.rows[0][1] == 1.25
    assert math.isnan(restored.rows[0][2])
    assert restored.missing_variables == ("absent",)
    frame = ParsedOutputService.to_frame(output)
    assert frame["label"].iloc[0] == literal
    assert frame["value"].iloc[0] == 1.25
    assert frame["config_json"].iloc[0] == '{"Case":"95% μ"}'


def test_schema_union_is_order_independent_and_has_explicit_owners(tmp_path: Path) -> None:
    first = ParsedFileResult(
        "a",
        (
            ParsedVariableResult("v", "number", "entries", (ParsedCell("v..a", "number", 2.0),)),
            _scalar("v..a", "001", column="literal"),
        ),
    )
    second = ParsedFileResult(
        "b",
        (
            ParsedVariableResult("v", "number", "entries", (ParsedCell("v..b", "number", 3.0),)),
            _scalar("v..a", "", column="literal"),
        ),
    )
    left = ParsedOutputService.resolve([first, second], ["v", "v..a"])
    right = ParsedOutputService.resolve([second, first], ["v", "v..a"])
    assert left.schema == right.schema
    assert left.source_paths == right.source_paths == ("a", "b")
    assert [(column.name, column.owner) for column in left.schema.columns] == [
        ("v..a", "v"),
        ("v..b", "v"),
        ("literal", "v..a"),
    ]
    assert math.isnan(left.rows[0][1]) and math.isnan(left.rows[1][0])
    one = ParsedOutputService.publish(tmp_path / "one.csv", left)
    two = ParsedOutputService.publish(tmp_path / "two.csv", right)
    assert one.sha256 == two.sha256
    assert Path(one.csv_path).read_bytes() == Path(two.csv_path).read_bytes()


def test_unobserved_dynamic_entries_do_not_invent_a_physical_column(tmp_path: Path) -> None:
    result = ParsedFileResult("source", (ParsedVariableResult("v", "number", "entries", ()),))
    table = ParsedOutputService.resolve([result], ["v"])
    assert table.schema.columns == () and table.rows == ((),)
    output = ParsedOutputService.publish(tmp_path / "empty-schema.csv", table)
    restored = ParsedOutputService.read(output)
    assert restored.rows == ((),)
    assert restored.missing_variables == ("v",)
    assert ParsedOutputService.to_frame(output).shape == (1, 0)


@pytest.mark.parametrize("metadata", [True, False])
def test_missing_text_rejects_before_publication(metadata: bool) -> None:
    if metadata:
        first = replace(_result("a"), metadata=(ParsedCell("tag", "text", ""),))
        second = _result("b")
    else:
        first = ParsedFileResult(
            "a",
            (ParsedVariableResult("value", "text", "entries", (ParsedCell("tag", "text", ""),)),),
        )
        second = ParsedFileResult("b", (ParsedVariableResult("value", "text", "entries", ()),))
    with pytest.raises(ValueError, match="Missing explicit text"):
        ParsedOutputService.resolve([first, second], ["value"])


@pytest.mark.parametrize("mismatch", ["owner", "kind", "shape", "duplicate_source"])
def test_explicit_schema_and_source_collisions_are_rejected(mismatch: str) -> None:
    first = _result("a")
    if mismatch == "owner":
        first = ParsedFileResult("a", (_scalar("value", 1.0, column="shared"), _scalar("b", 2.0)))
        second = ParsedFileResult("b", (_scalar("value", 1.0), _scalar("b", 2.0, column="shared")))
        order = ["value", "b"]
    elif mismatch == "kind":
        first = replace(first, metadata=(ParsedCell("tag", "text", "NaN"),))
        second = replace(_result("b"), metadata=(ParsedCell("tag", "number", math.nan),))
        order = ["value"]
    elif mismatch == "shape":
        second = ParsedFileResult("b", (ParsedVariableResult("value", "number", "entries", ()),))
        order = ["value"]
    else:
        second = first
        order = ["value"]
    with pytest.raises(ValueError, match="collision|Conflicting|provenance"):
        ParsedOutputService.resolve([first, second], order)


def test_metadata_namespace_does_not_reserve_a_logical_name() -> None:
    result = ParsedFileResult(
        "source", (_scalar("metadata", "NA"),), (ParsedCell("tag", "text", "001"),)
    )
    table = ParsedOutputService.resolve([result], ["metadata"])
    assert [(column.owner, column.kind) for column in table.schema.columns] == [
        ("metadata", "text"),
        (None, "text"),
    ]


def test_schema_substitution_changes_typed_digest_even_when_csv_bytes_match(tmp_path: Path) -> None:
    number = ParsedOutputService.resolve([_result("source", math.nan)], ["value"])
    text = ParsedOutputService.resolve(
        [ParsedFileResult("source", (_scalar("value", "NaN"),))], ["value"]
    )
    numeric_output = ParsedOutputService.publish(tmp_path / "number.csv", number)
    text_output = ParsedOutputService.publish(tmp_path / "text.csv", text)
    assert Path(numeric_output.csv_path).read_bytes() == Path(text_output.csv_path).read_bytes()
    assert numeric_output.sha256 != text_output.sha256
    with pytest.raises(ValueError, match="digest"):
        ParsedOutputService.read(replace(numeric_output, schema=text.schema))
    digest = ParsedOutputDigest(number.schema)
    digest.update(Path(numeric_output.csv_path).read_bytes())
    assert digest.hexdigest() == numeric_output.sha256


@pytest.mark.parametrize("failure", ["fsync", "replace", "descriptor", "promotion"])
def test_publication_failure_preserves_old_output_and_cleans_temporaries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    target = tmp_path / "results.csv"
    target.write_bytes(b"old-output")
    table = ParsedOutputService.resolve([_result("source")], ["value"])

    def fail(*args, **kwargs):
        raise RuntimeError("injected publication failure")

    callback = None
    if failure == "fsync":
        monkeypatch.setattr(parsed_output_service.os, "fsync", fail)
    elif failure == "replace":
        monkeypatch.setattr(parsed_output_service.os, "replace", fail)
    elif failure == "descriptor":
        monkeypatch.setattr(parsed_output_service, "ParsedOutput", fail)
    else:
        callback = fail
    with pytest.raises(RuntimeError, match="injected"):
        ParsedOutputService.publish(target, table, after_publish=callback)
    assert target.read_bytes() == b"old-output"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["results.csv"]


def test_budgets_reject_before_writer_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    table = ParsedOutputService.resolve(
        [ParsedFileResult("source", (_scalar("value", "x" * 20),))], ["value"]
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("Budget failure reached writer allocation")

    monkeypatch.setattr(parsed_output_service, "MAX_PARSED_OUTPUT_BYTES", 10)
    monkeypatch.setattr(parsed_output_service.tempfile, "NamedTemporaryFile", forbidden)
    with pytest.raises(ValueError, match="byte limit"):
        ParsedOutputService.publish(tmp_path / "output.csv", table)
    monkeypatch.setattr(parsed_output_codec, "MAX_PARSED_SCHEMA_BYTES", 10)
    with pytest.raises(ValueError, match="descriptor byte limit"):
        encode_parsed_schema(table.schema)
    assert list(tmp_path.iterdir()) == []


def test_integrity_and_exact_header_are_checked_before_loading(tmp_path: Path) -> None:
    table = ParsedOutputService.resolve([_result("source")], ["value"])
    output = ParsedOutputService.publish(tmp_path / "results.csv", table)
    Path(output.csv_path).write_bytes(b"value\r\n2.25\r\n")
    with pytest.raises(ValueError, match="digest"):
        ParsedOutputService.to_frame(output)
    digest = ParsedOutputDigest(output.schema)
    digest.update(b"other\r\n1.25\r\n")
    Path(output.csv_path).write_bytes(b"other\r\n1.25\r\n")
    with pytest.raises(ValueError, match="header"):
        ParsedOutputService.read(replace(output, sha256=digest.hexdigest()))


def test_same_content_path_replacement_during_read_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    table = ParsedOutputService.resolve([_result("source")], ["value"])
    path = tmp_path / "results.csv"
    output = ParsedOutputService.publish(path, table)
    content = path.read_bytes()
    original = Path.stat

    def swap(current, *args, **kwargs):
        if current == path:
            replacement = tmp_path / "replacement.csv"
            replacement.write_bytes(content)
            replacement.replace(path)
        return original(current, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", swap)
    with pytest.raises(ValueError, match="changed while"):
        ParsedOutputService.read(output)


@pytest.mark.parametrize("value", [True, 1, None, "1.0"])
def test_numeric_cells_reject_untyped_values(value: object) -> None:
    with pytest.raises(TypeError, match="exact float"):
        ParsedCell("value", "number", value)


def test_result_models_own_only_immutable_typed_collections() -> None:
    variable = _scalar("value", 1.25)
    result = ParsedFileResult("source", (variable,))
    with pytest.raises(FrozenInstanceError):
        result.source_path = "changed"
    with pytest.raises(TypeError, match="immutable tuple"):
        ParsedVariableResult("value", "number", "scalar", [variable.cells[0]])
    with pytest.raises(ValueError, match="exactly one"):
        ParsedVariableResult("value", "number", "scalar", ())
    with pytest.raises(ValueError, match="Metadata column collision"):
        ParsedFileResult("source", (variable,), (ParsedCell("value", "text", "001"),))
    with pytest.raises(ValueError, match="unknown owner"):
        ParsedSchema(
            (ParsedVariableSchema("value", "number", "entries"),),
            (ParsedColumn("x", "number", "other"),),
        )
    with pytest.raises(ValueError, match="SHA-256"):
        ParsedOutput("results.csv", "not-a-digest", ParsedSchema((), ()))


@pytest.mark.parametrize("token", ["1e400", "-1e400", "1e-400", "-1e-400", "2e-324"])
def test_finite_numeric_wire_overflow_and_nonzero_underflow_are_rejected(token: str) -> None:
    with pytest.raises(ValueError, match="Float64 range"):
        read_numeric_wire(token)


@pytest.mark.parametrize("token", ["5e-324", "0", "-0.0", "1.25", "inf", "-inf", "NaN"])
def test_numeric_wire_keeps_representable_and_explicit_nonfinite_values(token: str) -> None:
    value = read_numeric_wire(token)
    expected = float(token)
    assert math.isnan(value) if math.isnan(expected) else value == expected
    if token == "-0.0":
        assert math.copysign(1, value) == -1
    encoded = render_parsed_value("number", value)
    restored = read_parsed_value("number", encoded)
    assert math.isnan(restored) if math.isnan(value) else restored == value
    assert read_parsed_value("text", token) == token


def test_wire_range_checks_do_not_depend_on_decimal_context_or_exponent_size() -> None:
    assert read_numeric_wire("0e-1000000000000000000000") == 0.0
    with localcontext() as context:
        context.traps[InvalidOperation] = False
        with pytest.raises(ValueError, match="Float64 range"):
            read_numeric_wire("1e1000000000000000000000")
        with pytest.raises(ValueError, match="Float64 range"):
            read_numeric_wire("1e-1000000000000000000000")
