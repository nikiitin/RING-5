"""Tests for the ring5 CLI (in-process — no subprocess)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import pandas as pd
import pytest

import ring5
from ring5.cli import build_parser, main

# Shares the conftest `portfolios_dir` patching with the public-api suite —
# keep both files in one xdist group so they never interleave across workers.
pytestmark = [pytest.mark.xdist_group("ring5_portfolios"), pytest.mark.public_api]


class TestParserStructure:
    def test_subcommands_registered(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["doctor"])
        assert args.command == "doctor"

    def test_parse_requires_variable_and_output(self) -> None:
        with pytest.raises(SystemExit):
            build_parser().parse_args(["parse", "/some/dir"])

    def test_render_defaults(self) -> None:
        args = build_parser().parse_args(["render", "p", "-o", "out"])
        assert args.engine == "matplotlib"
        assert args.format is None
        assert args.no_deterministic is False

    def test_recipe_matrix_defaults(self) -> None:
        args = build_parser().parse_args(
            ["recipe-matrix", "recipe.json", "-m", "matrix.json", "-o", "out"]
        )
        assert args.command == "recipe-matrix"
        assert args.workers == 2

    def test_regression_gate_defaults(self) -> None:
        args = build_parser().parse_args(
            ["regression-gate", "main.csv", "change.csv", "-k", "benchmark", "-m", "ipc"]
        )
        assert args.command == "regression-gate"
        assert args.default_direction == "higher"
        assert args.default_threshold == 0.0
        assert args.threshold_mode == "percentage"
        assert args.format == "json"
        assert args.output is None

    def test_report_schedule_defaults(self) -> None:
        args = build_parser().parse_args(
            ["report-schedule", "recipe.json", "--report", "report.html"]
        )
        assert args.command == "report-schedule"
        assert args.parameters is None
        assert args.state is None
        assert args.stable_for == 30.0
        assert args.format == "html"
        assert args.watch is False
        assert args.interval == 5.0
        assert args.max_checks == 0


class TestDoctorCommand:
    # [test->req~ring5.api.doctor~1]
    def test_doctor_runs(self, capsys: pytest.CaptureFixture[str]) -> None:
        code = main(["doctor"])
        out = capsys.readouterr().out
        assert "dependency check" in out
        assert code in (0, 1)  # 1 only when the essential Perl binary is absent


class TestParseCommand:
    # [test->req~ring5.cli.parse~1]
    def test_parse_materializes_session_owned_output(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        run = tmp_path / "run"
        run.mkdir()
        (run / "stats.txt").write_text("simTicks 42 # ticks\n")
        output = tmp_path / "result.csv"

        assert main(["parse", str(run), "-v", "simTicks", "-o", str(output)]) == 0
        assert pd.read_csv(output).loc[0, "simTicks"] == 42
        assert "wrote" in capsys.readouterr().out

    def test_parse_accepts_repeated_variables(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        run = tmp_path / "run"
        run.mkdir()
        (run / "stats.txt").write_text("simTicks 42 # ticks\nsimInsts 17 # instructions\n")
        output = tmp_path / "result.csv"

        code = main(
            [
                "parse",
                str(run),
                "-v",
                "simTicks",
                "-v",
                "simInsts",
                "-o",
                str(output),
            ]
        )

        assert code == 0
        parsed = pd.read_csv(output)
        assert parsed.loc[0, "simTicks"] == 42
        assert parsed.loc[0, "simInsts"] == 17
        assert "wrote" in capsys.readouterr().out


class TestRenderCommand:
    # [test->req~ring5.portfolio.batch-replay~1]
    # [test->req~ring5.cli.render~1]
    def test_render_portfolio_to_pdf(self, tmp_path: Path, portfolios_dir: Path) -> None:
        import ring5

        df = pd.DataFrame({"x": ["a", "b"], "y": [1.0, 2.0]})
        with ring5.Session() as s:
            s.create_plot("bar", data=df, config={"x": "x", "y": "y"}, name="cli_test")
            s.save_portfolio("cli_probe")

        code = main(["render", "cli_probe", "-o", str(tmp_path / "figs"), "--format", "pdf"])
        assert code == 0
        written = list((tmp_path / "figs").glob("*.pdf"))
        assert len(written) == 1
        assert written[0].read_bytes()[:5] == b"%PDF-"

    def test_missing_portfolio_exits_2(
        self, tmp_path: Path, portfolios_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = main(["render", "nope", "-o", str(tmp_path / "figs")])
        assert code == 2
        assert "error:" in capsys.readouterr().err

    def test_future_portfolio_exits_2(
        self, tmp_path: Path, portfolios_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (portfolios_dir / "future.json").write_text(json.dumps({"schema_version": 99}))
        code = main(["render", "future", "-o", str(tmp_path / "figs")])
        assert code == 2
        assert "newer than this RING-5" in capsys.readouterr().err


class TestUpgradeCommand:
    # [test->req~ring5.portfolio.upgrade-protection~1]
    def test_upgrade_persists_current_schema(
        self, portfolios_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # V1 on disk: no schema_version, export_* keys
        v1 = {
            "data_csv": "x,y\na,1\n",
            "plots": [
                {
                    "id": 0,
                    "name": "p",
                    "plot_type": "bar",
                    "config": {"x": "x", "y": "y", "export_format": "png"},
                    "processed_data": "x,y\na,1\n",
                }
            ],
            "plot_counter": 1,
            "config": {},
            "parse_variables": [],
        }
        (portfolios_dir / "old.json").write_text(json.dumps(v1))

        code = main(["upgrade", "old"])
        assert code == 0

        upgraded = json.loads((portfolios_dir / "old.json").read_text())
        assert upgraded["schema_version"] == 4
        assert upgraded["environment_metadata"] is not None
        assert "export_format" not in upgraded["plots"][0]["config"]


class TestUpgradeRefusal:
    # [test->req~ring5.portfolio.upgrade-protection~1]
    def test_upgrade_refuses_incomplete_restore(
        self, portfolios_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Re-saving a partial restore would permanently destroy what could
        not be loaded — upgrade must refuse and leave the file untouched."""
        bad = {
            "data_csv": "x,y\na,1\n",
            "plots": [
                {
                    "id": 0,
                    "name": "future_plot",
                    "plot_type": "no_such_plot_type",
                    "config": {},
                    "processed_data": "x,y\na,1\n",
                }
            ],
            "plot_counter": 1,
            "config": {},
            "parse_variables": [],
        }
        target = portfolios_dir / "bad.json"
        target.write_text(json.dumps(bad))
        before = target.read_bytes()

        code = main(["upgrade", "bad"])

        assert code == 2
        assert target.read_bytes() == before, "upgrade modified a file it refused"
        err = capsys.readouterr().err
        assert "refusing to upgrade" in err
        assert "future_plot" in err


class TestRecipeMatrixCommand:
    @staticmethod
    def _write_recipe(path: Path) -> None:
        import ring5

        recipe = ring5.AnalysisRecipe(
            name="CLI matrix",
            parameters=(ring5.RecipeParameter("input_csv", "path"),),
            source=ring5.RecipeSource(kind="csv", path="{{input_csv}}"),
        )
        with ring5.Session() as session:
            path.write_bytes(session.export_analysis_recipe(recipe))

    def test_recipe_matrix_emits_ordered_versioned_summary(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # [test->req~ring5.automation.batch-matrices~1]
        first = tmp_path / "first.csv"
        second = tmp_path / "second.csv"
        pd.DataFrame({"value": [1]}).to_csv(first, index=False)
        pd.DataFrame({"value": [2, 3]}).to_csv(second, index=False)
        recipe = tmp_path / "recipe.json"
        matrix = tmp_path / "matrix.json"
        self._write_recipe(recipe)
        matrix.write_text(json.dumps({"input_csv": [str(first), str(second)]}))

        code = main(
            [
                "recipe-matrix",
                str(recipe),
                "--matrix",
                str(matrix),
                "--output-dir",
                str(tmp_path / "out"),
                "--workers",
                "2",
            ]
        )
        document = json.loads(capsys.readouterr().out)

        assert code == 0
        assert document["format"] == "ring5.analysis-recipe-matrix-result"
        assert document["schema_version"] == 1
        assert document["complete"] is True
        assert document["completed_cases"] == 2
        assert [case["rows"] for case in document["cases"]] == [1, 2]
        assert [case["status"] for case in document["cases"]] == [
            "completed",
            "completed",
        ]

    def test_recipe_matrix_returns_one_with_failed_case(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # [test->req~ring5.automation.batch-matrices~1]
        valid = tmp_path / "valid.csv"
        pd.DataFrame({"value": [1]}).to_csv(valid, index=False)
        recipe = tmp_path / "recipe.json"
        matrix = tmp_path / "matrix.json"
        self._write_recipe(recipe)
        matrix.write_text(json.dumps({"input_csv": [str(valid), str(tmp_path / "missing.csv")]}))

        code = main(
            [
                "recipe-matrix",
                str(recipe),
                "-m",
                str(matrix),
                "-o",
                str(tmp_path / "out"),
            ]
        )
        document = json.loads(capsys.readouterr().out)

        assert code == 1
        assert document["failed_cases"] == 1
        assert document["cases"][1]["status"] == "failed"
        assert document["cases"][1]["rows"] is None
        assert document["cases"][1]["columns"] == []
        assert document["cases"][1]["error"]

    @pytest.mark.parametrize("payload", [b"not json", b'{"input_csv": [NaN]}'])
    def test_recipe_matrix_rejects_invalid_json(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        payload: bytes,
    ) -> None:
        recipe = tmp_path / "recipe.json"
        matrix = tmp_path / "matrix.json"
        self._write_recipe(recipe)
        matrix.write_bytes(payload)

        assert (
            main(["recipe-matrix", str(recipe), "-m", str(matrix), "-o", str(tmp_path / "out")])
            == 2
        )
        assert "valid finite UTF-8 JSON" in capsys.readouterr().err

    def test_recipe_matrix_rejects_missing_and_oversized_inputs(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        recipe = tmp_path / "recipe.json"
        oversized = tmp_path / "oversized.json"
        self._write_recipe(recipe)
        oversized.write_bytes(b"x" * (512 * 1024 + 1))

        assert (
            main(
                [
                    "recipe-matrix",
                    str(recipe),
                    "-m",
                    str(tmp_path / "missing.json"),
                    "-o",
                    str(tmp_path / "out"),
                ]
            )
            == 2
        )
        assert "Could not read recipe matrix" in capsys.readouterr().err
        assert (
            main(
                [
                    "recipe-matrix",
                    str(recipe),
                    "-m",
                    str(oversized),
                    "-o",
                    str(tmp_path / "out"),
                ]
            )
            == 2
        )
        assert "exceeds the 512 KiB limit" in capsys.readouterr().err


class TestRegressionGateCommand:
    """CI statuses derive from the same rows emitted as JSON or JUnit."""

    @staticmethod
    def _write_inputs(
        tmp_path: Path,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
    ) -> tuple[Path, Path]:
        baseline_path = tmp_path / "baseline.csv"
        candidate_path = tmp_path / "candidate.csv"
        baseline.to_csv(baseline_path, index=False)
        candidate.to_csv(candidate_path, index=False)
        return baseline_path, candidate_path

    def test_pass_emits_versioned_json_and_returns_zero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # [test->req~ring5.automation.ci-regression-gates~1]
        baseline, candidate = self._write_inputs(
            tmp_path,
            pd.DataFrame({"benchmark": ["a", "b"], "ipc": [100.0, 100.0]}),
            pd.DataFrame({"benchmark": ["a", "b"], "ipc": [102.0, 99.0]}),
        )

        code = main(
            [
                "regression-gate",
                str(baseline),
                str(candidate),
                "--key",
                "benchmark",
                "--metric",
                "ipc",
                "--default-threshold",
                "5",
            ]
        )
        document = json.loads(capsys.readouterr().out)

        assert code == 0
        assert document["format"] == "ring5.regression-results"
        assert document["sources"] == {
            "baseline": str(baseline),
            "candidate": str(candidate),
        }
        assert document["summary"]["failures"] == 0
        assert document["summary"]["incomplete"] == 0

    def test_regression_writes_junit_and_returns_one(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # [test->req~ring5.automation.ci-regression-gates~1]
        baseline, candidate = self._write_inputs(
            tmp_path,
            pd.DataFrame({"benchmark": ["a"], "ipc": [100.0], "latency": [10.0]}),
            pd.DataFrame({"benchmark": ["a"], "ipc": [90.0], "latency": [12.0]}),
        )
        output = tmp_path / "artifacts" / "regression.xml"

        code = main(
            [
                "regression-gate",
                str(baseline),
                str(candidate),
                "-k",
                "benchmark",
                "-m",
                "ipc",
                "-m",
                "latency",
                "--direction",
                "latency=lower",
                "--threshold",
                "ipc=5",
                "--threshold",
                "latency=5",
                "--baseline-id",
                "main",
                "--candidate-id",
                "pull-request-42",
                "--format",
                "junit",
                "--output",
                str(output),
            ]
        )
        captured = capsys.readouterr()
        suite = ET.fromstring(output.read_bytes())

        assert code == 1
        assert captured.out == ""
        assert f"wrote {output}" in captured.err
        assert suite.attrib["failures"] == "2"
        assert suite.attrib["skipped"] == "0"

    def test_incomplete_evidence_takes_precedence_and_returns_three(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # [test->req~ring5.automation.ci-regression-gates~1]
        baseline, candidate = self._write_inputs(
            tmp_path,
            pd.DataFrame({"benchmark": ["shared", "old"], "ipc": [100.0, 1.0]}),
            pd.DataFrame({"benchmark": ["shared", "new"], "ipc": [80.0, 1.0]}),
        )

        code = main(
            [
                "regression-gate",
                str(baseline),
                str(candidate),
                "-k",
                "benchmark",
                "-m",
                "ipc",
                "--default-threshold",
                "5",
            ]
        )
        document = json.loads(capsys.readouterr().out)

        assert code == 3
        assert document["summary"]["failures"] == 1
        assert document["summary"]["incomplete"] == 2

    @pytest.mark.parametrize(
        ("extra", "message"),
        [
            (["--direction", "ipc"], "METRIC=VALUE"),
            (["--direction", "other=lower"], "unknown metric"),
            (
                ["--direction", "ipc=lower", "--direction", "ipc=higher"],
                "Duplicate direction",
            ),
            (["--direction", "ipc=sideways"], "Invalid metric directions"),
            (["--threshold", "ipc=lots"], "finite non-negative"),
            (["--default-threshold", "-1"], "finite non-negative"),
            (
                ["--threshold", "ipc=1", "--threshold", "ipc=2"],
                "Duplicate threshold",
            ),
        ],
    )
    def test_invalid_gate_configuration_returns_two(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        extra: list[str],
        message: str,
    ) -> None:
        baseline, candidate = self._write_inputs(
            tmp_path,
            pd.DataFrame({"benchmark": ["a"], "ipc": [1.0]}),
            pd.DataFrame({"benchmark": ["a"], "ipc": [1.0]}),
        )
        arguments = [
            "regression-gate",
            str(baseline),
            str(candidate),
            "-k",
            "benchmark",
            "-m",
            "ipc",
            *extra,
        ]

        assert main(arguments) == 2
        assert message in capsys.readouterr().err

    def test_input_and_output_execution_failures_return_two(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # [test->req~ring5.automation.ci-regression-gates~1]
        baseline, candidate = self._write_inputs(
            tmp_path,
            pd.DataFrame({"benchmark": ["a"], "ipc": [1.0]}),
            pd.DataFrame({"benchmark": ["a"], "ipc": [1.0]}),
        )

        assert (
            main(
                [
                    "regression-gate",
                    str(tmp_path / "missing.csv"),
                    str(candidate),
                    "-k",
                    "benchmark",
                    "-m",
                    "ipc",
                ]
            )
            == 2
        )
        assert "Could not load CSV" in capsys.readouterr().err

        blocked_parent = tmp_path / "not-a-directory"
        blocked_parent.write_text("blocked")
        assert (
            main(
                [
                    "regression-gate",
                    str(baseline),
                    str(candidate),
                    "-k",
                    "benchmark",
                    "-m",
                    "ipc",
                    "--output",
                    str(blocked_parent / "result.json"),
                ]
            )
            == 2
        )
        assert "Could not write regression result" in capsys.readouterr().err

        with patch("ring5.cli.sys.stdout.write", side_effect=BrokenPipeError("closed")):
            assert (
                main(
                    [
                        "regression-gate",
                        str(baseline),
                        str(candidate),
                        "-k",
                        "benchmark",
                        "-m",
                        "ipc",
                    ]
                )
                == 2
            )
        assert "standard output" in capsys.readouterr().err


class TestReportScheduleCommand:
    """Scheduled ticks and watch polling expose stable JSON outcomes."""

    @staticmethod
    def _write_recipe(path: Path) -> None:
        recipe = ring5.AnalysisRecipe(
            name="Scheduled CLI",
            parameters=(ring5.RecipeParameter("input_csv", "path"),),
            source=ring5.RecipeSource("csv", "{{input_csv}}"),
            plots=(
                ring5.RecipePlot(
                    name="IPC",
                    plot_type="bar",
                    config={"x": "benchmark", "y": "ipc"},
                ),
            ),
        )
        with ring5.Session() as session:
            path.write_bytes(session.export_analysis_recipe(recipe))

    def test_scheduler_tick_generates_then_skips_unchanged_input(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # [test->req~ring5.automation.scheduled-reporting~1]
        source = tmp_path / "input.csv"
        source.write_text("benchmark,ipc\na,1.0\n")
        recipe = tmp_path / "recipe.json"
        parameters = tmp_path / "parameters.json"
        report = tmp_path / "reports" / "nightly.html"
        state = tmp_path / "state.json"
        self._write_recipe(recipe)
        parameters.write_text(json.dumps({"input_csv": str(source)}))
        arguments = [
            "report-schedule",
            str(recipe),
            "--report",
            str(report),
            "--parameters",
            str(parameters),
            "--state",
            str(state),
            "--stable-for",
            "0",
            "--title",
            "CLI nightly",
        ]

        assert main(arguments) == 0
        generated = json.loads(capsys.readouterr().out)
        before = report.read_bytes()
        assert generated["format"] == "ring5.scheduled-report-result"
        assert generated["schema_version"] == 1
        assert generated["outcome"] == "generated"
        assert generated["generated"] is True
        assert generated["configuration_fingerprint"].startswith("sha256:")
        assert generated["source_files"] == [str(source.resolve())]
        assert b"CLI nightly" in before

        assert main(arguments) == 0
        unchanged = json.loads(capsys.readouterr().out)
        assert unchanged["outcome"] == "unchanged"
        assert unchanged["generated"] is False
        assert report.read_bytes() == before

    def test_watch_emits_ndjson_and_honors_check_limit(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # [test->req~ring5.automation.scheduled-reporting~1]
        source = tmp_path / "input.csv"
        source.write_text("benchmark,ipc\na,1.0\n")
        recipe = tmp_path / "recipe.json"
        parameters = tmp_path / "parameters.json"
        self._write_recipe(recipe)
        parameters.write_text(json.dumps({"input_csv": str(source)}))

        with patch("ring5.cli.time.sleep") as sleep:
            code = main(
                [
                    "report-schedule",
                    str(recipe),
                    "-o",
                    str(tmp_path / "report.html"),
                    "--parameters",
                    str(parameters),
                    "--stable-for",
                    "0",
                    "--watch",
                    "--interval",
                    "0.1",
                    "--max-checks",
                    "2",
                ]
            )
        results = [json.loads(line) for line in capsys.readouterr().out.splitlines()]

        assert code == 0
        assert [result["outcome"] for result in results] == ["generated", "unchanged"]
        sleep.assert_called_once_with(0.1)

    def test_first_scheduled_observation_waits_for_stability(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source = tmp_path / "input.csv"
        source.write_text("benchmark,ipc\na,1.0\n")
        recipe = tmp_path / "recipe.json"
        parameters = tmp_path / "parameters.json"
        self._write_recipe(recipe)
        parameters.write_text(json.dumps({"input_csv": str(source)}))
        report = tmp_path / "report.html"

        code = main(
            [
                "report-schedule",
                str(recipe),
                "-o",
                str(report),
                "--parameters",
                str(parameters),
            ]
        )
        result = json.loads(capsys.readouterr().out)

        assert code == 0
        assert result["outcome"] == "waiting_for_stability"
        assert not report.exists()

    def test_recipe_without_parameters_needs_no_parameter_document(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        source = tmp_path / "input.csv"
        source.write_text("benchmark,ipc\na,1.0\n")
        recipe_path = tmp_path / "recipe.json"
        recipe = ring5.AnalysisRecipe(
            name="Fixed source",
            source=ring5.RecipeSource("csv", str(source)),
            plots=(
                ring5.RecipePlot(
                    name="IPC",
                    plot_type="bar",
                    config={"x": "benchmark", "y": "ipc"},
                ),
            ),
        )
        with ring5.Session() as session:
            recipe_path.write_bytes(session.export_analysis_recipe(recipe))

        code = main(
            [
                "report-schedule",
                str(recipe_path),
                "--report",
                str(tmp_path / "report.html"),
                "--stable-for",
                "0",
            ]
        )

        assert code == 0
        assert json.loads(capsys.readouterr().out)["outcome"] == "generated"

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            (b"not json", "valid finite UTF-8 JSON"),
            (b"[]", "object with named values"),
            (b'{"": 1}', "object with named values"),
            (b'{"input_csv": NaN}', "valid finite UTF-8 JSON"),
        ],
    )
    def test_invalid_parameter_documents_return_two(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        payload: bytes,
        message: str,
    ) -> None:
        recipe = tmp_path / "recipe.json"
        parameters = tmp_path / "parameters.json"
        self._write_recipe(recipe)
        parameters.write_bytes(payload)

        assert (
            main(
                [
                    "report-schedule",
                    str(recipe),
                    "-o",
                    str(tmp_path / "report.html"),
                    "--parameters",
                    str(parameters),
                    "--stable-for",
                    "0",
                ]
            )
            == 2
        )
        assert message in capsys.readouterr().err

    @pytest.mark.parametrize(
        ("extra", "message"),
        [
            (["--max-checks", "-1"], "non-negative"),
            (["--max-checks", "1"], "requires --watch"),
            (["--watch", "--interval", "0"], "watch interval"),
            (["--watch", "--interval", "inf"], "watch interval"),
        ],
    )
    def test_invalid_watch_controls_return_two(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        extra: list[str],
        message: str,
    ) -> None:
        recipe = tmp_path / "recipe.json"
        self._write_recipe(recipe)

        assert (
            main(
                [
                    "report-schedule",
                    str(recipe),
                    "-o",
                    str(tmp_path / "report.html"),
                    *extra,
                ]
            )
            == 2
        )
        assert message in capsys.readouterr().err

    def test_missing_recipe_or_parameters_return_two(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert (
            main(
                [
                    "report-schedule",
                    str(tmp_path / "missing-recipe.json"),
                    "-o",
                    str(tmp_path / "report.html"),
                ]
            )
            == 2
        )
        assert "Could not read recipe" in capsys.readouterr().err

        recipe = tmp_path / "recipe.json"
        self._write_recipe(recipe)
        assert (
            main(
                [
                    "report-schedule",
                    str(recipe),
                    "-o",
                    str(tmp_path / "report.html"),
                    "--parameters",
                    str(tmp_path / "missing-parameters.json"),
                ]
            )
            == 2
        )
        assert "Could not read recipe" in capsys.readouterr().err
