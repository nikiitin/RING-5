#!/usr/bin/env python3
"""
Verification script for RING-5 installation and configuration.
Tests core functionality without requiring all dependencies.
"""
import sys
import json
from pathlib import Path


def test_config_validation():
    """Test configuration validation."""
    print("Testing configuration validation...")
    try:
        from src.config.config_manager import ConfigValidator
        
        # Test with template
        with open('templates/config_template.json') as f:
            config = json.load(f)
        
        validator = ConfigValidator()
        validator.validate(config)
        print("  ✓ Configuration validation works")
        return True
    except Exception as e:
        print(f"  ✗ Configuration validation failed: {e}")
        return False


def test_template_generation():
    """Test template generation."""
    print("\nTesting template generation...")
    try:
        from src.config.config_manager import ConfigTemplateGenerator
        
        config = ConfigTemplateGenerator.create_minimal_config(
            "./output",
            "/path/to/stats"
        )
        
        # Add some variables
        ConfigTemplateGenerator.add_variable(config, "simTicks", "scalar")
        ConfigTemplateGenerator.enable_seeds_reducer(config)
        
        # Create a plot
        plot = ConfigTemplateGenerator.create_plot_config(
            "bar", "benchmark", "simTicks", "test_plot",
            title="Test", grid=True
        )
        
        config['plots'].append(plot)
        
        # Validate it
        from src.config.config_manager import ConfigValidator
        validator = ConfigValidator()
        validator.validate(config)
        
        print("  ✓ Template generation works")
        return True
    except Exception as e:
        print(f"  ✗ Template generation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_validation():
    """Test JSON schema validation."""
    print("\nTesting JSON schema...")
    try:
        from src.config.config_manager import ConfigValidator
        
        # Test invalid config
        invalid_config = {
            "outputPath": "./output"
            # Missing required fields
        }
        
        validator = ConfigValidator()
        errors = validator.get_errors(invalid_config)
        
        if len(errors) == 0:
            print("  ✗ Should have detected errors in invalid config")
            return False
        
        print(f"  ✓ Correctly detected {len(errors)} validation errors")
        return True
    except Exception as e:
        print(f"  ✗ Schema validation failed: {e}")
        return False


def test_file_structure():
    """Test that all required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        'ring5.py',
        'app.py',
        'pyproject.toml',
        'requirements.txt',
        'README.md',
        'schemas/config_schema.json',
        'templates/config_template.json',
        'src/config/config_manager.py',
        'src/web/pages/portfolio.py',
        'src/web/pages/manage_plots.py',
        'src/data_management/dataManager.py',
        'src/data_plotter/src/shaper/shaperFactory.py',
        'tests/test_basic.py',
        'tests/test_modularization.py'
    ]
    
    missing = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing.append(file_path)
    
    if missing:
        print("  ✗ Missing files:")
        for f in missing:
            print(f"    - {f}")
        return False
    else:
        print(f"  ✓ All {len(required_files)} required files present")
        return True


def test_dependencies():
    """Check if dependencies are installed."""
    print("\nChecking dependencies...")
    
    required_modules = [
        ('jsonschema', 'JSON Schema validation'),
        ('pandas', 'Data processing'),
        ('numpy', 'Numerical operations'),
        ('matplotlib', 'Plotting'),
        ('seaborn', 'Statistical plotting')
    ]
    
    missing = []
    for module, description in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module:15s} - {description}")
        except ImportError:
            print(f"  ✗ {module:15s} - {description} (NOT INSTALLED)")
            missing.append(module)
    
    if missing:
        print("\n  Install missing dependencies:")
        print(f"  pip install {' '.join(missing)}")
        return False
    else:
        print("\n  ✓ All dependencies installed")
        return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("RING-5 Installation Verification")
    print("=" * 60)
    
    results = {
        'File Structure': test_file_structure(),
        'Dependencies': test_dependencies(),
        'Config Validation': test_config_validation(),
        'Template Generation': test_template_generation(),
        'Schema Validation': test_schema_validation()
    }
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{test_name:20s} : {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n✓ All tests passed!")
        print("\nNext steps:")
        print("  1. Create a configuration:")
        print("     python3 tools/create_config.py")
        print("  2. Or use the template:")
        print("     python3 ring5.py create-template --add-example-plot")
        print("  3. Run analysis:")
        print("     python3 ring5.py analyze --config config.json")
    else:
        print("\n✗ Some tests failed")
        print("\nInstall missing dependencies:")
        print("  pip install -r requirements.txt")
    
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
