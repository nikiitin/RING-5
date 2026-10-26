"""Fresh-checkout mock-data generation uses the real current parser contract."""

from pathlib import Path

import pandas as pd
import pytest

from scripts import generate_mock_fixtures as generator

pytestmark = pytest.mark.xdist_group("perl_pool")


def test_missing_fixture_is_generated_from_isolated_real_stats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stats_root = tmp_path / "stats"
    output = tmp_path / "mock" / "configurer_test_case01.csv"
    for seed, ticks, misses in [(0, 10.5, 2), (1, 14.5, 4)]:
        path = stats_root / str(seed) / "stats.txt"
        path.parent.mkdir(parents=True)
        path.write_text(
            "config_description_abbrev=baseline\nbenchmark_name=case\n"
            f"simTicks {ticks}\nsystem.cpu0.branchMispredicts {misses}\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "STATS_ROOT", stats_root)
    monkeypatch.setattr(generator, "OUTPUT_CSV", output)
    assert not output.exists()

    assert generator.main() == 0

    result = pd.read_csv(output, sep=r"\s+")
    assert list(result.columns) == generator.FINAL_ORDER
    assert result.to_dict("records") == [
        {
            "benchmark_name": "case",
            "config_description_abbrev": "baseline",
            "simTicks": 12.5,
            "branchMispredicts": 3.0,
        }
    ]
    before = output.read_bytes()
    assert generator.main() == 0
    assert output.read_bytes() == before


def test_parser_declares_exact_fixture_columns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stats_root = tmp_path / "stats"
    stats_root.mkdir()
    (stats_root / "stats.txt").write_text(
        "config_description_abbrev=baseline\nbenchmark_name=case\n"
        "simTicks 10.5\nsystem.cpu0.branchMispredicts 2\n"
        "system.cpu0.branchMispredicts.extra 999\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(generator, "STATS_ROOT", stats_root)

    result = generator._parse_to_dataframe()

    assert list(result.columns) == list(generator.COLUMN_SOURCES)
    assert result.to_dict("records") == [
        {
            "config_description_abbrev": "baseline",
            "benchmark_name": "case",
            "simTicks": 10.5,
            "branchMispredicts": 2.0,
        }
    ]


@pytest.mark.parametrize("metric", ["inf", "-inf"])
@pytest.mark.parametrize("existing", [False, True])
def test_infinite_metrics_do_not_publish_or_replace_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, metric: str, existing: bool
) -> None:
    stats_root = tmp_path / "stats"
    output = tmp_path / "fixture.csv"
    for seed, ticks in [(0, "10.5"), (1, metric)]:
        path = stats_root / str(seed) / "stats.txt"
        path.parent.mkdir(parents=True)
        path.write_text(
            "config_description_abbrev=baseline\nbenchmark_name=case\n"
            f"simTicks {ticks}\nsystem.cpu0.branchMispredicts 2\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "STATS_ROOT", stats_root)
    monkeypatch.setattr(generator, "OUTPUT_CSV", output)
    if existing:
        output.write_bytes(b"previous fixture\n")

    with pytest.raises(SystemExit, match="complete runs with finite metrics"):
        generator.generate()

    if existing:
        assert output.read_bytes() == b"previous fixture\n"
    else:
        assert not output.exists()


@pytest.mark.parametrize("metric", ["nan", "1e308"])
def test_seed_means_report_missing_runs_and_preserve_large_finite_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    metric: str,
) -> None:
    stats_root = tmp_path / "stats"
    output = tmp_path / "fixture.csv"
    for seed, ticks in [(0, "1e308"), (1, metric)]:
        path = stats_root / str(seed) / "stats.txt"
        path.parent.mkdir(parents=True)
        path.write_text(
            "config_description_abbrev=baseline\nbenchmark_name=case\n"
            f"simTicks {ticks}\nsystem.cpu0.branchMispredicts 2\n",
            encoding="utf-8",
        )
    monkeypatch.setattr(generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(generator, "STATS_ROOT", stats_root)
    monkeypatch.setattr(generator, "OUTPUT_CSV", output)

    generator.generate()

    result = pd.read_csv(output, sep=r"\s+")
    assert result["simTicks"].tolist() == [1e308]
    assert result["branchMispredicts"].tolist() == [2.0]
    if metric == "nan":
        assert "Excluding 1 incomplete run(s)" in caplog.text
    else:
        assert "Excluding" not in caplog.text
