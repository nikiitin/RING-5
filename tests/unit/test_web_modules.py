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


class TestStateManager:
    """Test the StateManager class."""

    @pytest.fixture
    def mock_session_state(self):
        """Mock streamlit.session_state as a dictionary."""
        with patch("streamlit.session_state", new_callable=dict) as mock_state:
            yield mock_state

    def test_initialize_creates_defaults(self, mock_session_state):
        """Test that initialize creates default values."""
        from src.core.state.state_manager import StateManager

        # StateManager() instantiation triggers SessionRepository.initialize_session()
        mgr = StateManager()

        # Check via public API instead of accessing implementation details
        # The Pure Python repositories store state in instance variables, not session_state directly

        # Parser variables are initialized by default
        assert len(mgr.get_parse_variables()) > 0

        # Data starts empty
        assert not mgr.has_data()
        assert mgr.get_data() is None

    def test_get_set_data(self, mock_session_state):
        """Test data getter and setter."""
        from src.core.state.state_manager import StateManager

        mgr = StateManager()

        test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        mgr.set_data(test_data)

        retrieved = mgr.get_data()
        assert retrieved is not None
        assert len(retrieved) == 3
        pd.testing.assert_frame_equal(retrieved, test_data)

    def test_get_set_config(self, mock_session_state):
        """Test config getter and setter."""
        from src.core.state.state_manager import StateManager

        mgr = StateManager()

        test_config = {"shapers": [{"type": "test"}]}
        mgr.set_config(test_config)

        retrieved = mgr.get_config()
        assert retrieved == test_config

    def test_update_config(self, mock_session_state):
        """Test config update method."""
        from src.core.state.state_manager import StateManager

        mgr = StateManager()

        mgr.update_config("test_key", "test_value")
        config = mgr.get_config()

        assert "test_key" in config
        assert config["test_key"] == "test_value"

    def test_has_data(self, mock_session_state):
        """Test has_data method."""
        from src.core.state.state_manager import StateManager

        mgr = StateManager()
        assert not mgr.has_data()

        test_data = pd.DataFrame({"a": [1, 2]})
        mgr.set_data(test_data)
        assert mgr.has_data()


class TestApplicationAPI:
    """Test the ApplicationAPI class."""

    def setup_method(self):
        """Setup test environment."""
        self.test_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Cleanup test environment."""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_api_initialization(self):
        """Test API initializes services."""
        from src.core.application_api import ApplicationAPI

        api = ApplicationAPI()

        # Check services initialized
        assert api.state_manager is not None
        assert api.portfolio_service is not None

        # Check CsvPoolService access (static service)
        # API doesn't allow direct property access to csv_pool_dir by default but uses service
        # We check functionality instead of internal properties

    def test_load_csv_pool_empty(self):
        """Test loading empty CSV pool."""
        from unittest.mock import patch

        from src.core.application_api import ApplicationAPI

        # Create a clean temp directory for testing
        temp_csv_pool = self.test_dir / "csv_pool"
        temp_csv_pool.mkdir(parents=True, exist_ok=True)

        # Patch PathService to use temp directory
        with patch(
            "src.core.services.csv_pool_service.PathService.get_data_dir",
            return_value=self.test_dir,
        ):
            # ApplicationAPI uses CsvPoolService.load_pool
            api = ApplicationAPI()

            # Since CsvPoolService relies on PathService, and we patched it,
            # we need to ensure CsvPoolService uses 'csv_pool' subdir of data_dir
            # (CsvPoolService implementation detail: data_dir / "csv_pool")

            pool = api.load_csv_pool()

            assert isinstance(pool, list)
            assert len(pool) == 0

    def test_add_to_csv_pool(self):
        """Test adding CSV to pool."""
        from src.core.application_api import ApplicationAPI

        # Create test CSV
        test_csv = self.test_dir / "test.csv"
        pd.DataFrame({"a": [1, 2, 3]}).to_csv(test_csv, index=False)

        with patch(
            "src.core.services.csv_pool_service.PathService.get_data_dir",
            return_value=self.test_dir,
        ):
            api = ApplicationAPI()
            pool_path = api.add_to_csv_pool(str(test_csv))

        assert Path(pool_path).exists()
        assert "parsed_" in Path(pool_path).name

    def test_load_csv_file(self):
        """Test loading CSV file."""
        from src.core.application_api import ApplicationAPI

        # Create test CSV
        test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        test_csv = self.test_dir / "test.csv"
        test_data.to_csv(test_csv, index=False)

        api = ApplicationAPI()
        # load_csv_file is static service call wrapper
        loaded_data = api.load_csv_file(str(test_csv))

        assert len(loaded_data) == 3
        assert list(loaded_data.columns) == ["a", "b"]

    def test_save_configuration(self):
        """Test saving configuration."""
        from src.core.application_api import ApplicationAPI

        api = ApplicationAPI()
        # Mock config_pool_dir property or ensure it uses patched home
        # ApplicationAPI.save_configuration uses self.config_pool_dir OR Path.home()/.ring5/configs
        # We can patch Path.home to use self.test_dir

        with patch.object(Path, "home", return_value=self.test_dir):
            config_path = api.save_configuration(
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
        from src.core.application_api import ApplicationAPI

        # Create test config
        test_config = {"name": "test", "description": "Test config", "shapers": [{"type": "test"}]}
        config_file = self.test_dir / "config.json"
        with open(config_file, "w") as f:
            json.dump(test_config, f)

        api = ApplicationAPI()
        loaded_config = api.load_configuration(str(config_file))

        assert loaded_config["name"] == "test"
        assert loaded_config["description"] == "Test config"

    def test_find_stats_files(self):
        """Test finding stats files."""
        from src.core.application_api import ApplicationAPI

        # Create test structure
        stats_dir = self.test_dir / "stats"
        stats_dir.mkdir()
        (stats_dir / "stats.txt").touch()

        subdir = stats_dir / "subdir"
        subdir.mkdir()
        (subdir / "stats.txt").touch()

        api = ApplicationAPI()
        found_files = api.find_stats_files(str(stats_dir), "stats.txt")

        assert len(found_files) == 2

    def test_apply_shapers(self):
        """Test applying shapers to data (requires shaper module)."""
        from src.core.application_api import ApplicationAPI

        # Skip if shaper module not properly configured
        try:
            api = ApplicationAPI()
            test_data = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6], "c": [7, 8, 9]})

            shapers_config = [{"type": "columnSelector", "columns": ["a", "b"]}]

            result = api.apply_shapers(test_data, shapers_config)

            assert len(result.columns) == 2
            assert "a" in result.columns
            assert "b" in result.columns
            assert "c" not in result.columns
        except ModuleNotFoundError:
            # Skip if shaper module has import issues
            pytest.skip("Shaper module not properly configured")

    def test_get_column_info(self):
        """Test getting column information."""
        from src.core.application_api import ApplicationAPI

        api = ApplicationAPI()
        test_data = pd.DataFrame(
            {"numeric1": [1, 2, 3], "numeric2": [4.5, 5.5, 6.5], "categorical": ["a", "b", "c"]}
        )

        info = api.get_column_info(test_data)

        assert info["total_columns"] == 3
        assert info["total_rows"] == 3
        assert len(info["numeric_columns"]) == 2
        assert len(info["categorical_columns"]) == 1


class TestUIComponents:
    """Test the UI Components."""

    def test_data_components_preview(self):
        """Test DataComponents.show_data_preview exist."""
        from src.web.pages.ui.components.data_components import DataComponents

        assert hasattr(DataComponents, "show_data_preview")
        assert callable(DataComponents.show_data_preview)

    def test_variable_editor_exists(self):
        """Test VariableEditor.render exists."""
        from src.web.pages.ui.components.variable_editor import VariableEditor

        assert hasattr(VariableEditor, "render")
        assert callable(VariableEditor.render)

    def test_variable_editor_histogram_support(self):
        """Test VariableEditor supports histogram configuration."""
        from unittest.mock import MagicMock

        from src.core.application_api import ApplicationAPI
        from src.web.pages.ui.components.variable_editor import VariableEditor

        assert hasattr(VariableEditor, "render_histogram_config")

        # Mock API
        mock_api = MagicMock(spec=ApplicationAPI)

        # Mock st
        with patch("src.web.pages.ui.components.variable_editor.st") as mock_st:
            mock_st.columns.side_effect = [
                [MagicMock(), MagicMock(), MagicMock(), MagicMock()],
                [MagicMock(), MagicMock()],
            ]
            variables = [{"name": "test_hist", "type": "histogram"}]
            # Pass mock API
            VariableEditor.render(mock_api, variables)


def run_tests():
    """Run all tests and report results."""
    print("Running RING-5 Web Module Tests...")
    print("=" * 60)

    # Run pytest
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
