"""Immutable typed values shared by simulator workers, publishers and consumers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.core.common.safe_regex import MAX_INPUT_LENGTH
from src.core.common.security_limits import (
    MAX_INCREMENTAL_CACHE_COLUMNS,
    MAX_PARSE_FILES,
    MAX_PARSE_MATRIX_CELLS,
    MAX_PARSE_VARIABLES,
)

ParsedKind = Literal["number", "text"]
ParsedShape = Literal["scalar", "entries"]
ParsedValue = float | str


def _name(value: str, field: str) -> None:
    if type(value) is not str or not value or len(value) > MAX_INPUT_LENGTH:
        raise ValueError(f"{field} must be a bounded non-empty string.")


def _kind(value: ParsedKind) -> None:
    if type(value) is not str or value not in ("number", "text"):
        raise ValueError("Parsed cell kind must be 'number' or 'text'.")


@dataclass(frozen=True)
class ParsedCell:
    """One finalized number or literal text value for an exact output column.

    Attributes:
        column: Exact physical column name without inferred ownership.
        kind: Explicit numeric or literal-text interpretation.
        value: A float, including NaN/infinity, or an exact string.
    """

    column: str
    kind: ParsedKind
    value: ParsedValue

    def __post_init__(self) -> None:
        _name(self.column, "Parsed column")
        _kind(self.kind)
        expected = float if self.kind == "number" else str
        if type(self.value) is not expected:
            raise TypeError(f"A {self.kind} cell requires an exact {expected.__name__} value.")


@dataclass(frozen=True)
class ParsedVariableSchema:
    """Declared logical variable interpretation, including empty entry output."""

    name: str
    kind: ParsedKind
    shape: ParsedShape

    def __post_init__(self) -> None:
        _name(self.name, "Parsed variable")
        _kind(self.kind)
        if type(self.shape) is not str or self.shape not in ("scalar", "entries"):
            raise ValueError("Parsed variable shape must be 'scalar' or 'entries'.")


@dataclass(frozen=True)
class ParsedVariableResult:
    """Finalized values and actual observation absence for one logical variable.

    Scalar output has exactly one cell. Entry output can have no observed columns.
    Missing measurements remain separate from numeric NaN strict-value semantics.
    """

    name: str
    kind: ParsedKind
    shape: ParsedShape
    cells: tuple[ParsedCell, ...]
    missing_measurements: int = 0

    def __post_init__(self) -> None:
        ParsedVariableSchema(self.name, self.kind, self.shape)
        if type(self.cells) is not tuple:
            raise TypeError("Parsed variable cells must be an immutable tuple.")
        if len(self.cells) > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ValueError("Parsed variable exceeds the output column limit.")
        if self.shape == "scalar" and len(self.cells) != 1:
            raise ValueError("A scalar variable requires exactly one output cell.")
        columns: set[str] = set()
        for cell in self.cells:
            if type(cell) is not ParsedCell or cell.kind != self.kind:
                raise TypeError("Variable cells must match their declared kind.")
            if cell.column in columns:
                raise ValueError(f"Duplicate parsed column: {cell.column!r}.")
            columns.add(cell.column)
        if type(self.missing_measurements) is not int or self.missing_measurements < 0:
            raise ValueError("Missing measurement count must be a non-negative integer.")

    @property
    def schema(self) -> ParsedVariableSchema:
        """Return this variable's immutable declaration."""
        return ParsedVariableSchema(self.name, self.kind, self.shape)


@dataclass(frozen=True)
class ParsedFileResult:
    """Finalized logical values and separate metadata from one exact source file."""

    source_path: str
    variables: tuple[ParsedVariableResult, ...]
    metadata: tuple[ParsedCell, ...] = ()

    def __post_init__(self) -> None:
        _name(self.source_path, "Parsed source path")
        if type(self.variables) is not tuple or type(self.metadata) is not tuple:
            raise TypeError("Parsed variables and metadata must be immutable tuples.")
        if len(self.variables) > MAX_PARSE_VARIABLES:
            raise ValueError("Parsed file exceeds the logical variable limit.")
        if len(self.metadata) > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ValueError("Parsed file exceeds the output column limit.")
        names: set[str] = set()
        columns: set[str] = set()
        for variable in self.variables:
            if type(variable) is not ParsedVariableResult:
                raise TypeError("Parsed files require typed variable results.")
            if variable.name in names:
                raise ValueError(f"Duplicate logical variable: {variable.name!r}.")
            names.add(variable.name)
            if len(columns) + len(variable.cells) > MAX_INCREMENTAL_CACHE_COLUMNS:
                raise ValueError("Parsed file exceeds the output column limit.")
            for cell in variable.cells:
                if cell.column in columns:
                    raise ValueError(f"Duplicate parsed column: {cell.column!r}.")
                columns.add(cell.column)
        for cell in self.metadata:
            if type(cell) is not ParsedCell:
                raise TypeError("Parsed metadata requires typed cells.")
            if cell.column in columns:
                raise ValueError(f"Metadata column collision: {cell.column!r}.")
            columns.add(cell.column)
            if len(columns) > MAX_INCREMENTAL_CACHE_COLUMNS:
                raise ValueError("Parsed file exceeds the output column limit.")


@dataclass(frozen=True)
class ParsedColumn:
    """One schema column with a logical owner or an explicit metadata namespace."""

    name: str
    kind: ParsedKind
    owner: str | None

    def __post_init__(self) -> None:
        _name(self.name, "Parsed column")
        _kind(self.kind)
        if self.owner is not None:
            _name(self.owner, "Parsed column owner")


@dataclass(frozen=True)
class ParsedSchema:
    """Ordered logical declarations and explicit physical column ownership."""

    variables: tuple[ParsedVariableSchema, ...]
    columns: tuple[ParsedColumn, ...]

    def __post_init__(self) -> None:
        if type(self.variables) is not tuple or type(self.columns) is not tuple:
            raise TypeError("Parsed schema collections must be immutable tuples.")
        if len(self.variables) > MAX_PARSE_VARIABLES:
            raise ValueError("Parsed schema exceeds the logical variable limit.")
        if len(self.columns) > MAX_INCREMENTAL_CACHE_COLUMNS:
            raise ValueError("Parsed schema exceeds the output column limit.")
        variables: dict[str, ParsedVariableSchema] = {}
        for variable in self.variables:
            if type(variable) is not ParsedVariableSchema:
                raise TypeError("Parsed schema requires typed variable declarations.")
            if variable.name in variables:
                raise ValueError(f"Duplicate logical variable: {variable.name!r}.")
            variables[variable.name] = variable
        names: set[str] = set()
        counts: dict[str, int] = dict.fromkeys(variables, 0)
        for column in self.columns:
            if type(column) is not ParsedColumn:
                raise TypeError("Parsed schema requires typed columns.")
            if column.name in names:
                raise ValueError(f"Duplicate parsed column: {column.name!r}.")
            names.add(column.name)
            if column.owner is not None:
                declared_owner = variables.get(column.owner)
                if declared_owner is None or declared_owner.kind != column.kind:
                    raise ValueError("Schema column has an unknown owner or conflicting kind.")
                counts[column.owner] += 1
        if any(
            variable.shape == "scalar" and counts[name] != 1 for name, variable in variables.items()
        ):
            raise ValueError("Scalar declarations require exactly one schema column.")


@dataclass(frozen=True)
class ResolvedParsedRows:
    """Owned typed rows, provenance and missing-variable facts ready for publication."""

    schema: ParsedSchema
    rows: tuple[tuple[ParsedValue, ...], ...]
    source_paths: tuple[str, ...]
    missing_variables: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.schema) is not ParsedSchema:
            raise TypeError("Resolved parser rows require a typed schema.")
        if (
            type(self.rows) is not tuple
            or type(self.source_paths) is not tuple
            or type(self.missing_variables) is not tuple
        ):
            raise TypeError("Resolved parser rows must own immutable tuples.")
        if not self.rows or len(self.rows) > MAX_PARSE_FILES:
            raise ValueError("Resolved parser output requires a bounded non-empty row set.")
        if len(self.rows) * len(self.schema.columns) > MAX_PARSE_MATRIX_CELLS:
            raise ValueError("Parser output exceeds the matrix cell limit.")
        if self.source_paths and len(self.source_paths) != len(self.rows):
            raise ValueError("Source provenance must align with resolved rows.")
        if len(self.source_paths) != len(set(self.source_paths)):
            raise ValueError("Resolved source paths must be unique.")
        for source_path in self.source_paths:
            _name(source_path, "Resolved source path")
        for row in self.rows:
            if type(row) is not tuple or len(row) != len(self.schema.columns):
                raise ValueError("Resolved parser row width must match the schema.")
            for column, value in zip(self.schema.columns, row, strict=True):
                if type(value) is not (float if column.kind == "number" else str):
                    raise TypeError("Resolved parser cell does not match its schema kind.")
        names = {variable.name for variable in self.schema.variables}
        if len(self.missing_variables) > len(names):
            raise ValueError("Missing-variable names exceed declared variables.")
        if len(self.missing_variables) != len(set(self.missing_variables)) or any(
            type(name) is not str or name not in names for name in self.missing_variables
        ):
            raise ValueError("Missing-variable names must be distinct declared variables.")


@dataclass(frozen=True)
class ParsedOutput:
    """CSV path and schema-bound typed-content digest.

    ``sha256`` binds canonical current schema bytes and CSV bytes. It detects
    changes to either content or meaning; it is not a raw file hash or an
    authentication signature.
    """

    csv_path: str
    sha256: str
    schema: ParsedSchema

    def __post_init__(self) -> None:
        _name(self.csv_path, "Parsed CSV path")
        if (
            type(self.sha256) is not str
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
        ):
            raise ValueError("Parsed output requires a lowercase SHA-256 digest.")
        if type(self.schema) is not ParsedSchema:
            raise TypeError("Parsed output requires an explicit typed schema.")
