"""Versioned storage and typed materialization for analysis recipes."""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import math
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, cast

from src.core.common.security_limits import (
    MAX_ANALYSIS_RECIPE_BYTES,
    MAX_ANALYSIS_RECIPE_DEPTH,
    MAX_ANALYSIS_RECIPE_EXPORTS,
    MAX_ANALYSIS_RECIPE_PARAMETERS,
    MAX_ANALYSIS_RECIPE_PLOTS,
    MAX_ANALYSIS_RECIPE_STRING_LENGTH,
    MAX_ANALYSIS_RECIPE_TRANSFORMATIONS,
    MAX_PIPELINE_CONFIG_DESCRIPTION_LENGTH,
    MAX_PIPELINE_CONFIG_NAME_LENGTH,
)
from src.core.common.utils import sanitize_filename, validate_path_within
from src.core.models.data_models import ParseVariableConfig, ScannedVariableDict
from src.core.models.recipe_models import (
    AnalysisRecipe,
    AnalysisRecipeInfo,
    RecipeExport,
    RecipeParameter,
    RecipeParameterType,
    RecipePlot,
    RecipeScalar,
    RecipeSource,
)
from src.core.models.shaper_models import ShaperStepConfig
from src.core.services.data_services.path_service import PathService
from src.core.services.data_services.pipeline_config_exchange_service import (
    PipelineConfigExchangeService,
)
from src.core.services.shapers.factory import ShaperFactory
from src.core.state.state_manager import StateManager

ANALYSIS_RECIPE_FORMAT = "ring5.analysis-recipe"
ANALYSIS_RECIPE_SCHEMA_VERSION = 1

_PARAMETER_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_PLACEHOLDER = re.compile(r"{{\s*([A-Za-z][A-Za-z0-9_]{0,63})\s*}}")
_EXACT_PLACEHOLDER = re.compile(r"^{{\s*([A-Za-z][A-Za-z0-9_]{0,63})\s*}}$")
_PARAMETER_TYPES = {"string", "integer", "number", "boolean", "path"}
_EXPORT_FORMATS = {
    "plotly": frozenset({"html", "pdf", "png", "svg"}),
    "matplotlib": frozenset({"pdf", "pgf", "png", "svg"}),
}
_TOP_LEVEL_FIELDS = {
    "format",
    "schema_version",
    "name",
    "description",
    "parameters",
    "source",
    "transformations",
    "plots",
    "exports",
}

logger = logging.getLogger(__name__)


class AnalysisRecipeService:
    """Capture, validate, persist, and materialize reusable analysis recipes."""

    def __init__(self, state_manager: StateManager) -> None:
        """Initialize recipe capture against one session state manager."""
        self._state_manager = state_manager

    def capture(
        self,
        name: str,
        *,
        description: str = "",
        parameters: Sequence[RecipeParameter] = (),
        source: RecipeSource | None = None,
        transformations: Sequence[ShaperStepConfig] = (),
        exports: Sequence[RecipeExport] = (),
    ) -> AnalysisRecipe:
        """Capture current source provenance, plots, and pipelines as a recipe.

        Args:
            name: Stable recipe name.
            description: Human-readable purpose.
            parameters: Typed runtime placeholder declarations.
            source: Explicit source, or ``None`` to capture current state.
            transformations: Dataset-wide shapers run before every plot.
            exports: Named-plot output instructions.

        Returns:
            A validated immutable recipe ready to save or serialize.
        """
        # [impl->req~ring5.portfolio.analysis-recipes~1]
        resolved_source = source or self._capture_source()
        plots: list[RecipePlot] = []
        for plot in self._state_manager.get_plots():
            pipeline = tuple(copy.deepcopy(step["config"]) for step in plot.pipeline)
            plots.append(
                RecipePlot(
                    name=plot.name,
                    plot_type=plot.plot_type,
                    config=copy.deepcopy(plot.config),
                    pipeline=pipeline,
                )
            )
        recipe = AnalysisRecipe(
            name=name,
            description=description,
            parameters=tuple(parameters),
            source=resolved_source,
            transformations=tuple(copy.deepcopy(list(transformations))),
            plots=tuple(plots),
            exports=tuple(exports),
        )
        self.validate(recipe)
        return recipe

    def _capture_source(self) -> RecipeSource:
        if self._state_manager.is_using_parser():
            path = self._state_manager.get_stats_path()
            if not path:
                raise ValueError("The active parser source has no statistics path.")
            variables = tuple(copy.deepcopy(self._state_manager.get_parse_variables()))
            if not variables:
                raise ValueError("The active parser source has no parser variables.")
            return RecipeSource(
                kind="parser",
                path=path,
                pattern=self._state_manager.get_stats_pattern(),
                strategy=self._state_manager.get_parser_strategy(),
                variables=variables,
                scanned_variables=tuple(copy.deepcopy(self._state_manager.get_scanned_variables())),
            )
        csv_path = self._state_manager.get_csv_path()
        if not csv_path:
            raise ValueError("The active dataset has no reusable CSV source path.")
        return RecipeSource(kind="csv", path=csv_path)

    @staticmethod
    def validate(recipe: AnalysisRecipe) -> None:
        """Validate recipe structure, placeholders, and concrete pipelines.

        Args:
            recipe: Recipe to inspect without mutation.

        Raises:
            TypeError: A field has the wrong Python type.
            ValueError: Content, limits, placeholders, or pipelines are invalid.
        """
        if not isinstance(recipe, AnalysisRecipe):
            raise TypeError("Analysis recipe must be an AnalysisRecipe instance.")
        if isinstance(recipe.schema_version, bool) or not isinstance(recipe.schema_version, int):
            raise TypeError("Analysis recipe schema version must be an integer.")
        if recipe.schema_version != ANALYSIS_RECIPE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported analysis recipe schema version {recipe.schema_version!r}; "
                f"expected {ANALYSIS_RECIPE_SCHEMA_VERSION}."
            )
        recipe_name = AnalysisRecipeService._bounded_text(
            recipe.name,
            "Analysis recipe name",
            MAX_PIPELINE_CONFIG_NAME_LENGTH,
            required=True,
        )
        if any(ord(character) < 32 for character in recipe_name):
            raise ValueError("Analysis recipe name must not contain control characters.")
        AnalysisRecipeService._bounded_text(
            recipe.description,
            "Analysis recipe description",
            MAX_PIPELINE_CONFIG_DESCRIPTION_LENGTH,
        )
        if len(recipe.parameters) > MAX_ANALYSIS_RECIPE_PARAMETERS:
            raise ValueError(
                f"Analysis recipe exceeds the {MAX_ANALYSIS_RECIPE_PARAMETERS}-parameter limit."
            )
        if len(recipe.transformations) > MAX_ANALYSIS_RECIPE_TRANSFORMATIONS:
            raise ValueError(
                "Analysis recipe exceeds the "
                f"{MAX_ANALYSIS_RECIPE_TRANSFORMATIONS}-transformation limit."
            )
        if len(recipe.plots) > MAX_ANALYSIS_RECIPE_PLOTS:
            raise ValueError(f"Analysis recipe exceeds the {MAX_ANALYSIS_RECIPE_PLOTS}-plot limit.")
        if len(recipe.exports) > MAX_ANALYSIS_RECIPE_EXPORTS:
            raise ValueError(
                f"Analysis recipe exceeds the {MAX_ANALYSIS_RECIPE_EXPORTS}-export limit."
            )

        declared: dict[str, RecipeParameter] = {}
        for parameter in recipe.parameters:
            AnalysisRecipeService._validate_parameter(parameter)
            if parameter.name in declared:
                raise ValueError(f"Duplicate analysis recipe parameter {parameter.name!r}.")
            declared[parameter.name] = parameter

        AnalysisRecipeService._validate_source(recipe.source)
        plot_names: set[str] = set()
        for plot in recipe.plots:
            if not isinstance(plot, RecipePlot):
                raise TypeError("Analysis recipe plots must be RecipePlot instances.")
            AnalysisRecipeService._bounded_text(plot.name, "Recipe plot name", 120, required=True)
            AnalysisRecipeService._bounded_text(
                plot.plot_type, "Recipe plot type", 80, required=True
            )
            if plot.name in plot_names:
                raise ValueError(f"Duplicate recipe plot name {plot.name!r}.")
            plot_names.add(plot.name)
            if not isinstance(plot.config, Mapping):
                raise TypeError(f"Recipe plot {plot.name!r} config must be a mapping.")
            AnalysisRecipeService._validate_pipeline(plot.pipeline, f"plot {plot.name!r}")
        AnalysisRecipeService._validate_pipeline(recipe.transformations, "global transformations")

        export_paths: set[str] = set()
        for export in recipe.exports:
            if not isinstance(export, RecipeExport):
                raise TypeError("Analysis recipe exports must be RecipeExport instances.")
            if export.plot not in plot_names:
                raise ValueError(f"Recipe export references unknown plot {export.plot!r}.")
            AnalysisRecipeService._validate_path_text(export.path, "Recipe export path")
            if export.path in export_paths:
                raise ValueError(f"Duplicate recipe export path {export.path!r}.")
            export_paths.add(export.path)
            if export.engine not in {"plotly", "matplotlib"}:
                raise ValueError(f"Unsupported recipe export engine {export.engine!r}.")
            AnalysisRecipeService._bounded_text(
                export.format, "Recipe export format", 16, required=True
            )
            supported_formats = _EXPORT_FORMATS[export.engine]
            if export.format not in supported_formats:
                raise ValueError(
                    f"Format {export.format!r} is not supported for {export.engine} recipe "
                    f"exports; choose from {', '.join(sorted(supported_formats))}."
                )
            if not isinstance(export.deterministic, bool):
                raise TypeError("Recipe export deterministic must be boolean.")

        template_payload = {
            "source": AnalysisRecipeService._source_payload(recipe.source),
            "transformations": list(recipe.transformations),
            "plots": [AnalysisRecipeService._plot_payload(plot) for plot in recipe.plots],
            "exports": [AnalysisRecipeService._export_payload(export) for export in recipe.exports],
        }
        AnalysisRecipeService._validate_json_value(template_payload, depth=0)
        referenced = AnalysisRecipeService._placeholder_names(template_payload)
        unknown = sorted(referenced - set(declared))
        if unknown:
            raise ValueError(
                "Analysis recipe uses undeclared parameters: " + ", ".join(unknown) + "."
            )

    @staticmethod
    def _validate_parameter(parameter: RecipeParameter) -> None:
        if not isinstance(parameter, RecipeParameter):
            raise TypeError("Analysis recipe parameters must be RecipeParameter instances.")
        if not _PARAMETER_NAME.fullmatch(parameter.name):
            raise ValueError(
                "Recipe parameter names must start with a letter and contain only letters, "
                "digits, or underscores."
            )
        if parameter.type not in _PARAMETER_TYPES:
            raise ValueError(f"Unsupported recipe parameter type {parameter.type!r}.")
        AnalysisRecipeService._bounded_text(
            parameter.description, "Recipe parameter description", 300
        )
        if not isinstance(parameter.required, bool):
            raise TypeError("Recipe parameter required must be boolean.")
        if not isinstance(parameter.choices, tuple):
            raise TypeError("Recipe parameter choices must be a tuple.")
        if not parameter.required and parameter.default is None:
            raise ValueError(
                f"Optional recipe parameter {parameter.name!r} must declare a default."
            )
        if parameter.default is not None:
            AnalysisRecipeService._validate_parameter_value(parameter, parameter.default)
        for choice in parameter.choices:
            AnalysisRecipeService._validate_parameter_value(parameter, choice)
        if parameter.default is not None and parameter.choices:
            if parameter.default not in parameter.choices:
                raise ValueError(
                    f"Recipe parameter {parameter.name!r} default is not one of its choices."
                )

    @staticmethod
    def _validate_parameter_value(parameter: RecipeParameter, value: object) -> RecipeScalar:
        valid = False
        if parameter.type in {"string", "path"}:
            valid = isinstance(value, str)
        elif parameter.type == "integer":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif parameter.type == "number":
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(float(value))
            )
        elif parameter.type == "boolean":
            valid = isinstance(value, bool)
        if not valid:
            raise TypeError(
                f"Recipe parameter {parameter.name!r} expects a {parameter.type} value."
            )
        if isinstance(value, str):
            if len(value) > MAX_ANALYSIS_RECIPE_STRING_LENGTH:
                raise ValueError(
                    f"Recipe parameter {parameter.name!r} exceeds "
                    f"{MAX_ANALYSIS_RECIPE_STRING_LENGTH} characters."
                )
            if parameter.type == "path" and (
                not value.strip() or any(ord(character) < 32 for character in value)
            ):
                raise ValueError(
                    f"Recipe path parameter {parameter.name!r} must be a non-empty valid path."
                )
        if parameter.choices and value not in parameter.choices:
            raise ValueError(
                f"Recipe parameter {parameter.name!r} must be one of "
                + ", ".join(repr(choice) for choice in parameter.choices)
                + "."
            )
        return cast(RecipeScalar, value)

    @staticmethod
    def _validate_source(source: RecipeSource) -> None:
        if not isinstance(source, RecipeSource):
            raise TypeError("Analysis recipe source must be a RecipeSource instance.")
        if source.kind not in {"csv", "parser"}:
            raise ValueError(f"Unsupported analysis recipe source {source.kind!r}.")
        AnalysisRecipeService._validate_path_text(source.path, "Recipe source path")
        if isinstance(source.scan_limit, bool) or not isinstance(source.scan_limit, int):
            raise TypeError("Recipe parser scan_limit must be an integer.")
        if not 0 <= source.scan_limit <= 10_000:
            raise ValueError("Recipe parser scan_limit must be between zero and 10,000.")
        if not isinstance(source.strict, bool):
            raise TypeError("Recipe parser strict must be boolean.")
        AnalysisRecipeService._bounded_text(
            source.pattern, "Recipe parser pattern", 500, required=True
        )
        AnalysisRecipeService._bounded_text(
            source.strategy, "Recipe parser strategy", 80, required=True
        )
        if source.kind == "csv":
            if source.variables or source.scanned_variables:
                raise ValueError("CSV recipe sources cannot contain parser variables.")
            return
        if not source.variables:
            raise ValueError("Parser recipe sources require at least one variable.")
        for index, variable in enumerate(source.variables):
            if not isinstance(variable, dict):
                raise TypeError(f"Recipe parser variable {index} must be an object.")
            name = variable.get("name")
            var_type = variable.get("type")
            if not isinstance(name, str) or not name:
                raise ValueError(f"Recipe parser variable {index} requires a name.")
            if not isinstance(var_type, str) or not var_type:
                raise ValueError(f"Recipe parser variable {index} requires a type.")
        for index, scanned_variable in enumerate(source.scanned_variables):
            if not isinstance(scanned_variable, dict):
                raise TypeError(f"Recipe scanned variable {index} must be an object.")
            name = scanned_variable.get("name")
            var_type = scanned_variable.get("type")
            entries = scanned_variable.get("entries")
            if not isinstance(name, str) or not name:
                raise ValueError(f"Recipe scanned variable {index} requires a name.")
            if not isinstance(var_type, str) or not var_type:
                raise ValueError(f"Recipe scanned variable {index} requires a type.")
            if not isinstance(entries, list) or not all(
                isinstance(entry, str) for entry in entries
            ):
                raise TypeError(f"Recipe scanned variable {index} entries must be text values.")

    @staticmethod
    def _validate_pipeline(pipeline: Sequence[ShaperStepConfig], location: str) -> None:
        if len(pipeline) > MAX_ANALYSIS_RECIPE_TRANSFORMATIONS:
            raise ValueError(f"Recipe {location} exceeds the transformation limit.")
        AnalysisRecipeService._validate_json_value(list(pipeline), depth=0)
        contains_template = bool(AnalysisRecipeService._placeholder_names(list(pipeline)))
        if contains_template:
            for index, step in enumerate(pipeline):
                if not isinstance(step, dict):
                    raise TypeError(f"Recipe {location} step {index} must be an object.")
                shaper_type = step.get("type")
                if shaper_type not in ShaperFactory.get_available_types():
                    raise ValueError(
                        f"Recipe {location} step {index} uses unknown shaper type "
                        f"{shaper_type!r}."
                    )
            return
        PipelineConfigExchangeService.dumps(
            "Recipe validation",
            "",
            list(copy.deepcopy(pipeline)),
        )

    @staticmethod
    def resolve_parameters(
        recipe: AnalysisRecipe,
        values: Mapping[str, RecipeScalar] | None = None,
    ) -> dict[str, RecipeScalar]:
        """Validate and resolve supplied values with recipe defaults.

        Args:
            recipe: Valid recipe containing parameter declarations.
            values: Runtime values keyed by parameter name.

        Returns:
            Resolved values in declaration order.

        Raises:
            TypeError: A runtime value does not match its declared type.
            ValueError: A value is missing, unknown, or outside its choices.
        """
        AnalysisRecipeService.validate(recipe)
        supplied = dict(values or {})
        declared = {parameter.name for parameter in recipe.parameters}
        unknown = sorted(set(supplied) - declared)
        if unknown:
            raise ValueError("Unknown analysis recipe parameters: " + ", ".join(unknown) + ".")
        resolved: dict[str, RecipeScalar] = {}
        for parameter in recipe.parameters:
            if parameter.name in supplied:
                value = supplied[parameter.name]
            elif parameter.default is not None:
                value = parameter.default
            else:
                raise ValueError(f"Analysis recipe parameter {parameter.name!r} is required.")
            resolved[parameter.name] = AnalysisRecipeService._validate_parameter_value(
                parameter, value
            )
        return resolved

    @staticmethod
    def materialize(
        recipe: AnalysisRecipe,
        values: Mapping[str, RecipeScalar] | None = None,
    ) -> AnalysisRecipe:
        """Substitute typed runtime values into a validated recipe.

        Whole-value placeholders retain integers, numbers, and booleans;
        placeholders embedded in text use their stable string form.

        Args:
            recipe: Recipe containing ``{{parameter}}`` placeholders.
            values: Runtime values keyed by declared parameter name.

        Returns:
            A fully concrete recipe with the original declarations retained.
        """
        # [impl->req~ring5.portfolio.analysis-recipes~1]
        resolved = AnalysisRecipeService.resolve_parameters(recipe, values)
        source_payload = AnalysisRecipeService._substitute(
            AnalysisRecipeService._source_payload(recipe.source), resolved
        )
        transformations = AnalysisRecipeService._substitute(list(recipe.transformations), resolved)
        plots = AnalysisRecipeService._substitute(
            [AnalysisRecipeService._plot_payload(plot) for plot in recipe.plots], resolved
        )
        exports = AnalysisRecipeService._substitute(
            [AnalysisRecipeService._export_payload(export) for export in recipe.exports], resolved
        )
        materialized = AnalysisRecipe(
            name=recipe.name,
            description=recipe.description,
            parameters=recipe.parameters,
            source=AnalysisRecipeService._source_from_payload(source_payload),
            transformations=tuple(cast(list[ShaperStepConfig], transformations)),
            plots=tuple(
                AnalysisRecipeService._plot_from_payload(item)
                for item in cast(list[dict[str, Any]], plots)
            ),
            exports=tuple(
                AnalysisRecipeService._export_from_payload(item)
                for item in cast(list[dict[str, Any]], exports)
            ),
        )
        AnalysisRecipeService.validate(materialized)
        return materialized

    @staticmethod
    def dumps(recipe: AnalysisRecipe) -> bytes:
        """Serialize a validated recipe as deterministic versioned JSON."""
        # [impl->req~ring5.portfolio.analysis-recipes~1]
        AnalysisRecipeService.validate(recipe)
        encoded = (
            json.dumps(
                AnalysisRecipeService._recipe_payload(recipe),
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
        if len(encoded) > MAX_ANALYSIS_RECIPE_BYTES:
            raise ValueError("Analysis recipe JSON exceeds the 512 KiB limit.")
        return encoded

    @staticmethod
    def loads(payload: str | bytes | bytearray) -> AnalysisRecipe:
        """Load and validate one bounded versioned recipe document."""
        # [impl->req~ring5.portfolio.analysis-recipes~1]
        if isinstance(payload, str):
            raw = payload.encode("utf-8")
        elif isinstance(payload, (bytes, bytearray)):
            raw = bytes(payload)
        else:
            raise TypeError("Analysis recipe import expects JSON text or bytes.")
        if len(raw) > MAX_ANALYSIS_RECIPE_BYTES:
            raise ValueError("Analysis recipe JSON exceeds the 512 KiB limit.")
        try:
            value = json.loads(raw.decode("utf-8"), parse_constant=_reject_json_constant)
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError) as exc:
            raise ValueError("Analysis recipe is not valid finite UTF-8 JSON.") from exc
        if not isinstance(value, dict):
            raise ValueError("Analysis recipe JSON must contain one object.")
        unknown = sorted(set(value) - _TOP_LEVEL_FIELDS)
        if unknown:
            raise ValueError("Analysis recipe has unsupported fields: " + ", ".join(unknown) + ".")
        if value.get("format") != ANALYSIS_RECIPE_FORMAT:
            raise ValueError(f"Unsupported analysis recipe format {value.get('format')!r}.")
        version = value.get("schema_version")
        if isinstance(version, bool) or not isinstance(version, int):
            raise ValueError("Analysis recipe schema_version must be an integer.")
        if version != ANALYSIS_RECIPE_SCHEMA_VERSION:
            raise ValueError(
                f"Unsupported analysis recipe schema version {version!r}; "
                f"expected {ANALYSIS_RECIPE_SCHEMA_VERSION}."
            )
        required = {"name", "source", "parameters", "transformations", "plots", "exports"}
        if not required.issubset(value):
            raise ValueError("Analysis recipe has missing required fields.")
        recipe = AnalysisRecipeService._recipe_from_payload(value)
        AnalysisRecipeService.validate(recipe)
        return recipe

    @staticmethod
    def save(recipe: AnalysisRecipe, *, overwrite: bool = False) -> str:
        """Atomically persist a validated recipe without silent replacement."""
        payload = AnalysisRecipeService.dumps(recipe)
        directory = PathService.get_analysis_recipes_dir()
        path = AnalysisRecipeService._storage_path(recipe.name, directory)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=directory,
                prefix=".ring5-analysis-recipe-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(payload)
            if overwrite:
                os.replace(temporary_path, path)
            else:
                try:
                    os.link(temporary_path, path)
                except FileExistsError as exc:
                    raise FileExistsError(
                        f"Analysis recipe {recipe.name!r} already exists."
                    ) from exc
                temporary_path.unlink()
            temporary_path = None
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()
        return str(path)

    @staticmethod
    def import_recipe(
        payload: str | bytes | bytearray, *, overwrite: bool = False
    ) -> AnalysisRecipe:
        """Validate and persist one portable recipe document."""
        recipe = AnalysisRecipeService.loads(payload)
        AnalysisRecipeService.save(recipe, overwrite=overwrite)
        return recipe

    @staticmethod
    def load(name: str) -> AnalysisRecipe:
        """Load a saved recipe by logical name."""
        directory = PathService.get_analysis_recipes_dir()
        path = AnalysisRecipeService._storage_path(name, directory)
        if not path.exists():
            raise FileNotFoundError(f"Analysis recipe {name!r} was not found.")
        recipe = AnalysisRecipeService.loads(path.read_bytes())
        if recipe.name != name:
            raise FileNotFoundError(f"Analysis recipe {name!r} was not found.")
        return recipe

    @staticmethod
    def list() -> tuple[AnalysisRecipeInfo, ...]:
        """List readable saved recipes in case-insensitive name order."""
        directory = PathService.get_analysis_recipes_dir()
        entries: list[AnalysisRecipeInfo] = []
        for path in directory.glob("*.json"):
            try:
                recipe = AnalysisRecipeService.loads(path.read_bytes())
                modified = path.stat().st_mtime
            except (OSError, TypeError, ValueError) as exc:
                logger.debug("Skipping unreadable analysis recipe %s: %s", path, exc)
                continue
            entries.append(
                AnalysisRecipeInfo(
                    name=recipe.name,
                    description=recipe.description,
                    path=str(path),
                    modified=modified,
                    parameters=len(recipe.parameters),
                    transformations=len(recipe.transformations),
                    plots=len(recipe.plots),
                    exports=len(recipe.exports),
                )
            )
        return tuple(sorted(entries, key=lambda item: item.name.casefold()))

    @staticmethod
    def delete(name: str) -> None:
        """Delete a saved recipe, raising when it does not exist."""
        directory = PathService.get_analysis_recipes_dir()
        path = AnalysisRecipeService._storage_path(name, directory)
        try:
            path.unlink()
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Analysis recipe {name!r} was not found.") from exc

    @staticmethod
    def _recipe_payload(recipe: AnalysisRecipe) -> dict[str, Any]:
        return {
            "format": ANALYSIS_RECIPE_FORMAT,
            "schema_version": ANALYSIS_RECIPE_SCHEMA_VERSION,
            "name": recipe.name,
            "description": recipe.description,
            "parameters": [
                {
                    "name": parameter.name,
                    "type": parameter.type,
                    "description": parameter.description,
                    "required": parameter.required,
                    "default": parameter.default,
                    "choices": list(parameter.choices),
                }
                for parameter in recipe.parameters
            ],
            "source": AnalysisRecipeService._source_payload(recipe.source),
            "transformations": list(copy.deepcopy(recipe.transformations)),
            "plots": [AnalysisRecipeService._plot_payload(plot) for plot in recipe.plots],
            "exports": [AnalysisRecipeService._export_payload(export) for export in recipe.exports],
        }

    @staticmethod
    def _recipe_from_payload(value: Mapping[str, Any]) -> AnalysisRecipe:
        parameters_value = _require_list(value.get("parameters"), "parameters")
        parameters: list[RecipeParameter] = []
        for item in parameters_value:
            mapping = _require_mapping(item, "recipe parameter")
            _reject_unknown(
                mapping,
                {"name", "type", "description", "required", "default", "choices"},
                "recipe parameter",
            )
            choices = _require_list(mapping.get("choices", []), "parameter choices")
            parameters.append(
                RecipeParameter(
                    name=_require_string(mapping.get("name"), "parameter name"),
                    type=cast(
                        RecipeParameterType,
                        _require_string(mapping.get("type"), "parameter type"),
                    ),
                    description=_require_string(
                        mapping.get("description", ""), "parameter description"
                    ),
                    required=_require_bool(mapping.get("required", True), "parameter required"),
                    default=cast(RecipeScalar | None, mapping.get("default")),
                    choices=tuple(cast(list[RecipeScalar], choices)),
                )
            )
        return AnalysisRecipe(
            name=_require_string(value.get("name"), "recipe name"),
            description=_require_string(value.get("description", ""), "recipe description"),
            parameters=tuple(parameters),
            source=AnalysisRecipeService._source_from_payload(value.get("source")),
            transformations=tuple(
                cast(
                    list[ShaperStepConfig],
                    _require_list(value.get("transformations"), "transformations"),
                )
            ),
            plots=tuple(
                AnalysisRecipeService._plot_from_payload(item)
                for item in _require_list(value.get("plots"), "plots")
            ),
            exports=tuple(
                AnalysisRecipeService._export_from_payload(item)
                for item in _require_list(value.get("exports"), "exports")
            ),
            schema_version=cast(int, value.get("schema_version")),
        )

    @staticmethod
    def _source_payload(source: RecipeSource) -> dict[str, Any]:
        return {
            "kind": source.kind,
            "path": source.path,
            "pattern": source.pattern,
            "strategy": source.strategy,
            "variables": list(copy.deepcopy(source.variables)),
            "scanned_variables": list(copy.deepcopy(source.scanned_variables)),
            "scan_limit": source.scan_limit,
            "strict": source.strict,
        }

    @staticmethod
    def _source_from_payload(value: object) -> RecipeSource:
        mapping = _require_mapping(value, "recipe source")
        _reject_unknown(
            mapping,
            {
                "kind",
                "path",
                "pattern",
                "strategy",
                "variables",
                "scanned_variables",
                "scan_limit",
                "strict",
            },
            "recipe source",
        )
        variables = _require_list(mapping.get("variables", []), "source variables")
        scanned = _require_list(mapping.get("scanned_variables", []), "scanned variables")
        return RecipeSource(
            kind=cast(Any, _require_string(mapping.get("kind"), "source kind")),
            path=_require_string(mapping.get("path"), "source path"),
            pattern=_require_string(mapping.get("pattern", "stats.txt"), "source pattern"),
            strategy=_require_string(mapping.get("strategy", "simple"), "source strategy"),
            variables=tuple(cast(list[ParseVariableConfig], variables)),
            scanned_variables=tuple(cast(list[ScannedVariableDict], scanned)),
            scan_limit=_require_int(mapping.get("scan_limit", 10), "source scan_limit"),
            strict=_require_bool(mapping.get("strict", True), "source strict"),
        )

    @staticmethod
    def _plot_payload(plot: RecipePlot) -> dict[str, Any]:
        return {
            "name": plot.name,
            "plot_type": plot.plot_type,
            "config": copy.deepcopy(dict(plot.config)),
            "pipeline": list(copy.deepcopy(plot.pipeline)),
        }

    @staticmethod
    def _plot_from_payload(value: object) -> RecipePlot:
        mapping = _require_mapping(value, "recipe plot")
        _reject_unknown(mapping, {"name", "plot_type", "config", "pipeline"}, "recipe plot")
        return RecipePlot(
            name=_require_string(mapping.get("name"), "plot name"),
            plot_type=_require_string(mapping.get("plot_type"), "plot type"),
            config=copy.deepcopy(_require_mapping(mapping.get("config"), "plot config")),
            pipeline=tuple(
                cast(
                    list[ShaperStepConfig],
                    _require_list(mapping.get("pipeline", []), "plot pipeline"),
                )
            ),
        )

    @staticmethod
    def _export_payload(export: RecipeExport) -> dict[str, Any]:
        return {
            "plot": export.plot,
            "path": export.path,
            "engine": export.engine,
            "format": export.format,
            "deterministic": export.deterministic,
        }

    @staticmethod
    def _export_from_payload(value: object) -> RecipeExport:
        mapping = _require_mapping(value, "recipe export")
        _reject_unknown(
            mapping, {"plot", "path", "engine", "format", "deterministic"}, "recipe export"
        )
        return RecipeExport(
            plot=_require_string(mapping.get("plot"), "export plot"),
            path=_require_string(mapping.get("path"), "export path"),
            engine=cast(Any, _require_string(mapping.get("engine"), "export engine")),
            format=_require_string(mapping.get("format"), "export format"),
            deterministic=_require_bool(mapping.get("deterministic", True), "export deterministic"),
        )

    @staticmethod
    def _substitute(value: Any, values: Mapping[str, RecipeScalar]) -> Any:
        if isinstance(value, str):
            exact = _EXACT_PLACEHOLDER.fullmatch(value)
            if exact:
                return copy.deepcopy(values[exact.group(1)])

            def replace(match: re.Match[str]) -> str:
                replacement = values[match.group(1)]
                if isinstance(replacement, bool):
                    return "true" if replacement else "false"
                return str(replacement)

            return _PLACEHOLDER.sub(replace, value)
        if isinstance(value, list):
            return [AnalysisRecipeService._substitute(item, values) for item in value]
        if isinstance(value, tuple):
            return [AnalysisRecipeService._substitute(item, values) for item in value]
        if isinstance(value, dict):
            return {
                key: AnalysisRecipeService._substitute(item, values) for key, item in value.items()
            }
        return copy.deepcopy(value)

    @staticmethod
    def _placeholder_names(value: object) -> set[str]:
        found: set[str] = set()
        if isinstance(value, str):
            found.update(match.group(1) for match in _PLACEHOLDER.finditer(value))
            if "{{" in value or "}}" in value:
                scrubbed = _PLACEHOLDER.sub("", value)
                if "{{" in scrubbed or "}}" in scrubbed:
                    raise ValueError(f"Invalid analysis recipe placeholder syntax in {value!r}.")
        elif isinstance(value, (list, tuple)):
            for item in value:
                found.update(AnalysisRecipeService._placeholder_names(item))
        elif isinstance(value, Mapping):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError("Analysis recipe object keys must be text.")
                if "{{" in key or "}}" in key:
                    raise ValueError("Analysis recipe object keys cannot contain placeholders.")
                found.update(AnalysisRecipeService._placeholder_names(item))
        return found

    @staticmethod
    def _validate_json_value(value: object, *, depth: int) -> None:
        if depth > MAX_ANALYSIS_RECIPE_DEPTH:
            raise ValueError("Analysis recipe nesting is too deep.")
        if isinstance(value, str):
            if len(value) > MAX_ANALYSIS_RECIPE_STRING_LENGTH:
                raise ValueError(
                    "Analysis recipe text exceeds "
                    f"{MAX_ANALYSIS_RECIPE_STRING_LENGTH} characters."
                )
            return
        if value is None or isinstance(value, (bool, int)):
            return
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ValueError("Analysis recipe numbers must be finite.")
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                AnalysisRecipeService._validate_json_value(item, depth=depth + 1)
            return
        if isinstance(value, Mapping):
            for key, item in value.items():
                if not isinstance(key, str):
                    raise TypeError("Analysis recipe object keys must be text.")
                AnalysisRecipeService._validate_json_value(key, depth=depth + 1)
                AnalysisRecipeService._validate_json_value(item, depth=depth + 1)
            return
        raise TypeError("Analysis recipe contains a non-JSON value.")

    @staticmethod
    def _bounded_text(
        value: object,
        label: str,
        limit: int,
        *,
        required: bool = False,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{label} must be text.")
        if required and not value.strip():
            raise ValueError(f"{label} must not be empty.")
        if len(value) > limit:
            raise ValueError(f"{label} exceeds {limit} characters.")
        return value

    @staticmethod
    def _validate_path_text(value: object, label: str) -> str:
        path = AnalysisRecipeService._bounded_text(
            value,
            label,
            MAX_ANALYSIS_RECIPE_STRING_LENGTH,
            required=True,
        )
        if any(ord(character) < 32 for character in path):
            raise ValueError(f"{label} must not contain control characters.")
        return path

    @staticmethod
    def _storage_path(name: object, directory: Path) -> Path:
        validated = AnalysisRecipeService._bounded_text(
            name,
            "Analysis recipe name",
            MAX_PIPELINE_CONFIG_NAME_LENGTH,
            required=True,
        )
        if any(ord(character) < 32 for character in validated):
            raise ValueError("Analysis recipe name must not contain control characters.")
        identity = hashlib.sha256(validated.encode("utf-8")).hexdigest()[:12]
        filename = f"{sanitize_filename(validated)}-{identity}.json"
        return validate_path_within(directory / filename, directory)


def _reject_json_constant(constant: str) -> float:
    raise ValueError(f"non-finite number {constant}")


def _require_mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"Analysis {label} must be an object.")
    return cast(dict[str, Any], value)


def _require_list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"Analysis recipe {label} must be a list.")
    return value


def _require_string(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"Analysis recipe {label} must be text.")
    return value


def _require_bool(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"Analysis recipe {label} must be boolean.")
    return value


def _require_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"Analysis recipe {label} must be an integer.")
    return value


def _reject_unknown(mapping: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        raise ValueError(f"Analysis {label} has unsupported fields: " + ", ".join(unknown) + ".")
