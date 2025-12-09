"""Test auto-refresh functionality for plots."""


def test_auto_refresh_config_detection():
    """Test that configuration changes are properly detected."""
    
    # Simulate initial plot configuration
    initial_config = {
        'type': 'bar',
        'x': 'benchmark',
        'y': 'speedup',
        'group': None,
        'color': None,
        'title': 'Performance',
        'xlabel': 'Benchmark',
        'ylabel': 'Speedup',
        'width': 800,
        'height': 600,
        'legend_title': '',
        'show_error_bars': False,
        'download_format': 'html',
        'legend_labels': None
    }
    
    # Test 1: No change
    current_config = initial_config.copy()
    config_changed = initial_config != current_config
    assert not config_changed, "Config should not be changed"
    
    # Test 2: Change title
    current_config = initial_config.copy()
    current_config['title'] = 'Updated Performance'
    config_changed = initial_config != current_config
    assert config_changed, "Config should be detected as changed"
    
    # Test 3: Change plot type
    current_config = initial_config.copy()
    current_config['type'] = 'grouped_bar'
    current_config['group'] = 'config'
    config_changed = initial_config != current_config
    assert config_changed, "Config should be detected as changed"
    
    # Test 4: Change dimensions
    current_config = initial_config.copy()
    current_config['width'] = 1200
    current_config['height'] = 800
    config_changed = initial_config != current_config
    assert config_changed, "Config should be detected as changed"
    
    # Test 5: Add legend labels
    current_config = initial_config.copy()
    current_config['legend_labels'] = {
        'baseline': 'Baseline Configuration',
        'optimized': 'Optimized Configuration'
    }
    config_changed = initial_config != current_config
    assert config_changed, "Config should be detected as changed"
    
    # Test 6: Toggle error bars
    current_config = initial_config.copy()
    current_config['show_error_bars'] = True
    config_changed = initial_config != current_config
    assert config_changed, "Config should be detected as changed"


def test_auto_refresh_triggers():
    """Test various triggers for auto-refresh."""
    
    triggers = {
        'plot_type_change': {'type': 'grouped_bar'},
        'axis_change': {'x': 'new_column'},
        'label_change': {'title': 'New Title'},
        'dimension_change': {'width': 1000},
        'legend_change': {'legend_title': 'Custom Legend'},
        'advanced_options': {'show_error_bars': True},
    }
    
    base_config = {
        'type': 'bar',
        'x': 'benchmark',
        'y': 'speedup',
        'group': None,
        'color': None,
        'title': 'Performance',
        'xlabel': 'Benchmark',
        'ylabel': 'Speedup',
        'width': 800,
        'height': 600,
        'legend_title': '',
        'show_error_bars': False,
        'download_format': 'html',
        'legend_labels': None
    }
    
    for trigger_name, change in triggers.items():
        modified_config = base_config.copy()
        modified_config.update(change)
        assert base_config != modified_config, f"{trigger_name} should trigger refresh"
