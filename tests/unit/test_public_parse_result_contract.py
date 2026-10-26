"""Public result handles reject ambiguous types and own immutable transport facts."""

from concurrent.futures import Future
from dataclasses import FrozenInstanceError
from unittest.mock import MagicMock

import pytest

import ring5
from tests.helpers.parsed_values import numeric_output, parser_context

pytestmark = pytest.mark.public_api


def test_parse_result_requires_explicit_current_output_and_source(tmp_path):
    output = numeric_output(tmp_path / "results.csv", {"x": 1.25})
    context = parser_context()
    with pytest.raises(TypeError, match="typed output"):
        ring5.ParseResult("filename.csv", context, parsed_files=1)
    with pytest.raises(TypeError, match="source context"):
        ring5.ParseResult(output, object(), parsed_files=1)
    result = ring5.ParseResult(output, context, parsed_files=1)
    assert result.csv_path == output.csv_path
    assert result.missing_stats == ()
    with pytest.raises(FrozenInstanceError):
        result.source_context = parser_context(stats_path="other")


@pytest.mark.parametrize("missing", [["x"], (1,)])
def test_missing_stat_names_require_an_immutable_text_tuple(tmp_path, missing):
    with pytest.raises(TypeError, match="immutable tuple"):
        ring5.ParseResult(
            numeric_output(tmp_path / "results.csv", {"x": float("nan")}),
            parser_context(),
            missing,
            parsed_files=1,
        )


@pytest.mark.parametrize("field", ["parsed_files", "reused_files", "removed_files"])
@pytest.mark.parametrize("value", [True, -1])
def test_public_parse_counts_cannot_be_coerced_or_negative(tmp_path, field, value):
    fields = {"parsed_files": 1, field: value}
    with pytest.raises(ValueError, match="non-negative integers"):
        ring5.ParseResult(
            numeric_output(tmp_path / "results.csv", {"x": 1.25}), parser_context(), **fields
        )


def test_invalid_strict_policy_rejects_before_waiting_or_publishing():
    pending: Future[ring5.ParsedFileResult] = Future()
    api = MagicMock()
    batch = ring5.ParseBatchResult((pending,), ("x",), ("source",), "output", "simple")
    job = ring5.ParseJob(api, batch, parser_context())
    with pytest.raises(ring5.ParseError, match="boolean"):
        job.finalize(strict="false")
    api.finalize_parsing.assert_not_called()
    assert not pending.done()
    job.cancel()
    assert pending.cancelled()
