"""Real Perl source routing preserves scientific observation and alias semantics."""

from pathlib import Path

import pandas as pd
import pytest

from src.core.models.parsing_models import StatConfig
from src.parsing.gem5.impl.gem5_parser import Gem5Parser

pytestmark = pytest.mark.xdist_group("perl_pool")


def _parse(root: Path, texts: list[str], configs: list[StatConfig]) -> pd.DataFrame:
    for number, text in enumerate(texts):
        source = root / f"run-{number}" / "stats.txt"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(text, encoding="utf-8")
    scan = Gem5Parser.aggregate_scan_results(
        [
            future.result(timeout=30)
            for future in Gem5Parser.submit_scan_async(str(root), "stats.txt")
        ]
    )
    batch = Gem5Parser.submit_parse_async(
        str(root), "stats.txt", configs, str(root / "out"), scanned_vars=scan.variables
    )
    results = [future.result(timeout=30) for future in batch.futures]
    path = Gem5Parser.finalize_parsing(str(root / "out"), results, var_names=batch.var_names)
    assert path is not None
    return pd.read_csv(path)


_SCALARS = "cpu0.ipc 2\ncpu1.ipc 4\ncpu0.ipc 6\ncpu1.ipc 8\n"


@pytest.mark.parametrize(
    "output_type,expected", [("vector", {"IPC..0": 4.0, "IPC..1": 6.0}), ("scalar", {"IPC": 5.0})]
)
def test_scalar_patterns_preserve_independent_entries_or_spatial_temporal_mean(
    tmp_path, output_type, expected
) -> None:
    frame = _parse(
        tmp_path,
        [_SCALARS],
        [
            StatConfig(
                "IPC",
                output_type,
                repeat=2,
                source_name=r"cpu\d+.ipc",
                params={"source_type": "scalar"},
            )
        ],
    )
    assert frame.to_dict("records") == [expected]


def test_selected_concrete_source_does_not_expand_a_numeric_id_or_parse_other_instances(
    tmp_path,
) -> None:
    frame = _parse(
        tmp_path,
        [_SCALARS],
        [
            StatConfig(
                "IPC",
                "vector",
                repeat=2,
                source_name=r"cpu\d+.ipc",
                params={"source_type": "scalar", "selected_sources": ["cpu1.ipc"]},
            )
        ],
    )
    assert frame.to_dict("records") == [{"IPC..1": 6.0}]


def test_keep_indices_preserves_current_concrete_output_names(tmp_path) -> None:
    frame = _parse(
        tmp_path,
        [_SCALARS],
        [
            StatConfig(
                "IPC",
                "vector",
                repeat=2,
                source_name=r"cpu\d+.ipc",
                keep_indices=True,
                params={"source_type": "scalar", "selected_sources": ["cpu1.ipc"]},
            )
        ],
    )
    assert frame.to_dict("records") == [{"cpu1.ipc": 6.0}]


@pytest.mark.parametrize("dump_markers", [False, True])
def test_true_vector_patterns_keep_spatial_samples_separate_with_and_without_dump_markers(
    tmp_path,
    dump_markers,
) -> None:
    body = "cpu0.v::a 2\ncpu1.v::a 4\ncpu0.v::a 6\ncpu1.v::a 8\n"
    if dump_markers:
        body = (
            "---------- Begin Simulation Statistics ----------\n"
            "cpu0.v::a 2\ncpu1.v::a 4\n"
            "---------- End Simulation Statistics ----------\n"
            "---------- Begin Simulation Statistics : second ----------\n"
            "cpu0.v::a 6\ncpu1.v::a 8\n"
            "---------- End Simulation Statistics ----------\n"
        )
    frame = _parse(
        tmp_path,
        [body],
        [
            StatConfig(
                "V",
                "vector",
                repeat=2,
                source_name=r"cpu\d+.v",
                params={"source_type": "vector", "entries": ["a"]},
            )
        ],
    )
    assert frame.to_dict("records") == [{"V..a": 5.0}]


def test_missing_scalar_instance_observation_remains_nan(tmp_path) -> None:
    frame = _parse(
        tmp_path,
        ["cpu0.ipc 2\ncpu1.ipc 4\ncpu0.ipc 6\n"],
        [
            StatConfig(
                "IPC",
                "vector",
                repeat=2,
                source_name=r"cpu\d+.ipc",
                params={"source_type": "scalar"},
            )
        ],
    )
    assert frame["IPC..0"].tolist() == [4.0]
    assert frame["IPC..1"].isna().all()


def test_histogram_missing_expected_source_is_nan_and_complete_source_mean_is_preserved(
    tmp_path,
) -> None:
    frame = _parse(
        tmp_path,
        ["cpu0.h::0-9 6 100% 100%\n", "cpu0.h::0-9 6 100% 100%\ncpu1.h::0-9 8 100% 100%\n"],
        [
            StatConfig(
                "H",
                "histogram",
                source_name=r"cpu\d+.h",
                params={"source_type": "histogram", "bins": 2, "max_range": 10},
            )
        ],
    )
    assert frame.iloc[0].isna().all()
    assert frame.iloc[1].to_dict() == {"H..0-9": 7.0, "H..10+": 0.0}


def test_one_source_can_feed_multiple_real_output_aliases_without_shared_accumulators(
    tmp_path,
) -> None:
    frame = _parse(
        tmp_path,
        ["source 2\nsource 4\n"],
        [
            StatConfig("source", "scalar", repeat=2, params={"source_type": "scalar"}),
            StatConfig(
                "Alias", "scalar", source_name="source", repeat=2, params={"source_type": "scalar"}
            ),
        ],
    )
    assert frame.to_dict("records") == [{"source": 3.0, "Alias": 3.0}]


def test_portfolio_and_recipe_round_trip_keep_current_source_bindings(tmp_path, portfolios_dir):
    import json

    import ring5

    (tmp_path / "stats.txt").write_text(_SCALARS, encoding="utf-8")
    with ring5.Session() as session:
        scan = session.scan(str(tmp_path))
        session.api.state_manager.set_scanned_variables(
            [value.to_dict() for value in scan.variables]
        )
        draft = session.api.draft_from_scanned_variable(scan.variables[0].to_dict())
        draft.update(name="IPC", source_name=r"cpu\d+.ipc", repeat=2)
        draft["params"]["selected_sources"] = ["cpu1.ipc"]
        session.api.state_manager.set_parse_variables([draft])
        session.api.state_manager.set_stats_path(str(tmp_path))
        session.api.state_manager.set_use_parser(True)
        session.save_portfolio("source-bindings")
        payload = json.loads((portfolios_dir / "source-bindings.json").read_text())
        assert payload["schema_version"] == 7
        assert payload["scanned_variables"][0]["source_type"] == "scalar"
        assert payload["scanned_variables"][0]["instances"][1] == {
            "source_name": "cpu1.ipc",
            "indices": ["1"],
        }
        assert session.load_portfolio("source-bindings").complete
        restored = session.api.state_manager.get_parse_variables()[0]
        assert restored["params"] == {"source_type": "scalar", "selected_sources": ["cpu1.ipc"]}
        recipe = session.capture_analysis_recipe("Source bindings")
        exported = session.export_analysis_recipe(recipe)
        assert json.loads(exported)["schema_version"] == 3
        result = session.parse(
            str(tmp_path), variables=session.api.compile_parse_variables([restored])
        )
        assert pd.read_csv(result.csv_path).to_dict("records") == [{"IPC..1": 6.0}]


@pytest.mark.parametrize("declared_kind", ["histogram", "distribution"])
def test_manual_requests_cannot_misdeclare_the_actual_entry_source_kind(tmp_path, declared_kind):
    source = tmp_path / "stats.txt"
    source.write_text("v::0 3\nv::1 7\n", encoding="utf-8")
    config = StatConfig(
        "out",
        "vector",
        source_name="v",
        params={"source_type": declared_kind, "entries": ["0-0", "1-1"]},
    )
    batch = Gem5Parser.submit_parse_async(
        str(tmp_path), "stats.txt", [config], str(tmp_path / "out")
    )
    with pytest.raises(RuntimeError, match="Raw source kind mismatch"):
        [future.result(timeout=30) for future in batch.futures]
    assert not (tmp_path / "out" / "result.csv").exists()


def test_actual_vector_source_can_be_explicitly_represented_as_histogram(tmp_path):
    frame = _parse(
        tmp_path,
        ["v::0 3\nv::1 7\n"],
        [StatConfig("out", "histogram", source_name="v", params={"source_type": "vector"})],
    )
    assert frame.to_dict("records") == [{"out..0-0": 3.0, "out..1-1": 7.0}]
