#!/usr/bin/env python3
"""
Verification script for RING-5 installation and configuration.
Tests core functionality without requiring all dependencies.
"""

import json
import sys
from pathlib import Path


def test_config_validation():
    """Test configuration validation."""
    print("Testing configuration validation...")
    try:
        from src.core.models.config.config_manager import ConfigValidator

        # Test with template
        with open("templates/config_template.json") as f:
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
        from src.core.models.config.config_manager import ConfigTemplateGenerator

        config = ConfigTemplateGenerator.create_minimal_config("./output", "/path/to/stats")

        # Add some variables
        ConfigTemplateGenerator.add_variable(config, "simTicks", "scalar")
        ConfigTemplateGenerator.enable_seeds_reducer(config)

        # Create a plot
        plot = ConfigTemplateGenerator.create_plot_config(
            "bar", "benchmark", "simTicks", "test_plot", title="Test", grid=True
        )

        config["plots"].append(plot)

        # Validate it
        from src.core.models.config.config_manager import ConfigValidator

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
        from src.core.models.config.config_manager import ConfigValidator

        # Test invalid config
        invalid_config = {
            "outputPath": "./output"
            # Missing required fields
        }

        validator = ConfigValidator()
        validation_failed = False
        try:
            validator.validate(invalid_config)
        except Exception:
            # Expected failure - invalid config should raise validation error
            validation_failed = True

        if not validation_failed:
            print("  ✗ Schema validation did not raise exception for invalid config")
            return False

    except Exception as e:
        print(f"  ✗ Unexpected error during validation test: {e}")
        return False

    # Test valid config logic is already covered by test_config_validation
    print("  ✓ Schema validation logic works")
    return True


def test_file_structure():
    """Test that all required files exist."""
    print("\nTesting file structure...")

    required_files = [
        "app.py",
        "pyproject.toml",
        "README.md",
        "src/core/models/config/schemas/parser_config_schema.json",
        "src/web/pages/ui/plotting/export/presets/latex_presets.yaml",
        "src/core/models/config/config_manager.py",
        "src/web/pages/portfolio.py",
        "src/web/pages/ui/data_managers/data_manager.py",
        "tests/unit/test_web_modules.py",
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
        ("jsonschema", "JSON Schema validation"),
        ("pandas", "Data processing"),
        ("numpy", "Numerical operations"),
        ("plotly", "Interactive plotting"),
        ("streamlit", "Web framework"),
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


def test_latex_dependencies():
    """Check if LaTeX system packages are installed (for export feature)."""
    print("\nChecking LaTeX dependencies (for export feature)...")
    import shutil
    import subprocess  # nosec B404 - Needed to check LaTeX installation

    checks = [
        ("latex", "LaTeX engine (pdflatex)", "Basic PDF export"),
        ("xelatex", "XeLaTeX engine", "PGF format export"),
    ]

    all_good = True
    for command, name, purpose in checks:
        if shutil.which(command):
            try:
                result = subprocess.run(  # nosec B603 B607 - System LaTeX tools
                    [command, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                version = result.stdout.split("\n")[0]
                print(f"  ✓ {name:25s} - {purpose}")
                print(f"    {version}")
            except Exception as e:
                print(f"  ⚠ {name:25s} - Found but cannot verify: {e}")
        else:
            print(f"  ✗ {name:25s} - {purpose} (NOT INSTALLED)")
            all_good = False

    # Check for cm-super package (type1ec.sty)
    if shutil.which("kpsewhich"):
        try:
            result = subprocess.run(  # nosec B603 B607 - TeX Live system tool
                ["kpsewhich", "type1ec.sty"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                print(f"  ✓ {'cm-super package':25s} - Type 1 fonts for LaTeX")
            else:
                print(f"  ✗ {'cm-super package':25s} - Type 1 fonts (NOT INSTALLED)")
                all_good = False
        except Exception:
            print(f"  ⚠ {'cm-super package':25s} - Cannot verify")
    else:
        print(f"  ⚠ {'cm-super package':25s} - Cannot verify (kpsewhich not found)")

    if not all_good:
        print("\n  ⚠️  LaTeX export features will not work without these packages")
        print("\n  Install with:")
        print("    make install-latex")
        print("  Or manually:")
        print("    sudo apt-get install texlive-latex-base texlive-fonts-recommended \\")
        print("                         texlive-fonts-extra cm-super texlive-xetex")
        print("\n  📖 See docs/LaTeX-Export-Guide.md for details")
        return False
    else:
        print("\n  ✓ All LaTeX dependencies installed")
        return True


def main():
    """Run all verification tests."""
    print("=" * 60)
    print("RING-5 Installation Verification")
    print("=" * 60)

    results = {
        "File Structure": test_file_structure(),
        "Dependencies": test_dependencies(),
        "LaTeX Dependencies": test_latex_dependencies(),
        "Config Validation": test_config_validation(),
        "Template Generation": test_template_generation(),
        "Schema Validation": test_schema_validation(),
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
        print("  1. Start the web application:")
        print("     streamlit run app.py")
        print("  2. Or use the launcher:")
        print("     ./launch_webapp.sh")
        print("  3. Open browser to: http://localhost:8501")
    else:
        print("\n✗ Some tests failed")
        print("\nInstall missing dependencies:")
        print("  Python packages: pip install -r requirements.txt")
        print("  LaTeX packages:  make install-latex")

    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
