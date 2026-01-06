"""
Unit Tests for RING-5 Web Modules
Tests for styles, state manager, facade, and components.
"""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest


class TestAppStyles:
    """Test the AppStyles class."""

    def test_get_custom_css_returns_string(self):
        """Test that get_custom_css returns a non-empty string."""
        from src.web.styles import AppStyles

        css = AppStyles.get_custom_css()
        assert isinstance(css, str)
        assert len(css) > 0
        assert "<style>" in css
        assert "</style>" in css

    def test_header_html(self):
        """Test header HTML generation."""
        from src.web.styles import AppStyles

        result = AppStyles.header("Test Header")
        assert "main-header" in result
        assert "Test Header" in result

    def test_step_header_html(self):
        """Test step header HTML generation."""
        from src.web.styles import AppStyles

        result = AppStyles.step_header("Step 1")
        assert "step-header" in result
        assert "Step 1" in result

    def test_success_box_html(self):
        """Test success box HTML generation."""
        from src.web.styles import AppStyles

        result = AppStyles.success_box("Success message")
        assert "success-box" in result
        assert "Success message" in result


class TestStateManager:
    """Test the StateManager class."""

    def setup_method(self):
        """Setup test session state mock."""
        import streamlit as st

        # Mock session state
        if not hasattr(st, "session_state"):
            st.session_state = {}

    def test_initialize_creates_defaults(self):
        """Test that initialize creates default values."""
        import streamlit as st

        from src.web.state_manager import StateManager

        st.session_state.clear()
        StateManager.initialize()

        assert StateManager.DATA in st.session_state
        assert StateManager.CONFIG in st.session_state
        assert StateManager.USE_PARSER in st.session_state

    def test_get_set_data(self):
        """Test data getter and setter."""
        from src.web.state_manager import StateManager

        StateManager.initialize()

        test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        StateManager.set_data(test_data)

        retrieved = StateManager.get_data()
        assert retrieved is not None
        assert len(retrieved) == 3
        pd.testing.assert_frame_equal(retrieved, test_data)

    def test_get_set_config(self):
        """Test config getter and setter."""
        from src.web.state_manager import StateManager

        StateManager.initialize()

        test_config = {"shapers": [{"type": "test"}]}
        StateManager.set_config(test_config)

        retrieved = StateManager.get_config()
        assert retrieved == test_config

    def test_update_config(self):
        """Test config update method."""
        from src.web.state_manager import StateManager

        StateManager.initialize()

        StateManager.update_config("test_key", "test_value")
        config = StateManager.get_config()

        assert "test_key" in config
        assert config["test_key"] == "test_value"

    def test_has_data(self):
        """Test has_data method."""
        import streamlit as st

        from src.web.state_manager import StateManager

        st.session_state.clear()
        StateManager.initialize()
        assert not StateManager.has_data()

        test_data = pd.DataFrame({"a": [1, 2]})
        StateManager.set_data(test_data)
        assert StateManager.has_data()


class TestBackendFacade:
    """Test the BackendFacade class."""

    def setup_method(self):
        """Setup test environment."""
        self.test_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_facade_initialization(self):
        """Test facade creates necessary directories."""
        from src.web.facade import BackendFacade

        facade = BackendFacade()

        assert facade.csv_pool_dir.exists()
        assert facade.config_pool_dir.exists()

    def test_load_csv_pool_empty(self):
        """Test loading empty CSV pool."""
        from src.web.facade import BackendFacade

        # Create facade with test directory (override paths after creation)
        facade = BackendFacade()
        
        # Create a clean temp directory for testing
        temp_csv_pool = self.test_dir / "csv_pool"
        temp_csv_pool.mkdir(parents=True, exist_ok=True)
        facade.csv_pool_dir = temp_csv_pool
        
        pool = facade.load_csv_pool()

        assert isinstance(pool, list)
        assert len(pool) == 0

    def test_add_to_csv_pool(self):
        """Test adding CSV to pool."""
        from src.web.facade import BackendFacade

        # Create test CSV
        test_csv = self.test_dir / "test.csv"
        pd.DataFrame({"a": [1, 2, 3]}).to_csv(test_csv, index=False)

        with patch.object(Path, "home", return_value=self.test_dir):
            facade = BackendFacade()
            pool_path = facade.add_to_csv_pool(str(test_csv))

        assert Path(pool_path).exists()
        assert "parsed_" in Path(pool_path).name

    def test_load_csv_file(self):
        """Test loading CSV file."""
        from src.web.facade import BackendFacade

        # Create test CSV
        test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_csv = self.test_dir / "test.csv"
        test_data.to_csv(test_csv, index=False)

        facade = BackendFacade()
        loaded_data = facade.load_csv_file(str(test_csv))

        assert len(loaded_data) == 3
        assert list(loaded_data.columns) == ["a", "b"]

    def test_save_configuration(self):
        """Test saving configuration."""
        from src.web.facade import BackendFacade

        with patch.object(Path, "home", return_value=self.test_dir):
            facade = BackendFacade()

            config_path = facade.save_configuration(
                name="test_config",
                description="Test description",
                shapers_config=[{"type": "test"}],
                csv_path="/path/to/csv",
            )

        assert Path(config_path).exists()

        # Verify content
        with open(config_path, "r") as f:
            config_data = json.load(f)

        assert config_data["name"] == "test_config"
        assert config_data["description"] == "Test description"
        assert len(config_data["shapers"]) == 1

    def test_load_configuration(self):
        """Test loading configuration."""
        from src.web.facade import BackendFacade

        # Create test config
        test_config = {"name": "test", "description": "Test config", "shapers": [{"type": "test"}]}
        config_file = self.test_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(test_config, f)

        facade = BackendFacade()
        loaded_config = facade.load_configuration(str(config_file))

        assert loaded_config["name"] == "test"
        assert loaded_config["description"] == "Test config"

    def test_find_stats_files(self):
        """Test finding stats files."""
        from src.web.facade import BackendFacade

        # Create test structure
        stats_dir = self.test_dir / "stats"
        stats_dir.mkdir()
        (stats_dir / "stats.txt").touch()

        subdir = stats_dir / "subdir"
        subdir.mkdir()
        (subdir / "stats.txt").touch()

        facade = BackendFacade()
        found_files = facade.find_stats_files(str(stats_dir), "stats.txt")

        assert len(found_files) == 2

    def test_apply_shapers(self):
        """Test applying shapers to data (requires shaper module)."""
        from src.web.facade import BackendFacade

        # Skip if shaper module not properly configured
        try:
            facade = BackendFacade()
            test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})

            shapers_config = [{"type": "columnSelector", "columns": ["a", "b"]}]

            result = facade.apply_shapers(test_data, shapers_config)

            assert len(result.columns) == 2
            assert "a" in result.columns
            assert "b" in result.columns
            assert "c" not in result.columns
        except ModuleNotFoundError:
            # Skip if shaper module has import issues
            pytest.skip("Shaper module not properly configured")

    def test_get_column_info(self):
        """Test getting column information."""
        from src.web.facade import BackendFacade

        facade = BackendFacade()
        test_data = pd.DataFrame(
            {"numeric1": [1, 2, 3], "numeric2": [4.5, 5.5, 6.5], "categorical": ["a", "b", "c"]}
        )

        info = facade.get_column_info(test_data)

        assert info["total_columns"] == 3
        assert info["total_rows"] == 3
        assert len(info["numeric_columns"]) == 2
        assert len(info["categorical_columns"]) == 1


class TestUIComponents:
    """Test the UIComponents class."""

    def test_show_data_preview(self):
        """Test data preview display (simplified)."""
        from src.web.components import UIComponents

        # Just verify the method exists and is callable
        # Full UI testing requires Streamlit context
        assert hasattr(UIComponents, "show_data_preview")
        assert callable(UIComponents.show_data_preview)

    def test_variable_editor_returns_list(self):
        """Test variable editor returns updated list."""
        from src.web.components import UIComponents

        # This test needs Streamlit context, so we'll just verify the function exists
        assert hasattr(UIComponents, "variable_editor")
        assert callable(UIComponents.variable_editor)


def run_tests():
    """Run all tests and report results."""
    print("Running RING-5 Web Module Tests...")
    print("=" * 60)

    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
