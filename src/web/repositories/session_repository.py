"""
Session Repository
Single Responsibility: Manage session lifecycle and restoration.
"""

import io
import logging
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from src.plotting import BasePlot
from src.web.types import PortfolioData

logger = logging.getLogger(__name__)


class SessionRepository:
    """
    Repository for managing session lifecycle operations.
    
    Responsibilities:
    - Session initialization
    - Session restoration from portfolios
    - Widget state cleanup
    - Complete session clearing
    
    Adheres to SRP: Only manages session lifecycle, nothing else.
    
    Note:
        This repository coordinates with other repositories for
        complete session operations but doesn't duplicate their logic.
    """
    
    @staticmethod
    def initialize_session() -> None:
        """
        Initialize all session state with default values.
        
        This should be called once at application startup.
        Delegates to specialized repositories for their domains.
        """
        from src.web.repositories import (
            DataRepository,
            PlotRepository,
            ParserStateRepository,
            ConfigRepository
        )
        
        # Initialize data state
        if DataRepository.DATA_KEY not in st.session_state:
            st.session_state[DataRepository.DATA_KEY] = None
        if DataRepository.PROCESSED_DATA_KEY not in st.session_state:
            st.session_state[DataRepository.PROCESSED_DATA_KEY] = None
        
        # Initialize plot state
        if PlotRepository.PLOTS_KEY not in st.session_state:
            st.session_state[PlotRepository.PLOTS_KEY] = []
        if PlotRepository.PLOT_COUNTER_KEY not in st.session_state:
            st.session_state[PlotRepository.PLOT_COUNTER_KEY] = 0
        if PlotRepository.CURRENT_PLOT_ID_KEY not in st.session_state:
            st.session_state[PlotRepository.CURRENT_PLOT_ID_KEY] = None
        
        # Initialize parser state
        if ParserStateRepository.PARSE_VARIABLES_KEY not in st.session_state:
            st.session_state[ParserStateRepository.PARSE_VARIABLES_KEY] = (
                ParserStateRepository.DEFAULT_PARSE_VARIABLES.copy()
            )
        if ParserStateRepository.STATS_PATH_KEY not in st.session_state:
            st.session_state[ParserStateRepository.STATS_PATH_KEY] = "/path/to/gem5/stats"
        if ParserStateRepository.STATS_PATTERN_KEY not in st.session_state:
            st.session_state[ParserStateRepository.STATS_PATTERN_KEY] = "stats.txt"
        if ParserStateRepository.SCANNED_VARIABLES_KEY not in st.session_state:
            st.session_state[ParserStateRepository.SCANNED_VARIABLES_KEY] = []
        if ParserStateRepository.USE_PARSER_KEY not in st.session_state:
            st.session_state[ParserStateRepository.USE_PARSER_KEY] = False
        
        # Initialize config state
        if ConfigRepository.CONFIG_KEY not in st.session_state:
            st.session_state[ConfigRepository.CONFIG_KEY] = {}
        if ConfigRepository.TEMP_DIR_KEY not in st.session_state:
            st.session_state[ConfigRepository.TEMP_DIR_KEY] = None
        if ConfigRepository.CSV_PATH_KEY not in st.session_state:
            st.session_state[ConfigRepository.CSV_PATH_KEY] = None
        if ConfigRepository.CSV_POOL_KEY not in st.session_state:
            st.session_state[ConfigRepository.CSV_POOL_KEY] = {}
        if ConfigRepository.SAVED_CONFIGS_KEY not in st.session_state:
            st.session_state[ConfigRepository.SAVED_CONFIGS_KEY] = {}
        
        logger.info("SESSION_REPO: Session initialized with default values")
    
    @staticmethod
    def clear_widget_state() -> None:
        """
        Clear widget-specific state markers from session.
        
        This removes transient UI widget keys that should not persist
        across portfolio loads or session restarts.
        """
        markers = [
            "_order_",
            "leg_ren_",
            "xaxis_angle_",
            "ydtick_",
            "bargap_",
            "editable_",
            "show_error_bars",
            "colsel_",
            "norm_",
            "mean_",
            "sort_",
            "filter_",
            "trans_",
            "leg_x_",
            "leg_y_",
            "leg_orient_",
        ]
        
        keys_to_delete = [
            k for k in st.session_state.keys()
            if isinstance(k, str) and any(marker in k for marker in markers)
        ]
        
        for key in keys_to_delete:
            del st.session_state[key]
        
        logger.info(f"SESSION_REPO: Cleared {len(keys_to_delete)} widget state keys")
    
    @staticmethod
    def restore_from_portfolio(portfolio_data: PortfolioData) -> None:
        """
        Restore complete session state from portfolio data.
        
        Args:
            portfolio_data: Portfolio restoration data
            
        Note:
            This coordinates restoration across all repositories while
            maintaining their individual responsibilities.
        """
        from src.web.repositories import (
            DataRepository,
            PlotRepository,
            ParserStateRepository,
            ConfigRepository
        )
        
        # Clear widget state first
        SessionRepository.clear_widget_state()
        
        # Restore parser state
        ParserStateRepository.set_parse_variables(
            portfolio_data.get("parse_variables", [])
        )
        ParserStateRepository.set_stats_path(
            portfolio_data.get("stats_path", "")
        )
        ParserStateRepository.set_stats_pattern(
            portfolio_data.get("stats_pattern", "stats.txt")
        )
        ParserStateRepository.set_scanned_variables(
            portfolio_data.get("scanned_variables", [])
        )
        ParserStateRepository.set_using_parser(
            portfolio_data.get("use_parser", False)
        )
        
        # Restore config state
        ConfigRepository.set_csv_path(portfolio_data.get("csv_path", ""))
        ConfigRepository.set_config(portfolio_data.get("config", {}))
        
        # Restore data
        if "data_csv" in portfolio_data:
            try:
                df = pd.read_csv(io.StringIO(portfolio_data["data_csv"]))
                DataRepository.set_data(df)
                logger.info(f"SESSION_REPO: Restored data - {len(df)} rows")
            except Exception as e:
                logger.error(f"SESSION_REPO: Failed to restore data: {e}")
        
        # Restore plots
        loaded_plots: List[BasePlot] = []
        for plot_data in portfolio_data.get("plots", []):
            try:
                if "plot_type" in plot_data:
                    loaded_plots.append(BasePlot.from_dict(plot_data))
            except Exception as e:
                logger.error(f"SESSION_REPO: Failed to restore plot: {e}")
        
        PlotRepository.set_plots(loaded_plots)
        PlotRepository.set_plot_counter(
            portfolio_data.get("plot_counter", len(loaded_plots))
        )
        
        logger.info(
            f"SESSION_REPO: Session restored - "
            f"{len(loaded_plots)} plots, parser={'ON' if portfolio_data.get('use_parser') else 'OFF'}"
        )
    
    @staticmethod
    def clear_all() -> None:
        """
        Clear all session state completely.
        
        This performs a full reset, delegating to specialized repositories
        for their respective domains.
        """
        from src.web.repositories import (
            DataRepository,
            PlotRepository,
            ParserStateRepository,
            ConfigRepository
        )
        
        # Clear each domain
        DataRepository.clear_data()
        PlotRepository.clear_plots()
        PlotRepository.set_plot_counter(0)
        PlotRepository.set_current_plot_id(None)
        ParserStateRepository.clear_parser_state()
        ConfigRepository.clear_config()
        
        # Clear widget state
        SessionRepository.clear_widget_state()
        
        logger.info("SESSION_REPO: Complete session cleared")
