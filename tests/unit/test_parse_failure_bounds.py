"""Diagnostics use native bounded facts and work cannot escape its declared source plan."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from src.core.common.parse_failure import (
    _native_unicode_metadata,
    classify_parse_failure,
    detach_parse_failure,
    parse_error_text,
)
from src.core.models.parse_failure_models import ParseDataValueError, ResultAdmissionError
from src.core.models.parsed_output_models import ParsedFileResult
from src.parsing.framework import result_admission
from src.parsing.framework.result_admission import AdmittedParseWork, ResultAdmission
from src.parsing.gem5.impl.strategies import config_aware


class Forbidden:
    def __str__(self):
        pytest.fail("diagnostics invoked an arbitrary string hook")

    def __repr__(self):
        pytest.fail("diagnostics invoked an arbitrary repr hook")

    def __format__(self, spec):
        pytest.fail("diagnostics invoked an arbitrary format hook")

    def __hash__(self):
        pytest.fail("source validation invoked an arbitrary hash hook")


def _unicode_error(error_type):
    source = (
        b"PRIVATE_SOURCE" * 10_000
        if error_type is UnicodeDecodeError
        else "PRIVATE_SOURCE" * 10_000
    )
    return error_type("utf8", source, 0, 1, "native reason")


@pytest.mark.parametrize("error_type", [UnicodeEncodeError, UnicodeDecodeError])
def test_native_unicode_diagnostics_exclude_input_and_remain_useful(error_type) -> None:
    error = _unicode_error(error_type)
    assert classify_parse_failure(error) in {"encoding", "configuration"}
    diagnostic = parse_error_text(error)
    assert diagnostic == "utf8 positions 0:1: native reason"
    assert "PRIVATE_SOURCE" not in diagnostic


@pytest.mark.parametrize("error_type", [UnicodeEncodeError, UnicodeDecodeError])
@pytest.mark.parametrize("field", ["encoding", "reason"])
@pytest.mark.parametrize("value", [Forbidden(), 1 << 100_000], ids=["hook", "huge-int"])
def test_mutated_unicode_metadata_is_declined_and_formatted_without_hooks(
    error_type, field: str, value: object
) -> None:
    error = _unicode_error(error_type)
    setattr(error, field, value)
    assert classify_parse_failure(error) is None
    text = parse_error_text(error)
    assert "<Forbidden>" in text or "<int>" in text
    assert len(text) <= 1024 and "PRIVATE_SOURCE" not in text
    outer = ParseDataValueError("visible data rejection")
    outer.__cause__ = error
    fresh = detach_parse_failure(outer, "source")
    assert len(fresh.failure_facts.cause) <= 1024
    assert "PRIVATE_SOURCE" not in fresh.failure_facts.cause
    assert fresh.__cause__ is fresh.__context__ is None


@pytest.mark.parametrize("error_type", [UnicodeEncodeError, UnicodeDecodeError])
@pytest.mark.parametrize("field,value", [("start", -1), ("start", 2), ("end", -1)])
def test_invalid_native_unicode_positions_are_not_known_input_errors(
    error_type, field, value
) -> None:
    error = _unicode_error(error_type)
    setattr(error, field, value)
    assert classify_parse_failure(error) is None
    assert len(parse_error_text(error)) <= 1024


def test_huge_unicode_positions_and_ordinary_exception_ints_are_checked_before_conversion() -> None:
    huge = 1 << 100_000
    assert not _native_unicode_metadata(("utf8", "reason", huge, huge))
    assert parse_error_text(ValueError(huge)) == "<int>"


@pytest.mark.parametrize("base", [UnicodeEncodeError, UnicodeDecodeError])
def test_unicode_subclass_formatting_uses_native_fields_and_never_source_arguments(base) -> None:
    class Subtype(base):
        def __getattribute__(self, name):
            if name in {"encoding", "reason", "start", "end", "object", "args", "__class__"}:
                pytest.fail(f"diagnostics invoked a Unicode attribute hook: {name}")
            return super().__getattribute__(name)

    source = b"PRIVATE_SOURCE" * 10_000 if base is UnicodeDecodeError else "PRIVATE_SOURCE" * 10_000
    error = Subtype("utf8", source, 0, 1, "native reason")
    assert classify_parse_failure(error) is None
    assert parse_error_text(error) == "utf8 positions 0:1: native reason"


def test_arbitrary_cause_args_type_names_and_links_never_invoke_hooks() -> None:
    class HostileMeta(type):
        @property
        def __name__(cls):
            pytest.fail("diagnostics invoked a metaclass name hook")

        def __eq__(cls, other):
            pytest.fail("classification invoked a metaclass equality hook")

    class Argument(metaclass=HostileMeta):
        def __str__(self):
            pytest.fail("diagnostics invoked an argument string hook")

    class Cause(Exception, metaclass=HostileMeta):
        def __bool__(self):
            pytest.fail("diagnostics evaluated exception truthiness")

        def __getattribute__(self, name):
            if name in {"args", "__cause__", "__context__", "__traceback__", "__class__"}:
                pytest.fail(f"diagnostics invoked a cause attribute hook: {name}")
            return super().__getattribute__(name)

    cause = Cause(Argument())
    leaf = _unicode_error(UnicodeEncodeError)
    BaseException.__dict__["__cause__"].__set__(cause, leaf)
    outer = ParseDataValueError("visible data rejection")
    outer.__cause__ = cause
    assert classify_parse_failure(cause) is None
    assert parse_error_text(cause) == "<Argument>"
    fresh = detach_parse_failure(outer, "source")
    assert "Cause: <Argument>" in fresh.failure_facts.cause
    assert "UnicodeEncodeError" in fresh.failure_facts.cause
    assert "PRIVATE_SOURCE" not in fresh.failure_facts.cause


@pytest.mark.parametrize("error_type", [UnicodeEncodeError, UnicodeDecodeError])
def test_mutated_unicode_rejects_preserve_identity_through_actual_inner_owner(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error_type
) -> None:
    error = _unicode_error(error_type)
    error.reason = Forbidden()

    def fail(*args, **kwargs):
        raise error

    if error_type is UnicodeEncodeError:
        monkeypatch.setattr(result_admission, "iter_parsed_file_encoding", fail)
    else:
        path = tmp_path / "config.ini"
        path.write_text("[system]\nv=1\n")
        monkeypatch.setattr(config_aware._LiteralConfigParser, "read_string", fail)

    class Work:
        source_path = "source"

        def __call__(self):
            if error_type is UnicodeDecodeError:
                config_aware.ConfigAwareParseWork._read_config(path)
            return ParsedFileResult("source", ())

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(AdmittedParseWork(Work(), ResultAdmission(("source",))))
        assert future.exception(timeout=5) is error
    assert not hasattr(error, "failure_facts")


class SourceText(str):
    def __hash__(self):
        pytest.fail("source validation invoked a string-subclass hook")


@pytest.mark.parametrize(
    "source",
    ["x" * 10_000, "", "unplanned", Forbidden(), SourceText("planned-source")],
    ids=["long-unplanned", "empty", "unplanned", "object", "string-subclass"],
)
def test_invalid_work_source_is_rejected_before_storing_or_executing_work(source) -> None:
    calls = []

    class Work:
        source_path = source

        def __call__(self):
            calls.append(True)
            raise ParseDataValueError("nominal failure before result admission")

    wrapper = AdmittedParseWork.__new__(AdmittedParseWork)
    with pytest.raises(ResultAdmissionError, match="exact planned source ID") as caught:
        wrapper.__init__(Work(), ResultAdmission(("planned-source",)))
    assert wrapper.__dict__ == {} and calls == []
    assert len(str(caught.value)) < 100 and not hasattr(caught.value, "failure_facts")


def test_valid_work_failure_retains_its_fixed_planned_source_id() -> None:
    class Work:
        source_path = "planned-source"

        def __call__(self):
            raise ParseDataValueError("nominal data failure")

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(AdmittedParseWork(Work(), ResultAdmission(("planned-source",))))
        error = future.exception(timeout=5)
    assert type(error) is ParseDataValueError
    assert error.failure_facts.source_path == "planned-source"
    assert error.__cause__ is error.__context__ is None
