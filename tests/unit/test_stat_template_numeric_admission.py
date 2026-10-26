"""Known template finite-check overflow remains a normal typed recipe rejection."""

import pytest

import ring5
from src.core.common.stat_config_codec import StatConfigCodec
from src.core.models.parsing_models import StatConfig

NUMERIC_OPTIONS = ["minimum", "maximum", "bucket_size", "max_range"]


def template(field):
    kind = "histogram" if field == "max_range" else "distribution"
    params = (
        {"source_type": kind, "bins": 1, "max_range": 10}
        if kind == "histogram"
        else {
            "source_type": kind,
            "minimum": 0,
            "maximum": 10,
            "bucket_size": 1,
            "zero_policy": "missing",
        }
    )
    payload = StatConfigCodec.to_payload(StatConfig("d", kind, params=params))
    payload["repeat"] = "{{repeats}}"
    return payload


def placeholder(value):
    return isinstance(value, str) and value.startswith("{{") and value.endswith("}}")


@pytest.mark.parametrize("field", NUMERIC_OPTIONS)
def test_numeric_template_overflow_rejects_at_known_conversion_and_keeps_cause(field):
    payload = template(field)
    payload["params"][field] = 10**400
    with pytest.raises(ValueError, match=f"{field} exceeds the finite numeric range") as caught:
        StatConfigCodec.validate_template_payload(payload, placeholder)
    assert type(caught.value.__cause__) is OverflowError


@pytest.mark.parametrize("field", NUMERIC_OPTIONS)
def test_public_recipe_reports_numeric_template_overflow_as_recipe_error(
    field, platformdirs_isolated
):
    payload = template(field)
    payload["params"][field] = 10**400
    recipe = ring5.AnalysisRecipe(
        "bounded",
        ring5.RecipeSource("parser", "unused", variables=(payload,), scan_limit=None),
        parameters=(ring5.RecipeParameter("repeats", "integer", default=1),),
    )
    with ring5.Session() as session:
        with pytest.raises(
            ring5.RecipeError, match=f"{field} exceeds the finite numeric range"
        ) as caught:
            session.export_analysis_recipe(recipe)
    assert type(caught.value.__cause__) is ValueError
    assert type(caught.value.__cause__.__cause__) is OverflowError


@pytest.mark.parametrize("field", NUMERIC_OPTIONS)
@pytest.mark.parametrize("value", [1, 0.5, "{{number}}"])
def test_finite_literal_and_placeholder_numeric_options_keep_current_template_contract(
    field, value
):
    payload = template(field)
    payload["params"][field] = value
    StatConfigCodec.validate_template_payload(payload, placeholder)


def test_finite_template_does_not_weaken_lossless_native_execution_admission():
    payload = template("bucket_size")
    payload["repeat"] = 1
    payload["params"]["bucket_size"] = 2**53 + 1
    StatConfigCodec.validate_template_payload(payload, placeholder)
    with pytest.raises(ValueError, match="represented exactly as a double"):
        StatConfigCodec.from_payload(payload)


@pytest.mark.parametrize("bins", [1, 2])
def test_runnable_histogram_numeric_overflow_rejects_before_template_or_worker(
    tmp_path, monkeypatch, bins
):
    from src.parsing.gem5.impl.gem5_parser import Gem5Parser
    from src.parsing.gem5.impl.strategies.simple import SimpleStatsStrategy
    from src.parsing.framework.work_pool import WorkPool

    (tmp_path / "stats.txt").write_text("h::0-0 1\n")
    config = StatConfig(
        "h", "histogram", params={"source_type": "histogram", "bins": bins, "max_range": 10**400}
    )

    def no_allocation(*args, **kwargs):
        raise AssertionError(
            "Invalid numeric geometry must reject before template/worker allocation."
        )

    monkeypatch.setattr(SimpleStatsStrategy, "_map_variables", no_allocation)
    monkeypatch.setattr(WorkPool, "get_instance", no_allocation)
    with pytest.raises(ValueError, match="max_range exceeds the finite numeric range") as caught:
        Gem5Parser.submit_parse_async(str(tmp_path), "stats.txt", [config], str(tmp_path / "out"))
    assert type(caught.value.__cause__) is OverflowError


@pytest.mark.parametrize("bins", [1, 2])
def test_public_parse_reports_histogram_finite_overflow_as_parse_error(
    tmp_path, monkeypatch, bins, platformdirs_isolated
):
    from unittest.mock import Mock
    from concurrent.futures import Future

    config = StatConfig(
        "h", "histogram", params={"source_type": "histogram", "bins": bins, "max_range": 10**400}
    )
    with ring5.Session() as session:
        scan = Future()
        scan.set_result(
            ring5.ScanFileResult(
                str(tmp_path / "stats.txt"),
                [
                    ring5.ScannedVariable(
                        "h",
                        "histogram",
                        entries=["0-0"],
                        source_evidence=ring5.ResolvedSourceKind("histogram", "backend_metadata"),
                        instances=(ring5.SourceInstance("h", ()),),
                    ),
                ],
            )
        )
        monkeypatch.setattr(session.api, "submit_scan_async", Mock(return_value=[scan]))
        submit = Mock(side_effect=AssertionError("Invalid geometry reached submission."))
        monkeypatch.setattr(session.api, "submit_parse_async", submit)
        with pytest.raises(
            ring5.ParseError, match="max_range exceeds the finite numeric range"
        ) as caught:
            session.parse(str(tmp_path), [config])
        submit.assert_not_called()
    assert type(caught.value.__cause__) is ValueError
    assert type(caught.value.__cause__.__cause__) is OverflowError


@pytest.mark.parametrize("statistics_only", [False, True])
def test_finite_unused_histogram_geometry_preserves_selection_bypasses(
    monkeypatch, statistics_only
):
    from src.parsing.gem5.impl.source_bindings import resolve_sources
    from src.parsing.gem5.types.type_mapper import TypeMapper
    from src.parsing.gem5.types.histogram import Histogram

    params = {"source_type": "histogram", "bins": 10**9, "max_range": 10**200}
    params.update({"statistics": ["mean"]} if statistics_only else {"entries": ["0-0"]})
    config = StatConfig("h", "histogram", params=params, statistics_only=statistics_only)
    configured = StatConfigCodec.validate(config)
    assert configured.params["max_range"] == 10**200

    def no_labels(*args, **kwargs):
        raise AssertionError("Unused rebin geometry must not allocate labels.")

    monkeypatch.setattr(Histogram, "_bin_label", no_labels)
    plan = resolve_sources([configured], None, file_count=1, metadata_columns=())
    accumulator = TypeMapper.create_stat(plan.accumulators[0])
    assert accumulator.entries == (["mean"] if statistics_only else ["0-0"])
