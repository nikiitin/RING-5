"""Execution selection preserves complete evidence while bounding numeric matching."""

from __future__ import annotations

from copy import deepcopy
from typing import cast

import pytest

from src.core.common import source_matching
from src.core.common.safe_regex import SafeRegexError
from src.core.models.data_models import ScannedVariableDict
from src.core.models.parsing_models import ScannedVariable, SourceInstance, StatConfig
from src.core.models.source_evidence import ResolvedSourceKind


def _record(name: str, *instances: SourceInstance) -> ScannedVariableDict:
    return ScannedVariable(
        name,
        "scalar",
        source_evidence=ResolvedSourceKind("scalar", "backend_metadata"),
        instances=instances or (SourceInstance(name, ()),),
    ).to_dict()


def _literal(name: str, source: str | None = None) -> StatConfig:
    return StatConfig(name, "scalar", source_name=source, params={"source_type": "scalar"})


def _pattern(name: str) -> StatConfig:
    return StatConfig(name, "scalar", is_regex=True, params={"source_type": "scalar"})


def test_literal_alias_union_retains_original_group_and_owned_evidence() -> None:
    grouped = _record(
        r"rack\d+.cpu\d+.ipc",
        SourceInstance("rack2.cpu03.ipc", ("2", "03")),
        SourceInstance("rack2.cpu4.ipc", ("2", "4")),
    )
    catalog = [_record("unrelated"), grouped]
    before = deepcopy(catalog)
    configs = [_literal("first", "rack2.cpu03.ipc"), _literal("second", "rack2.cpu4.ipc")]
    projected = source_matching.request_scanned_variables(configs, catalog)
    assert projected == [grouped]
    assert catalog == before
    projected[0]["instances"][0]["indices"].append("9")
    projected[0]["entries"].append("changed")
    assert catalog == before
    assert configs[0].source_name == "rack2.cpu03.ipc"


def test_pattern_retains_all_matching_records_and_original_coordinates() -> None:
    first = _record(r"rack\d+.cpu\d+.ipc", SourceInstance("rack2.cpu03.ipc", ("2", "03")))
    second = _record("rack2.cpu4.ipc")
    values = [first, _record("other"), second]
    config = StatConfig(
        "chosen",
        "scalar",
        source_name=r"rack2.cpu\d+.ipc",
        is_regex=True,
        params={"source_type": "scalar", "selected_sources": ["rack2.cpu4.ipc"]},
    )
    before = deepcopy(values)
    assert source_matching.request_scanned_variables([config], values) == [first, second]
    assert source_matching.matching_source_instances(r"rack2.cpu\d+.ipc", values) == [
        {"source_name": "rack2.cpu03.ipc", "indices": ["03"]},
        {"source_name": "rack2.cpu4.ipc", "indices": ["4"]},
    ]
    assert first["instances"][0]["indices"] == ["2", "03"]
    assert config.params["selected_sources"] == ["rack2.cpu4.ipc"]
    assert values == before


def test_literal_matching_never_interprets_backend_punctuation_as_regex() -> None:
    name = "device[0]+.cycles"
    values = [_record(name), _record("device0Xcycles")]
    assert source_matching.request_scanned_variables([_literal("alias", name)], values) == [
        values[0]
    ]
    assert source_matching.request_scanned_variables([_literal("absent")], values) == []


@pytest.mark.parametrize("defect", ["malformed", "duplicate"])
def test_unrelated_invalid_metadata_is_not_hidden_by_projection(defect: str) -> None:
    needed = _record("needed")
    unrelated = _record("other")
    if defect == "malformed":
        malformed: dict[str, object] = dict(unrelated)
        malformed["retired"] = True
        values = [needed, cast(ScannedVariableDict, malformed)]
    else:
        values = [needed, unrelated, deepcopy(unrelated)]
    before = deepcopy(values)
    with pytest.raises(ValueError, match="current fields|more than once"):
        source_matching.request_scanned_variables([_literal("needed")], values)
    assert values == before


def test_literal_request_does_not_acquire_numeric_candidate_or_deadline_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = [
        _record("needed"),
        _record(
            r"cpu\d+.ipc", SourceInstance("cpu0.ipc", ("0",)), SourceInstance("cpu1.ipc", ("1",))
        ),
    ]
    monkeypatch.setattr(source_matching, "MAX_REGEX_CANDIDATES", 1)
    assert source_matching.request_scanned_variables([_literal("needed")], values) == [values[0]]
    with pytest.raises(ValueError, match="candidate limit"):
        source_matching.request_scanned_variables([_pattern(r"cpu\d+.ipc")], values)
    monkeypatch.setattr(source_matching, "MAX_REGEX_CANDIDATES", 10)
    monkeypatch.setattr(source_matching, "MAX_REGEX_EXPANSION_SECONDS", -1)
    assert source_matching.request_scanned_variables([_literal("needed")], values) == [values[0]]
    with pytest.raises(SafeRegexError, match="deadline"):
        source_matching.request_scanned_variables([_pattern(r"cpu\d+.ipc")], values)


def test_patterns_share_one_attempt_budget_but_repeated_aliases_do_not_rematch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values = [_record("cpu0.ipc"), _record("cpu1.ipc")]
    config = _pattern(r"cpu\d+.ipc")
    monkeypatch.setattr(source_matching, "MAX_REGEX_MATCH_ATTEMPTS", 3)
    assert (
        source_matching.request_scanned_variables(
            [config, deepcopy(config), _pattern(r"cpu\d+\.ipc")], values
        )
        == values
    )
    with pytest.raises(SafeRegexError, match="match limit"):
        source_matching.request_scanned_variables([config, _pattern(r"cpu\d+.cycles")], values)


def test_numeric_projection_rejects_unsupported_grammar_and_preserves_no_match() -> None:
    values = [_record("cpu0.ipc")]
    with pytest.raises(SafeRegexError):
        source_matching.request_scanned_variables([_pattern(r"cpu.*")], values)
    assert source_matching.request_scanned_variables([_pattern(r"cache\d+.ipc")], values) == []
