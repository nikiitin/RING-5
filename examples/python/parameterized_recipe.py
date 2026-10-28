"""Run and export a complete parameterized recipe and a serial threshold matrix."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import ring5

DEFAULT_INPUT = Path(__file__).resolve().parents[1] / "data" / "repeated_runs.csv"


def build_recipe() -> ring5.AnalysisRecipe:
    """Describe a filtered IPC/energy scatter plot without embedding measurements."""
    return ring5.AnalysisRecipe(
        name="Synthetic efficiency observations",
        description="Inspect individual observations above an explicit IPC threshold.",
        source=ring5.RecipeSource(kind="csv", path="{{input_csv}}"),
        parameters=(
            ring5.RecipeParameter("input_csv", "path"),
            ring5.RecipeParameter("minimum", "number", default=0.0),
            ring5.RecipeParameter("output_dir", "path", default="recipe-output"),
        ),
        transformations=(
            {
                "type": "conditionSelector",
                "column": "ipc",
                "mode": "greater_than",
                "threshold": "{{minimum}}",
            },
        ),
        plots=(
            ring5.RecipePlot(
                name="IPC and energy",
                plot_type="scatter",
                config={
                    "x": "energy_j",
                    "y": "ipc",
                    "color": "configuration",
                    "title": "Synthetic individual observations",
                    "xlabel": "Energy (J)",
                    "ylabel": "IPC (higher is better)",
                },
            ),
        ),
        exports=(
            ring5.RecipeExport(
                plot="IPC and energy",
                path="{{output_dir}}/efficiency.html",
                engine="plotly",
                format="html",
            ),
        ),
    )


def run(input_csv: Path, output_dir: Path) -> dict:
    """Execute one recipe and both matrix cases beneath the requested directory."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("RING5_DATA_DIR", str(output_dir / "workspace"))
    recipe = build_recipe()
    with ring5.Session() as session:
        payload = session.export_analysis_recipe(recipe)
        (output_dir / "analysis.ring5-recipe.json").write_bytes(payload)
        decoded = session.decode_analysis_recipe(payload)
        result = session.run_analysis_recipe(
            decoded,
            {
                "input_csv": str(input_csv.resolve()),
                "output_dir": str(output_dir / "single"),
            },
        )
        (output_dir / "reproduce.py").write_bytes(session.export_analysis_recipe_script(decoded))
        (output_dir / "reproduce.ipynb").write_bytes(
            session.export_analysis_recipe_notebook(decoded)
        )
        batch = session.run_analysis_recipe_matrix(
            decoded,
            {"input_csv": [str(input_csv.resolve())], "minimum": [0.0, 1.5]},
            output_directory=str(output_dir / "matrix"),
            max_workers=1,
        )
    if not batch.complete:
        errors = "; ".join(
            case.error or "Incomplete case" for case in batch.cases if not case.successful
        )
        raise ring5.RecipeError(errors)
    summary = {
        "recipe": result.recipe_name,
        "rows": result.rows,
        "exports": list(result.exported_paths),
        "matrix": [
            {
                "case_id": case.case_id,
                "parameters": dict(case.parameter_values),
                "rows": case.result.rows,
                "exports": list(case.result.exported_paths),
            }
            for case in batch.cases
            if case.result is not None
        ],
    }
    (output_dir / "analysis.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    """Run the example with caller-selected paths."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-dir", type=Path, default=Path("example-output/recipe"))
    args = parser.parse_args()
    try:
        summary = run(args.input, args.output_dir)
    except (ring5.Ring5Error, OSError) as exc:
        print(f"Recipe failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
