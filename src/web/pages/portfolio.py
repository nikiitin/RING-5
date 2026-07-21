"""
Portfolio Management Page

Provides functionality to save and load complete analysis snapshots including
data, plots, and all configurations as portfolio files.
"""

import logging


import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.models import EnvironmentComparison
from src.core.services.environment_metadata_service import EnvironmentMetadataService
from src.core.services.portfolio_migrator import PortfolioVersionError
from src.web.components.report_composer import ReportComposer
from src.web.components.analysis_recipe_component import AnalysisRecipeComponent
from src.web.rendering.config_builder import build_figure_spec_dict

logger: logging.Logger = logging.getLogger(__name__)


def _display_version(value: str | None) -> str:
    """Return a human label for an optional captured version."""
    return value or "Not available"


def _render_environment_comparison(api: ApplicationAPI, portfolio_name: str) -> None:
    # [impl->req~ring5.portfolio.environment-metadata~1]
    """Show save-time environment evidence before a portfolio is restored."""
    try:
        portfolio = api.data_services.load_portfolio(portfolio_name)
        comparison = EnvironmentMetadataService.compare(portfolio.get("environment_metadata"))
    except Exception as exc:
        logger.warning(
            "PORTFOLIO: environment metadata for '%s' could not be inspected: %s",
            portfolio_name,
            exc,
        )
        st.warning("The saved environment could not be inspected.")
        return

    with st.expander("Reproducibility environment", expanded=False):
        _render_environment_status(comparison)
        st.dataframe(
            [
                {
                    "Area": item.section,
                    "Component": item.component,
                    "Saved": _display_version(item.recorded),
                    "Current": _display_version(item.current),
                    "Status": item.status.replace("-", " ").title(),
                }
                for item in comparison.differences
            ],
            hide_index=True,
            width="stretch",
        )
        st.caption(
            "This comparison reports exact versions. A difference is evidence to review, "
            "not proof that the portfolio is incompatible."
        )


def _render_environment_status(comparison: EnvironmentComparison) -> None:
    """Render one concise interpretation above environment details."""
    if not comparison.recorded_available:
        st.info("Environment not recorded — this portfolio predates environment capture.")
    elif comparison.exact_match:
        st.success("Saved environment matches this RING-5 runtime exactly.")
    else:
        st.warning(
            f"{comparison.review_count} saved environment value(s) differ or were not recorded."
        )


def _portfolio_fragment(api: ApplicationAPI) -> None:
    # [impl->req~ring5.portfolio.partial-report~1]
    # [impl->req~ring5.portfolio.manage~1]
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Save Portfolio")
        st.markdown(
            "Save current data, all plots, and their configurations to a single portfolio file."
        )

        portfolio_name = st.text_input(
            "Portfolio Name", value="my_portfolio", key="portfolio_save_name"
        )

        if st.button("Save Portfolio", type="primary", width="stretch"):
            try:
                current_data = api.state_manager.get_data()
                api.data_services.save_portfolio(
                    name=portfolio_name,
                    data=current_data,
                    plots=api.state_manager.get_plots(),
                    config=api.state_manager.get_config(),
                    plot_counter=api.state_manager.get_plot_counter(),
                    csv_path=api.state_manager.get_csv_path(),
                    parse_variables=api.state_manager.get_parse_variables(),
                    figure_spec_enricher=build_figure_spec_dict,
                )
                st.toast(f"Portfolio saved: {portfolio_name}", icon="✅")
                st.rerun()
            except Exception as e:
                st.exception(e)
                logger.error(
                    "PORTFOLIO: Failed to save portfolio %r: %s",
                    str(portfolio_name).replace("\n", ""),
                    e,
                    exc_info=True,
                )

    # Fetch portfolio list once for both sections (avoids double disk I/O).
    portfolios = api.data_services.list_portfolios()

    with col2:
        st.markdown("### Load Portfolio")
        st.markdown("Restore a previously saved portfolio with all data and plot configurations.")

        if portfolios:
            selected_portfolio = st.selectbox(
                "Select Portfolio", portfolios, key="portfolio_load_select"
            )
            _render_environment_comparison(api, str(selected_portfolio))

            if st.button("Load Portfolio", type="primary", width="stretch"):
                try:
                    data = api.data_services.load_portfolio(selected_portfolio)
                    report = api.state_manager.restore_session(data)
                    if not report.complete:
                        issues: list[str] = list(report.plots_skipped)
                        if report.data_error:
                            issues.append(f"data: {report.data_error}")
                        if report.parse_variables_skipped:
                            issues.append(
                                f"{report.parse_variables_skipped} malformed "
                                "parse-variable entries skipped"
                            )
                        # Toast (not st.warning): must survive the rerun below.
                        st.toast(
                            f"Restore incomplete — {'; '.join(issues[:3])}"
                            + ("…" if len(issues) > 3 else ""),
                            icon="⚠️",
                        )
                        logger.warning(
                            "PORTFOLIO: incomplete restore of '%s': %s",
                            selected_portfolio,
                            issues,
                        )
                    st.toast(f"Portfolio loaded: {selected_portfolio}", icon="✅")
                    st.rerun(scope="app")
                except PortfolioVersionError as e:
                    st.error(str(e))
                except Exception as e:
                    st.exception(e)
                    logger.error(
                        "PORTFOLIO: Failed to load portfolio '%s': %s",
                        selected_portfolio,
                        e,
                        exc_info=True,
                    )
        else:
            st.warning("No portfolios found. Save one first!")

    # Manage Saved Portfolios
    st.markdown("---")
    st.markdown("### Manage Saved Portfolios")

    if portfolios:
        for pname in portfolios:
            with st.expander(f"{pname}"):

                def _delete_portfolio(name: str = pname) -> None:
                    api.data_services.delete_portfolio(name)
                    st.toast(f"Deleted {name}", icon="🗑️")

                st.button(
                    "Delete",
                    key=f"del_portfolio_{pname}",
                    on_click=_delete_portfolio,
                    type="tertiary",
                )

    st.markdown("---")
    AnalysisRecipeComponent.render(api)


def show_portfolio_page(api: ApplicationAPI) -> None:
    """
    Display the portfolio management page.

    Allows users to save complete snapshots of their work including data,
    plots, and configurations, and restore previously saved portfolios.
    """
    st.markdown("## Portfolio Management")
    st.markdown(
        "Save and load complete snapshots of your work including data, plots, and all "
        "configurations."
    )
    st.markdown("---")

    st.fragment(_portfolio_fragment)(api)
    st.markdown("---")
    ReportComposer(api).render()
