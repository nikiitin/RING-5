"""Parser CSV admission validates exact declared types, schema, rows and digest."""

from pathlib import Path

import pytest

from src.core.common.parsed_output import ParsedOutputIO
from src.core.common.parsed_output_codec import MISSING_VALUE, ParsedOutputDigest
from src.core.models.parsed_output_models import (
    ParsedCell,
    ParsedColumn,
    ParsedFileResult,
    ParsedOutput,
    ParsedSchema,
    ParsedVariableResult,
    ParsedVariableSchema,
)


def _schema(name="name"):
    return ParsedSchema(
        (
            ParsedVariableSchema(name, "text", "scalar"),
            ParsedVariableSchema("value", "number", "scalar"),
        ),
        (ParsedColumn(name, "text", name), ParsedColumn("value", "number", "value")),
    )


def _raw_output(path: Path, content: bytes):
    path.write_bytes(content)
    schema = _schema()
    digest = ParsedOutputDigest(schema)
    digest.update(content)
    return ParsedOutput(str(path), digest.hexdigest(), schema)


class TestTypedCsvAdmission:
    # [test->req~ring5.ingestion.csv-contract~2]
    def test_valid_csv(self, tmp_path):
        output = _raw_output(tmp_path / "valid.csv", b"name,value\r\nfoo,1.0\r\nbar,2.0\r\n")
        assert ParsedOutputIO.read(output).rows == (("foo", 1.0), ("bar", 2.0))

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ParsedOutputIO.read(
                ParsedOutput(str(tmp_path / "nonexistent.csv"), "0" * 64, _schema())
            )

    @pytest.mark.parametrize(
        "content",
        [
            b"",
            b"\r\nfoo,1.0\r\n",
            b"name,value\r\n",
            b"name,value,name\r\nfoo,1.0,foo\r\n",
            b"name,value\r\nfoo\r\n",
            b"name,value\r\nfoo,1.0,extra\r\n",
        ],
        ids=["empty", "empty-header", "no-data", "duplicate-header", "short-row", "wide-row"],
    )
    def test_malformed_rows_or_headers_reject_even_with_matching_raw_digest(
        self, tmp_path, content
    ):
        with pytest.raises(ValueError):
            ParsedOutputIO.read(_raw_output(tmp_path / "malformed.csv", content))

    def test_whitespace_and_unicode_column_names_are_exact_supported_data(self, tmp_path):
        name = " μ label "
        result = ParsedFileResult(
            "source",
            (
                ParsedVariableResult(name, "text", "scalar", (ParsedCell(name, "text", "001"),)),
                ParsedVariableResult(
                    "value", "number", "scalar", (ParsedCell("value", "number", float("nan")),)
                ),
            ),
        )
        output = ParsedOutputIO.publish(
            tmp_path / "unicode.csv", ParsedOutputIO.resolve([result], [name, "value"], ("source",))
        )
        assert name.encode("utf-8") in Path(output.csv_path).read_bytes()
        assert MISSING_VALUE.encode("ascii") in Path(output.csv_path).read_bytes()
        assert ParsedOutputIO.to_frame(output).columns.tolist() == [name, "value"]

    def test_vector_columns_use_explicit_owner_and_shape(self, tmp_path):
        result = ParsedFileResult(
            "source",
            (
                ParsedVariableResult(
                    "system.cpu.stat",
                    "number",
                    "entries",
                    (
                        ParsedCell("system.cpu.stat..0", "number", 1.0),
                        ParsedCell("system.cpu.stat..1", "number", 2.0),
                    ),
                ),
            ),
        )
        output = ParsedOutputIO.publish(
            tmp_path / "vector.csv",
            ParsedOutputIO.resolve([result], ["system.cpu.stat"], ("source",)),
        )
        assert ParsedOutputIO.read(output).rows == ((1.0, 2.0),)
        assert output.schema.variables[0].shape == "entries"
        assert [column.owner for column in output.schema.columns] == ["system.cpu.stat"] * 2
