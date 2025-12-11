import streamlit as st
import pandas as pd
from src.data_plotter.src.shaper.shaperFactory import ShaperFactory

# Constants
SHAPER_TYPE_MAP = {
    'Column Selector': 'columnSelector',
    'Normalize': 'normalize',
    'Mean Calculator': 'mean',
    'Sort': 'sort',
    'Filter': 'conditionSelector',
    # Reverse mapping for compatibility
    'columnSelector': 'Column Selector',
    'normalize': 'Normalize',
    'mean': 'Mean Calculator',
    'sort': 'Sort',
    'conditionSelector': 'Filter'
}

def configure_shaper(shaper_type, data, shaper_id, existing_config):
    """Configure a specific shaper and return its config."""
    config = {}
    
    # Handle None existing_config
    if existing_config is None:
        existing_config = {}
    
    if shaper_type == 'columnSelector':
        st.markdown("Select which columns to keep")
        default_cols = existing_config.get('columns', [data.columns[0]] if len(data.columns) > 0 else [])
        selected_columns = st.multiselect(
            "Columns to keep",
            options=data.columns.tolist(),
            default=default_cols,
            key=f"colsel_{shaper_id}"
        )
        config = {
            'type': 'columnSelector',
            'columns': selected_columns if selected_columns else []
        }
    
    elif shaper_type == 'normalize':
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        col1, col2 = st.columns(2)
        with col1:
            normalizer_vars = st.multiselect(
                "Normalizer variables (will be summed)",
                options=numeric_cols,
                default=existing_config.get('normalizerVars', []),
                key=f"normalizer_vars_{shaper_id}",
                help="These columns will be summed to create the baseline normalizer value"
            )
            
            normalize_vars = st.multiselect(
                "Variables to normalize",
                options=numeric_cols,
                default=existing_config.get('normalizeVars', []),
                key=f"norm_vars_{shaper_id}",
                help="These columns will be divided by the sum of normalizer variables"
            )
            
            norm_col_default = existing_config.get('normalizerColumn')
            norm_col_index = categorical_cols.index(norm_col_default) if norm_col_default in categorical_cols else 0
            normalizer_column = st.selectbox(
                "Normalizer column (baseline identifier)",
                options=categorical_cols,
                index=norm_col_index,
                key=f"norm_col_{shaper_id}",
                help="The categorical column that identifies the baseline configuration"
            )
        
        with col2:
            normalizer_value = None
            if normalizer_column:
                unique_vals = data[normalizer_column].unique().tolist()
                norm_val_default = existing_config.get('normalizerValue')
                norm_val_index = unique_vals.index(norm_val_default) if norm_val_default in unique_vals else 0
                normalizer_value = st.selectbox(
                    "Baseline value",
                    options=unique_vals,
                    index=norm_val_index,
                    key=f"norm_val_{shaper_id}"
                )
            
            group_by = st.multiselect(
                "Group by",
                options=categorical_cols,
                default=existing_config.get('groupBy', []),
                key=f"norm_group_{shaper_id}"
            )
            
            # Checkbox for auto-normalizing SD columns
            normalize_sd = st.checkbox(
                "Automatically normalize standard deviation columns",
                value=existing_config.get('normalizeSd', True),
                key=f"norm_sd_{shaper_id}",
                help="If enabled, .sd columns will be automatically normalized using the sum of their base normalizer columns"
            )
        
        if normalizer_vars and normalize_vars and normalizer_column and normalizer_value and group_by:
            config = {
                'type': 'normalize',
                'normalizerVars': normalizer_vars,
                'normalizeVars': normalize_vars,
                'normalizerColumn': normalizer_column,
                'normalizerValue': normalizer_value,
                'groupBy': group_by,
                'normalizeSd': normalize_sd
            }
    
    elif shaper_type == 'mean':
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            mean_algos = ['arithmean', 'geomean', 'harmean']
            mean_algo_default = existing_config.get('meanAlgorithm', 'arithmean')
            mean_algo_index = mean_algos.index(mean_algo_default) if mean_algo_default in mean_algos else 0
            mean_algorithm = st.selectbox(
                "Mean type",
                options=mean_algos,
                index=mean_algo_index,
                key=f"mean_algo_{shaper_id}"
            )
        
        with col2:
            mean_vars = st.multiselect(
                "Variables",
                options=numeric_cols,
                default=existing_config.get('meanVars', []),
                key=f"mean_vars_{shaper_id}"
            )
        
        with col3:
            group_col_default = existing_config.get('groupingColumn')
            group_col_index = categorical_cols.index(group_col_default) if group_col_default in categorical_cols else 0
            grouping_column = st.selectbox(
                "Group by",
                options=categorical_cols,
                index=group_col_index,
                key=f"mean_group_{shaper_id}"
            )
        
        if mean_vars and grouping_column:
            replace_col_default = existing_config.get('replacingColumn')
            replace_col_index = categorical_cols.index(replace_col_default) if replace_col_default in categorical_cols else 0
            replacing_column = st.selectbox(
                "Replacing column",
                options=categorical_cols,
                index=replace_col_index,
                key=f"mean_replace_{shaper_id}"
            )
            
            if replacing_column:
                config = {
                    'type': 'mean',
                    'meanAlgorithm': mean_algorithm,
                    'meanVars': mean_vars,
                    'groupingColumn': grouping_column,
                    'replacingColumn': replacing_column
                }
    
    elif shaper_type == 'sort':
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        
        sort_col_default = None
        if existing_config.get('order_dict'):
            sort_col_default = list(existing_config['order_dict'].keys())[0]
        sort_col_index = categorical_cols.index(sort_col_default) if sort_col_default in categorical_cols else 0
        
        sort_column = st.selectbox(
            "Column to sort",
            options=categorical_cols,
            index=sort_col_index,
            key=f"sort_col_{shaper_id}"
        )
        
        if sort_column:
            unique_values = data[sort_column].unique().tolist()
            st.markdown(f"Define order for `{sort_column}`")
            
            # Use existing order if available, otherwise use unique values
            default_order = existing_config.get('order_dict', {}).get(sort_column, unique_values)
            
            # Initialize order in session state if not exists
            order_key = f"sort_order_list_{shaper_id}"
            if order_key not in st.session_state:
                st.session_state[order_key] = default_order.copy()
            
            order_list = st.session_state[order_key]
            
            # Display sortable list with up/down buttons
            st.markdown("**Drag items to reorder** (use ↑↓ buttons)")
            for i, value in enumerate(order_list):
                col1, col2, col3, col4 = st.columns([6, 1, 1, 1])
                with col1:
                    st.text(value)
                with col2:
                    if i > 0:
                        if st.button("↑", key=f"sort_up_{shaper_id}_{i}"):
                            order_list[i], order_list[i-1] = order_list[i-1], order_list[i]
                            st.session_state[order_key] = order_list
                            st.rerun()
                with col3:
                    if i < len(order_list) - 1:
                        if st.button("↓", key=f"sort_down_{shaper_id}_{i}"):
                            order_list[i], order_list[i+1] = order_list[i+1], order_list[i]
                            st.session_state[order_key] = order_list
                            st.rerun()
                with col4:
                    if st.button("🗑️", key=f"sort_del_{shaper_id}_{i}"):
                        order_list.pop(i)
                        st.session_state[order_key] = order_list
                        st.rerun()
            
            # Add missing values
            missing = [v for v in unique_values if v not in order_list]
            if missing:
                st.warning(f"Missing values (will appear at end): {', '.join(map(str, missing))}")
                if st.button("Add all missing values", key=f"sort_add_missing_{shaper_id}"):
                    order_list.extend(missing)
                    st.session_state[order_key] = order_list
                    st.rerun()
            
            # Preview button
            if st.button("Preview Sort Result", key=f"sort_preview_{shaper_id}"):
                try:
                    preview_data = data.copy()
                    # Apply the sort shaper with correct params structure
                    sort_config = {'order_dict': {sort_column: order_list}}
                    sorter = ShaperFactory.createShaper('sort', sort_config)
                    preview_result = sorter(preview_data)
                    st.markdown("**Preview (first 20 rows):**")
                    st.dataframe(preview_result.head(20), width='stretch')
                except Exception as e:
                    st.error(f"Preview failed: {e}")
            
            if order_list:
                config = {
                    'type': 'sort',
                    'order_dict': {sort_column: order_list}
                }
    
    elif shaper_type == 'conditionSelector':
        categorical_cols = data.select_dtypes(include=['object']).columns.tolist()
        numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        all_cols = categorical_cols + numeric_cols
        
        st.markdown("Filter rows based on column values")
        
        filter_col_default = existing_config.get('column')
        filter_col_index = all_cols.index(filter_col_default) if filter_col_default in all_cols else 0
        
        filter_column = st.selectbox(
            "Column to filter",
            options=all_cols,
            index=filter_col_index,
            key=f"filter_col_{shaper_id}"
        )
        
        if filter_column:
            unique_values = data[filter_column].unique().tolist()
            
            # Check if column is numeric or categorical
            is_numeric = filter_column in numeric_cols
            
            if is_numeric:
                # Numeric filtering
                st.markdown("**Numeric Filter**")
                
                filter_modes = ['range', 'greater_than', 'less_than', 'equals']
                filter_mode_default = existing_config.get('mode', 'range')
                filter_mode_index = filter_modes.index(filter_mode_default) if filter_mode_default in filter_modes else 0
                
                filter_mode = st.selectbox(
                    "Filter mode",
                    options=filter_modes,
                    index=filter_mode_index,
                    key=f"filter_mode_{shaper_id}"
                )
                
                min_val = float(data[filter_column].min())
                max_val = float(data[filter_column].max())
                
                if filter_mode == 'range':
                    default_range = existing_config.get('range', [min_val, max_val])
                    value_range = st.slider(
                        "Value range",
                        min_value=min_val,
                        max_value=max_val,
                        value=(float(default_range[0]), float(default_range[1])),
                        key=f"filter_range_{shaper_id}"
                    )
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'mode': 'range',
                        'range': list(value_range)
                    }
                elif filter_mode == 'greater_than':
                    default_threshold = existing_config.get('threshold', min_val)
                    threshold = st.number_input(
                        "Greater than",
                        value=float(default_threshold),
                        key=f"filter_gt_{shaper_id}"
                    )
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'mode': 'greater_than',
                        'threshold': threshold
                    }
                elif filter_mode == 'less_than':
                    default_threshold = existing_config.get('threshold', max_val)
                    threshold = st.number_input(
                        "Less than",
                        value=float(default_threshold),
                        key=f"filter_lt_{shaper_id}"
                    )
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'mode': 'less_than',
                        'threshold': threshold
                    }
                else:  # equals
                    default_value = existing_config.get('value', min_val)
                    value = st.number_input(
                        "Equals",
                        value=float(default_value),
                        key=f"filter_eq_{shaper_id}"
                    )
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'mode': 'equals',
                        'value': value
                    }
            else:
                # Categorical filtering
                st.markdown("**Categorical Filter**")
                
                default_values = existing_config.get('values', [])
                selected_values = st.multiselect(
                    "Keep rows where value is:",
                    options=unique_values,
                    default=default_values,
                    key=f"filter_values_{shaper_id}"
                )
                
                if selected_values:
                    config = {
                        'type': 'conditionSelector',
                        'column': filter_column,
                        'values': selected_values
                    }
    
    return config


def apply_shapers(data, shapers_config):
    """Apply shapers to data."""
    result = data.copy()
    
    for shaper_config in shapers_config:
        shaper_type = shaper_config['type']
        shaper = ShaperFactory.createShaper(shaper_type, shaper_config)
        result = shaper(result)
    
    return result
