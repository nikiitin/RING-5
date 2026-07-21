"""Human-facing capture and management controls for analysis recipes."""

from __future__ import annotations

import re
from dataclasses import replace

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import AnalysisRecipe, RecipeExport, RecipeParameter


class AnalysisRecipeComponent:
    """Render versioned recipe capture, inspection, import, and export."""

    @staticmethod
    def render(api: ApplicationAPI) -> None:
        """Render the analysis-recipe workflow.

        Args:
            api: Session-owned application facade.
        """
        # [impl->req~ring5.portfolio.analysis-recipes~1]
        feedback = st.session_state.pop("analysis_recipe_feedback", None)
        if isinstance(feedback, str):
            st.success(feedback)

        with st.expander("Analysis recipes", expanded=False):
            st.caption(
                "Save the current source, parser variables, transformations, plots, and "
                "optional downloads as versioned JSON. Runtime paths remain typed parameters."
            )
            save_tab, saved_tab, import_tab = st.tabs(["Save current", "Saved", "Import"])
            with save_tab:
                AnalysisRecipeComponent._render_capture(api)
            with saved_tab:
                AnalysisRecipeComponent._render_saved(api)
            with import_tab:
                AnalysisRecipeComponent._render_import(api)

    @staticmethod
    def _render_capture(api: ApplicationAPI) -> None:
        name = st.text_input(
            "Recipe name",
            value="analysis_recipe",
            max_chars=80,
            key="analysis_recipe_name",
        )
        description = st.text_area(
            "Recipe description",
            max_chars=500,
            key="analysis_recipe_description",
        )
        parameterize_source = st.checkbox(
            "Make the source path a runtime parameter",
            value=True,
            key="analysis_recipe_parameterize_source",
        )
        include_exports = st.checkbox(
            "Download each current plot when the recipe runs",
            value=False,
            key="analysis_recipe_include_exports",
        )
        engine = "matplotlib"
        export_format = "pdf"
        output_dir = "recipe-output"
        if include_exports:
            engine = (
                st.selectbox(
                    "Download engine",
                    ["matplotlib", "plotly"],
                    key="analysis_recipe_export_engine",
                )
                or "matplotlib"
            )
            formats = (
                ["pdf", "svg", "png", "pgf"]
                if engine == "matplotlib"
                else [
                    "html",
                    "pdf",
                    "svg",
                    "png",
                ]
            )
            export_format = (
                st.selectbox(
                    "File format",
                    formats,
                    key="analysis_recipe_export_format",
                )
                or formats[0]
            )
            output_dir = st.text_input(
                "Default output directory",
                value="recipe-output",
                key="analysis_recipe_output_dir",
            )
        overwrite = st.checkbox(
            "Replace a saved recipe with this name",
            value=False,
            key="analysis_recipe_overwrite",
        )
        if not st.button(
            "Save analysis recipe",
            type="primary",
            key="analysis_recipe_save",
        ):
            return
        try:
            captured = api.data_services.capture_analysis_recipe(
                name,
                description=description,
            )
            parameters: list[RecipeParameter] = []
            source = captured.source
            if parameterize_source:
                parameters.append(
                    RecipeParameter(
                        "source_path",
                        "path",
                        description="CSV file or simulator-results root.",
                        default=source.path,
                    )
                )
                source = replace(source, path="{{source_path}}")
            exports: list[RecipeExport] = []
            if include_exports:
                parameters.append(
                    RecipeParameter(
                        "output_dir",
                        "path",
                        description="Directory for generated figure files.",
                        default=output_dir,
                    )
                )
                exports = [
                    RecipeExport(
                        plot=plot.name,
                        path=(
                            "{{output_dir}}/"
                            + AnalysisRecipeComponent._safe_stem(plot.name)
                            + f".{export_format}"
                        ),
                        engine=engine,  # type: ignore[arg-type]
                        format=export_format,
                    )
                    for plot in captured.plots
                ]
            recipe = api.data_services.capture_analysis_recipe(
                name,
                description=description,
                parameters=parameters,
                source=source,
                exports=exports,
            )
            api.data_services.save_analysis_recipe(recipe, overwrite=overwrite)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            st.error(str(exc))
            return
        st.session_state["analysis_recipe_feedback"] = f"Saved analysis recipe {recipe.name}."
        st.rerun()

    @staticmethod
    def _render_saved(api: ApplicationAPI) -> None:
        entries = api.data_services.list_analysis_recipes()
        if not entries:
            st.info("No analysis recipes saved yet.")
            return
        selected = st.selectbox(
            "Saved recipe",
            [entry.name for entry in entries],
            key="analysis_recipe_saved_select",
        )
        if selected is None:
            return
        try:
            recipe = api.data_services.load_analysis_recipe(selected)
            payload = api.data_services.export_analysis_recipe(recipe)
            script = api.data_services.export_analysis_recipe_script(recipe)
            notebook = api.data_services.export_analysis_recipe_notebook(recipe)
        except (OSError, TypeError, ValueError) as exc:
            st.error(str(exc))
            return
        AnalysisRecipeComponent._render_summary(recipe)
        # [impl->req~ring5.automation.script-notebook-export~1]
        st.caption(
            "Take this analysis outside the browser. The script provides typed command-line "
            "options; the notebook provides an editable parameter cell. Both embed this exact "
            "recipe and use only the supported ring5 Python API."
        )
        st.download_button(
            "Download recipe JSON",
            data=payload,
            file_name=f"{AnalysisRecipeComponent._safe_stem(recipe.name)}.ring5-recipe.json",
            mime="application/json",
            key="analysis_recipe_download",
            on_click="ignore",
        )
        st.download_button(
            "Download Python script",
            data=script,
            file_name=f"{AnalysisRecipeComponent._safe_stem(recipe.name)}.py",
            mime="text/x-python",
            key="analysis_recipe_script_download",
            on_click="ignore",
        )
        st.download_button(
            "Download Jupyter notebook",
            data=notebook,
            file_name=f"{AnalysisRecipeComponent._safe_stem(recipe.name)}.ipynb",
            mime="application/x-ipynb+json",
            key="analysis_recipe_notebook_download",
            on_click="ignore",
        )
        if st.button("Delete recipe", key="analysis_recipe_delete"):
            try:
                api.data_services.delete_analysis_recipe(recipe.name)
            except (OSError, ValueError) as exc:
                st.error(str(exc))
                return
            st.session_state["analysis_recipe_feedback"] = f"Deleted analysis recipe {recipe.name}."
            st.rerun()

    @staticmethod
    def _render_import(api: ApplicationAPI) -> None:
        uploaded = st.file_uploader(
            "Analysis recipe JSON",
            type=["json"],
            key="analysis_recipe_import_file",
            help="Accepts versioned RING-5 analysis recipes up to 512 KiB.",
        )
        overwrite = st.checkbox(
            "Replace a saved recipe with the imported name",
            value=False,
            key="analysis_recipe_import_overwrite",
        )
        if not st.button(
            "Import analysis recipe",
            disabled=uploaded is None,
            key="analysis_recipe_import",
        ):
            return
        if uploaded is None:
            return
        try:
            recipe = api.data_services.import_analysis_recipe(
                uploaded.getvalue(),
                overwrite=overwrite,
            )
        except (OSError, TypeError, ValueError) as exc:
            st.error(str(exc))
            return
        st.session_state["analysis_recipe_feedback"] = f"Imported analysis recipe {recipe.name}."
        st.rerun()

    @staticmethod
    def _render_summary(recipe: AnalysisRecipe) -> None:
        source_label = "CSV" if recipe.source.kind == "csv" else "Simulator parser"
        st.markdown(f"**{recipe.name}** — {recipe.description or 'No description'}")
        st.caption(
            f"{source_label}; {len(recipe.transformations)} shared transformation(s); "
            f"{len(recipe.plots)} plot(s); {len(recipe.exports)} download(s)."
        )
        if recipe.parameters:
            st.dataframe(
                [
                    {
                        "Parameter": parameter.name,
                        "Type": parameter.type,
                        "Default": parameter.default,
                        "Required": parameter.required,
                        "Purpose": parameter.description,
                    }
                    for parameter in recipe.parameters
                ],
                hide_index=True,
                width="stretch",
            )

    @staticmethod
    def _safe_stem(value: str) -> str:
        """Return a portable non-empty file stem."""
        stem = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip()).strip("-._")
        return stem or "analysis-recipe"
