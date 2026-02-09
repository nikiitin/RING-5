"""
Performance Monitoring Page

Shows cache statistics, performance metrics, and optimization controls.
"""

import logging

import streamlit as st

from src.core.application_api import ApplicationAPI
from src.core.performance import clear_all_caches, get_cache_stats

logger = logging.getLogger(__name__)


def render_performance_page(api: ApplicationAPI) -> None:
    """Render the performance monitoring dashboard."""

    st.title("⚡ Performance Monitor")
    st.markdown("---")

    # Cache Statistics
    st.header("Cache Statistics")

    stats = get_cache_stats()
    csv_stats = api.data_services.get_cache_stats()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("Plot Figure Cache")
        plot_stats = stats.get("plot_cache", {})

        st.metric("Cache Hits", plot_stats.get("hits", 0))
        st.metric("Cache Misses", plot_stats.get("misses", 0))
        st.metric("Hit Rate", f"{plot_stats.get('hit_rate', 0):.1f}%")
        st.metric("Cached Figures", plot_stats.get("size", 0))

        # Interpretation
        hit_rate = plot_stats.get("hit_rate", 0)
        if hit_rate > 70:
            st.success("✅ Excellent cache performance!")
        elif hit_rate > 40:
            st.info("ℹ️ Good cache performance")
        else:
            st.warning("⚠️ Low cache hit rate - consider increasing cache size")

    with col2:
        st.subheader("CSV Pool Caches")

        # Metadata cache
        meta_stats = csv_stats.get("metadata_cache", {})
        st.metric("Metadata Hits", meta_stats.get("hits", 0))
        st.metric("Metadata Misses", meta_stats.get("misses", 0))
        st.metric("Meta Hit Rate", f"{meta_stats.get('hit_rate', 0):.1f}%")

        # DataFrame cache
        df_stats = csv_stats.get("dataframe_cache", {})
        st.metric("Cached DataFrames", df_stats.get("size", 0))

    with col3:
        st.subheader("Cache Management")
        st.markdown("""
        **How caching works:**
        - Plot figures cached by config + data
        - CSV metadata cached (columns, rows)
        - DataFrames cached for reuse
        - TTL: 5-10 minutes
        """)

        if st.button("Clear All Caches", type="primary"):
            clear_all_caches()
            api.data_services.clear_caches()
            st.success("All caches cleared!")
            st.rerun()

    st.markdown("---")

    # Session State Size
    st.header("Session State")

    session_keys = list(st.session_state.keys())

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Keys", len(session_keys))

    with col2:
        # Count plot objects
        plots = api.state_manager.get_plots()
        st.metric("Plot Objects", len(plots))

    with col3:
        # Check for data
        has_data = api.state_manager.has_data()
        st.metric("Data Loaded", "Yes" if has_data else "No")

    # Show all keys in expander
    with st.expander("Show All Session Keys"):
        for key in sorted(session_keys):
            st.text(f"• {key}")

    st.markdown("---")

    # Performance Tips
    st.header("📊 Performance Tips")

    st.markdown("""
    ### Optimization Strategy

    1. **Data Loading**
       - Use CSV pool to avoid re-parsing gem5 stats
       - Enable parser caching for repeated variables

    2. **Plot Generation**
       - Plots are cached automatically based on config
       - Avoid unnecessary `should_generate=True` calls
       - Legend customization invalidates cache

    3. **Shaper Pipeline**
       - Keep pipelines short (< 5 shapers)
       - Use filters early to reduce data size
       - Combine multiple renames into one

    4. **Session State**
       - Clear unused plots regularly
       - Portfolio save/load is optimized
       - Widget state is automatically cleaned

    ### When to Clear Cache

    - After major config changes
    - When debugging plot rendering
    - If memory usage is high
    - Before performance benchmarking
    """)

    st.markdown("---")

    # Advanced Diagnostics
    with st.expander("🔧 Advanced Diagnostics"):
        st.subheader("Repository Statistics")

        # Show what's in session state
        st.json(
            {
                "data_loaded": api.state_manager.has_data(),
                "processed_data_loaded": "processed_data" in st.session_state,
                "plots_count": len(api.state_manager.get_plots()),
                "plot_counter": api.state_manager.get_plot_counter(),
                "current_plot_id": api.state_manager.get_current_plot_id(),
                "stats_path": (
                    "Not exposed in StateManager public API yet"
                    if not api.state_manager.has_data()
                    else "Loaded"
                ),
                "csv_pool_size": len(st.session_state.get("csv_pool", [])),
                "saved_configs": len(st.session_state.get("saved_configs", [])),
            }
        )
