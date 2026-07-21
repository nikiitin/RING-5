"""Deterministic public-API Python and notebook exports for analysis recipes."""

from __future__ import annotations

import json
from typing import Any

from src.core.models import AnalysisRecipe, RecipeParameter
from src.core.services.data_services.analysis_recipe_service import AnalysisRecipeService


class AnalysisRecipeAutomationService:
    """Render validated recipes as documented, executable Python artifacts."""

    @staticmethod
    def export_script(recipe: AnalysisRecipe) -> bytes:
        """Return a deterministic command-line script for *recipe*."""
        # [impl->req~ring5.automation.script-notebook-export~1]
        recipe_json = AnalysisRecipeService.dumps(recipe).decode("utf-8")
        boolean_parser = ""
        if any(parameter.type == "boolean" for parameter in recipe.parameters):
            boolean_parser = '''

def _parse_boolean(value: str) -> bool:
    """Parse an explicit, human-readable boolean command-line value."""
    normalized = value.casefold()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    raise argparse.ArgumentTypeError("expected true/false, yes/no, or 1/0")
'''
        arguments = "\n".join(
            AnalysisRecipeAutomationService._script_argument(parameter)
            for parameter in recipe.parameters
        )
        source = f'''#!/usr/bin/env python3
"""Run an embedded RING-5 analysis recipe.

Pass ``--help`` to review the typed runtime parameters.
The embedded recipe is validated again before every run.
"""

from __future__ import annotations

import argparse
import json

import ring5


RECIPE_JSON = {recipe_json!r}
{boolean_parser}

def _build_parser() -> argparse.ArgumentParser:
    """Build this recipe's typed command-line interface."""
    parser = argparse.ArgumentParser(
        description={recipe.description or recipe.name!r},
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
{arguments or '    # This recipe has no runtime parameters.'}
    return parser


def main() -> None:
    """Execute the embedded recipe and print a concise JSON summary."""
    parameters = vars(_build_parser().parse_args())
    with ring5.Session() as session:
        recipe = session.decode_analysis_recipe(RECIPE_JSON)
        result = session.run_analysis_recipe(recipe, parameters)
    summary = {{
        "recipe": result.recipe_name,
        "parameters": dict(result.parameter_values),
        "rows": result.rows,
        "columns": list(result.columns),
        "plots": list(result.plot_names),
        "exports": list(result.exported_paths),
    }}
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
'''
        return source.encode("utf-8")

    @staticmethod
    def export_notebook(recipe: AnalysisRecipe) -> bytes:
        """Return a deterministic Jupyter notebook for *recipe*."""
        # [impl->req~ring5.automation.script-notebook-export~1]
        recipe_json = AnalysisRecipeService.dumps(recipe).decode("utf-8")
        setup = f'''import json
import ring5

RECIPE_JSON = {recipe_json!r}


def run_recipe(parameters):
    """Run the embedded recipe in a fresh, automatically closed session."""
    with ring5.Session() as session:
        recipe = session.decode_analysis_recipe(RECIPE_JSON)
        return session.run_analysis_recipe(recipe, parameters)
'''
        parameter_lines = ["parameters = {"]
        for parameter in recipe.parameters:
            value = parameter.default if parameter.default is not None else None
            comment = AnalysisRecipeAutomationService._notebook_parameter_comment(parameter)
            parameter_lines.append(f"    {parameter.name!r}: {value!r},{comment}")
        parameter_lines.append("}")
        parameters = "\n".join(parameter_lines) + "\n"
        run = """result = run_recipe(parameters)
summary = {
    "recipe": result.recipe_name,
    "parameters": dict(result.parameter_values),
    "rows": result.rows,
    "columns": list(result.columns),
    "plots": list(result.plot_names),
    "exports": list(result.exported_paths),
}
print(json.dumps(summary, indent=2, sort_keys=True))
result
"""
        notebook: dict[str, Any] = {
            "cells": [
                AnalysisRecipeAutomationService._markdown_cell(
                    AnalysisRecipeAutomationService._notebook_intro(recipe)
                ),
                AnalysisRecipeAutomationService._code_cell("ring5-setup", setup),
                AnalysisRecipeAutomationService._code_cell("ring5-parameters", parameters),
                AnalysisRecipeAutomationService._code_cell("ring5-run", run),
            ],
            "metadata": {
                "kernelspec": {
                    "display_name": "Python 3",
                    "language": "python",
                    "name": "python3",
                },
                "language_info": {"name": "python", "version": "3"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        }
        return (json.dumps(notebook, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode(
            "utf-8"
        )

    @staticmethod
    def _script_argument(parameter: RecipeParameter) -> str:
        option = "--" + parameter.name.replace("_", "-")
        parser_type = {
            "string": "str",
            "path": "str",
            "integer": "int",
            "number": "float",
            "boolean": "_parse_boolean",
        }[parameter.type]
        fields = [
            f"        {option!r},",
            f"        dest={parameter.name!r},",
            f"        type={parser_type},",
        ]
        if parameter.default is None:
            fields.append("        required=True,")
        else:
            fields.append(f"        default={parameter.default!r},")
        if parameter.choices:
            fields.append(f"        choices={parameter.choices!r},")
        help_text = parameter.description or f"Runtime {parameter.type} parameter."
        fields.append(f"        help={help_text!r},")
        return "    parser.add_argument(\n" + "\n".join(fields) + "\n    )"

    @staticmethod
    def _notebook_parameter_comment(parameter: RecipeParameter) -> str:
        details: list[str] = [parameter.type]
        if parameter.default is None:
            details.append("REQUIRED: replace None before running")
        return "  # " + " — ".join(details)

    @staticmethod
    def _notebook_intro(recipe: AnalysisRecipe) -> str:
        lines = [
            f"# {AnalysisRecipeAutomationService._markdown_text(recipe.name)}",
            "",
            AnalysisRecipeAutomationService._markdown_text(
                recipe.description or "Reusable RING-5 analysis recipe."
            ),
            "",
            "Generated by RING-5. This notebook uses only the supported `ring5` Python API.",
            "Edit the parameter cell, then run the cells from top to bottom. The embedded recipe ",
            "is validated before execution.",
            "",
            f"- Source: `{AnalysisRecipeAutomationService._markdown_text(recipe.source.kind)}`",
            f"- Shared transformations: {len(recipe.transformations)}",
            f"- Plots: {len(recipe.plots)}",
            f"- File exports: {len(recipe.exports)}",
        ]
        if recipe.parameters:
            lines.extend(["", "## Runtime parameters", "", "| Name | Type | Required | Purpose |"])
            lines.append("| --- | --- | --- | --- |")
            for parameter in recipe.parameters:
                lines.append(
                    "| "
                    + " | ".join(
                        (
                            AnalysisRecipeAutomationService._markdown_text(parameter.name),
                            AnalysisRecipeAutomationService._markdown_text(parameter.type),
                            "yes" if parameter.default is None else "no",
                            AnalysisRecipeAutomationService._markdown_text(
                                parameter.description or "—"
                            ),
                        )
                    )
                    + " |"
                )
        else:
            lines.extend(["", "This recipe has no runtime parameters."])
        return "\n".join(lines) + "\n"

    @staticmethod
    def _markdown_text(value: str) -> str:
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\\", "\\\\")
            .replace("|", "\\|")
            .replace("\r", " ")
            .replace("\n", " ")
        )

    @staticmethod
    def _markdown_cell(source: str) -> dict[str, Any]:
        return {"cell_type": "markdown", "id": "ring5-overview", "metadata": {}, "source": source}

    @staticmethod
    def _code_cell(identifier: str, source: str) -> dict[str, Any]:
        return {
            "cell_type": "code",
            "execution_count": None,
            "id": identifier,
            "metadata": {},
            "outputs": [],
            "source": source,
        }
