"""Execute the distributed documentation examples through their public entry points."""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "python"


def _environment(output_dir: Path) -> dict[str, str]:
    """Keep example persistence, native threads, and imports isolated."""
    return {
        **os.environ,
        "PYTHONPATH": str(ROOT),
        "RING5_DATA_DIR": str(output_dir / "application-data"),
        "MPLBACKEND": "Agg",
        "BROWSER_PATH": str(output_dir / "no-browser"),
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }


def _run_example(name: str, output_dir: Path, *arguments: str) -> dict:
    """Execute the actual user script, retaining diagnostic output on failure."""
    completed = subprocess.run(  # noqa: S603
        [sys.executable, str(EXAMPLES / name), "--output-dir", str(output_dir), *arguments],
        cwd=ROOT,
        env=_environment(output_dir),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    summary = json.loads(completed.stdout)
    assert summary == json.loads((output_dir / "analysis.json").read_text(encoding="utf-8"))
    return summary


def test_comparison_example_preserves_means_uncertainty_and_portfolio(tmp_path: Path) -> None:
    """Verify numerical meaning, both real exports, and restore in another process."""
    output = tmp_path / "comparison"
    summary = _run_example("compare_configurations.py", output)
    assert summary["raw_rows"] == 12
    assert summary["reduced_rows"] == 4
    rows = {(row["benchmark"], row["configuration"]): row for row in summary["normalized_rows"]}
    expected = {
        ("mcf", "baseline"): (1.0, 0.1),
        ("mcf", "candidate"): (1.2, 0.12),
        ("xalancbmk", "baseline"): (1.0, 0.1),
        ("xalancbmk", "candidate"): (1.5, 0.15),
    }
    assert rows.keys() == expected.keys()
    for key, (mean, standard_deviation) in expected.items():
        assert rows[key]["ipc"] == pytest.approx(mean)
        assert rows[key]["ipc.sd"] == pytest.approx(standard_deviation)
    with (output / "reduced.csv").open(encoding="utf-8", newline="") as stream:
        reduced = {
            (row["benchmark"], row["configuration"]): float(row["ipc"])
            for row in csv.DictReader(stream)
        }
    assert reduced == pytest.approx(
        {
            ("mcf", "baseline"): 2.0,
            ("mcf", "candidate"): 2.4,
            ("xalancbmk", "baseline"): 1.0,
            ("xalancbmk", "candidate"): 1.5,
        }
    )
    assert (output / "ipc-normalized.pdf").read_bytes().startswith(b"%PDF-")
    html = (output / "ipc-normalized.html").read_text(encoding="utf-8")
    assert "Plotly.newPlot" in html and "Synthetic repeated-run comparison" in html
    assert len(summary["replayed"]) == 1
    assert Path(summary["replayed"][0]).read_bytes().startswith(b"%PDF-")
    restored = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            (
                "import json, ring5; "
                "session = ring5.Session(); "
                "report = session.load_portfolio('Documentation IPC comparison'); "
                "print(json.dumps({'complete': report.complete, 'data': report.data_restored, "
                "'plots': [plot.name for plot in session.plots]})); session.close()"
            ),
        ],
        cwd=ROOT,
        env=_environment(output),
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    assert json.loads(restored.stdout) == {
        "complete": True,
        "data": True,
        "plots": ["IPC relative to baseline"],
    }


def test_recipe_example_replays_changed_input_through_generated_script(tmp_path: Path) -> None:
    """Verify the recipe matrix and execute its generated public-only script."""
    output = tmp_path / "recipe"
    summary = _run_example("parameterized_recipe.py", output)
    assert summary["rows"] == 12
    assert [case["rows"] for case in summary["matrix"]] == [12, 7]
    assert [case["parameters"]["minimum"] for case in summary["matrix"]] == [0.0, 1.5]
    paths = summary["exports"] + [path for case in summary["matrix"] for path in case["exports"]]
    assert len(paths) == len(set(paths)) == 3
    for path in paths:
        assert Path(path).is_relative_to(output)
        assert "Plotly.newPlot" in Path(path).read_text(encoding="utf-8")
    payload = json.loads((output / "analysis.ring5-recipe.json").read_text(encoding="utf-8"))
    assert payload["schema_version"] == 8
    notebook = json.loads((output / "reproduce.ipynb").read_text(encoding="utf-8"))
    assert notebook["nbformat"] == 4
    changed_input = tmp_path / "changed.csv"
    changed_input.write_text(
        "benchmark,configuration,seed,ipc,energy_j\nnew,candidate,0,4.0,3.0\n", encoding="utf-8"
    )
    generated = subprocess.run(  # noqa: S603
        [
            sys.executable,
            str(output / "reproduce.py"),
            "--input-csv",
            str(changed_input),
            "--output-dir",
            str(output / "changed"),
            "--minimum",
            "2.0",
        ],
        cwd=ROOT,
        env=_environment(output),
        capture_output=True,
        text=True,
        timeout=90,
        check=True,
    )
    result = json.loads(generated.stdout)
    assert result["rows"] == 1
    assert result["parameters"]["input_csv"] == str(changed_input)
    assert result["parameters"]["minimum"] == 2.0
    assert len(result["exports"]) == 1
    assert "Plotly.newPlot" in Path(result["exports"][0]).read_text(encoding="utf-8")


@pytest.mark.parametrize("strategy", ["simple", "config_aware"])
def test_parser_example_uses_actual_synthetic_statistics(tmp_path: Path, strategy: str) -> None:
    """Use real Perl against tiny declared fixtures, without external datasets."""
    output = tmp_path / strategy
    summary = _run_example("parse_gem5.py", output, "--strategy", strategy)
    assert summary["parsed_files"] == 2
    assert summary["missing_stats"] == []
    assert len(summary["rows"]) == 2
    assert sorted(row["simTicks"] for row in summary["rows"]) == [800000, 1000000]
    assert sorted(row["system.cpu.ipc"] for row in summary["rows"]) == [2.0, 2.4]
    assert (output / "measurements.csv").is_file()
    assert Path(summary["parser_csv"]).is_file()
    if strategy == "config_aware":
        assert {"sim_path", "config_json"} <= set(summary["columns"])
        for row in summary["rows"]:
            assert json.loads(row["config_json"])["system.cpu"]["type"] == "TimingSimpleCPU"
