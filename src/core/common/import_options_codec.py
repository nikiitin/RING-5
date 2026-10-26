"""One value codec for the immutable reviewed-import request policy."""

from __future__ import annotations

from typing import cast

from src.core.common.security_limits import MAX_IMPORT_COLUMNS
from src.core.models.import_models import ImportColumnCorrection, ImportColumnType, ImportOptions


class ImportOptionsCodec:
    """Serialize requested options without inferring policy from imported data."""

    @staticmethod
    def to_payload(options: ImportOptions) -> dict[str, object]:
        """Return a fresh current wire value for an exact immutable options value."""
        if type(options) is not ImportOptions:
            raise TypeError("Import policy requires ImportOptions.")
        return {
            "encoding": options.encoding,
            "delimiter": options.delimiter,
            "header_row": options.header_row,
            "trim_whitespace": options.trim_whitespace,
            "null_values": list(options.null_values),
            "column_types": [
                {"column": correction.column, "import_as": correction.import_as}
                for correction in options.column_types
            ],
            "preview_rows": options.preview_rows,
        }

    @staticmethod
    def from_payload(value: object) -> ImportOptions:
        """Reject unsupported fields and mutable or mistyped option components."""
        fields = {
            "encoding",
            "delimiter",
            "header_row",
            "trim_whitespace",
            "null_values",
            "column_types",
            "preview_rows",
        }
        if type(value) is not dict or value.keys() != fields:
            raise ValueError("Import options require exactly the current fields.")
        nullable_text = (value["encoding"], value["delimiter"])
        if any(item is not None and type(item) is not str for item in nullable_text):
            raise TypeError("Import encoding and delimiter must be text or None.")
        if type(value["header_row"]) is not int or type(value["preview_rows"]) is not int:
            raise TypeError("Import header and preview limits must be integers.")
        if type(value["trim_whitespace"]) is not bool:
            raise TypeError("Import whitespace policy must be boolean.")
        nulls = value["null_values"]
        if type(nulls) is not list or len(nulls) > 50 or any(type(v) is not str for v in nulls):
            raise ValueError("Import null_values must be a bounded list of text.")
        raw_corrections = value["column_types"]
        if type(raw_corrections) is not list or len(raw_corrections) > MAX_IMPORT_COLUMNS:
            raise ValueError("Import column_types must be a bounded list.")
        corrections: list[ImportColumnCorrection] = []
        for correction in raw_corrections:
            if type(correction) is not dict or correction.keys() != {"column", "import_as"}:
                raise ValueError("Import corrections require column and import_as.")
            if type(correction["column"]) is not str or type(correction["import_as"]) is not str:
                raise TypeError("Import corrections require text fields.")
            corrections.append(
                ImportColumnCorrection(
                    correction["column"], cast(ImportColumnType, correction["import_as"])
                )
            )
        return ImportOptions(
            encoding=value["encoding"],
            delimiter=value["delimiter"],
            header_row=value["header_row"],
            trim_whitespace=value["trim_whitespace"],
            null_values=tuple(nulls),
            column_types=tuple(corrections),
            preview_rows=value["preview_rows"],
        )
