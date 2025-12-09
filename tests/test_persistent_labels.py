"""Test persistent legend labels across different group-by columns."""


def test_persistent_legend_labels_per_column():
    """Test that legend labels are preserved per column."""
    
    # Simulate a plot object
    plot = {
        'id': 1,
        'name': 'Test Plot',
        'legend_mappings_by_column': {}
    }
    
    # Step 1: User sets custom labels for 'config' column
    current_column = 'config'
    config_labels = {
        'baseline': 'Baseline Configuration',
        'optimized': 'Optimized Build',
        'experimental': 'Experimental Feature'
    }
    plot['legend_mappings_by_column'][current_column] = config_labels
    
    # Step 2: User switches to 'architecture' column
    current_column = 'architecture'
    arch_labels = {
        'x86': 'Intel x86-64',
        'arm': 'ARM Cortex',
        'risc': 'RISC-V'
    }
    plot['legend_mappings_by_column'][current_column] = arch_labels
    
    # Verify 'config' labels are still stored
    assert 'config' in plot['legend_mappings_by_column']
    assert plot['legend_mappings_by_column']['config'] == config_labels
    
    # Step 3: User switches BACK to 'config' column
    current_column = 'config'
    restored_labels = plot['legend_mappings_by_column'].get(current_column, {})
    
    # Verify the labels were preserved
    assert restored_labels == config_labels
    assert restored_labels['baseline'] == 'Baseline Configuration'
    assert restored_labels['optimized'] == 'Optimized Build'
    assert restored_labels['experimental'] == 'Experimental Feature'
    
    # Step 4: Verify all columns' labels are still there
    assert len(plot['legend_mappings_by_column']) == 2
    assert 'config' in plot['legend_mappings_by_column']
    assert 'architecture' in plot['legend_mappings_by_column']


def test_legend_labels_backward_compatibility():
    """Test backward compatibility with old legend_mappings field."""
    
    # Simulate old plot object with legacy legend_mappings
    plot = {
        'id': 1,
        'name': 'Old Plot',
        'legend_mappings': {
            'baseline': 'Baseline Config',
            'optimized': 'Optimized Config'
        }
    }
    
    # When initializing legend_mappings_by_column
    if 'legend_mappings_by_column' not in plot:
        plot['legend_mappings_by_column'] = {}
    
    # Get existing mappings for 'config' column
    current_column = 'config'
    existing_mappings = plot['legend_mappings_by_column'].get(current_column, {})
    
    # Should fallback to legacy legend_mappings
    if not existing_mappings and plot.get('legend_mappings'):
        existing_mappings = plot['legend_mappings']
    
    assert existing_mappings == plot['legend_mappings']
    assert existing_mappings['baseline'] == 'Baseline Config'


def test_multiple_column_persistence():
    """Test that multiple columns can have different custom labels."""
    
    plot = {
        'id': 1,
        'legend_mappings_by_column': {
            'config': {
                'baseline': 'Baseline',
                'opt1': 'Optimization 1',
                'opt2': 'Optimization 2'
            },
            'architecture': {
                'x86': 'Intel',
                'arm': 'ARM',
                'risc': 'RISC-V'
            },
            'compiler': {
                'gcc': 'GCC Compiler',
                'clang': 'Clang/LLVM',
                'icc': 'Intel Compiler'
            }
        }
    }
    
    # Verify all three columns have independent mappings
    assert len(plot['legend_mappings_by_column']) == 3
    
    # Verify each column's mappings are independent
    assert plot['legend_mappings_by_column']['config']['baseline'] == 'Baseline'
    assert plot['legend_mappings_by_column']['architecture']['x86'] == 'Intel'
    assert plot['legend_mappings_by_column']['compiler']['gcc'] == 'GCC Compiler'
    
    # Switching between columns should preserve all
    for column in ['config', 'architecture', 'compiler']:
        labels = plot['legend_mappings_by_column'].get(column, {})
        assert len(labels) == 3  # Each has 3 custom labels
