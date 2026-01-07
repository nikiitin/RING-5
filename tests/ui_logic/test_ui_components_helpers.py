
import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
from src.web.components import UIComponents

@pytest.fixture
def mock_streamlit():
    with patch("src.web.components.st") as mock_st:
        mock_st.session_state = {}
        
        # Mock columns to return list of mocks
        def columns_side_effect(spec, **kwargs):
            if isinstance(spec, int):
                return [MagicMock() for _ in range(spec)]
            elif isinstance(spec, (list, tuple)):
                return [MagicMock() for _ in range(len(spec))]
            return [MagicMock()]
        mock_st.columns.side_effect = columns_side_effect
        
        # Mock expander
        mock_st.expander.return_value.__enter__.return_value = MagicMock()
        
        # Mock button defaults
        mock_st.button.return_value = False
        
        yield mock_st

@pytest.fixture
def mock_facade():
    with patch("src.web.components.BackendFacade") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance

def test_show_data_preview(mock_streamlit):
    df = pd.DataFrame({"A": [1, 2], "B": ["x", "y"]})
    UIComponents.show_data_preview(df)
    
    mock_streamlit.dataframe.assert_called()
    mock_streamlit.metric.assert_called()

def test_file_info_card(mock_streamlit):
    info = {"name": "test.csv", "size": 1024, "modified": 1600000000}
    
    # Mock button clicks
    mock_streamlit.button.side_effect = [True, False, False] # Load clicked
    
    load, preview, delete = UIComponents.file_info_card(info, 0)
    
    assert load is True
    assert preview is False
    assert delete is False
    mock_streamlit.expander.assert_called()

def test_variable_editor_render_existing(mock_streamlit):
    vars_config = [{"name": "v1", "type": "scalar", "_id": "1"}]
    
    # Setup inputs
    mock_streamlit.text_input.side_effect = ["v1", "ali"] # Name, Alias
    mock_streamlit.selectbox.return_value = "scalar"
    
    updated = UIComponents.variable_editor(vars_config)
    
    assert len(updated) == 1
    assert updated[0]["name"] == "v1"
    assert updated[0]["alias"] == "ali"
    assert updated[0]["type"] == "scalar"

def test_variable_editor_add_manual(mock_streamlit):
    vars_config = []
    
    # Button clicks: X (delete) -> False, Add Selected -> False, Add Manual -> True
    mock_streamlit.button.side_effect = lambda label, **k: label == "+ Add Manual"
    
    # Rerun should be called
    UIComponents.variable_editor(vars_config)
    
    assert len(vars_config) == 1
    assert vars_config[0]["name"] == "new_variable"
    mock_streamlit.rerun.assert_called()

def test_variable_editor_deep_scan(mock_streamlit, mock_facade):
    vars_config = [{"name": "vec", "type": "vector", "_id": "1"}]
    
    # Inputs:
    # 1. Name ("vec")
    # 2. Alias ("")
    # 3. Type ("vector")
    
    # 4. Radio Entry Mode -> "Select from Discovered Entries" (to trigger logic checks)
    # Actually logic depends on stats_path etc.
    
    # Helper for side effects is tricky because of loop.
    # We'll mock specific calls if possible or allow loose matching.
    
    mock_streamlit.text_input.return_value = "vec"
    mock_streamlit.selectbox.return_value = "vector"
    
    # Trigger Deep Scan path: requires stats_path, no discovered entries, manual entry mode?
    # Or "Select from Discovered Entries" + Button
    
    # Let's say entry_mode = "Select from Discovered Entries"
    mock_streamlit.radio.return_value = "Select from Discovered Entries"
    
    # Deep Scan Button -> True
    # We need to distinguish buttons.
    # Button keys: delete_var_.., deep_scan_.., add_selected.., add_manual..
    def button_side_effect(label, key=None, **kwargs):
        if key and key.startswith("deep_scan"):
            return True
        return False
    mock_streamlit.button.side_effect = button_side_effect
    
    # Mock Facade
    mock_facade.scan_vector_entries.return_value = ["e1", "e2"]
    
    UIComponents.variable_editor(
        vars_config, 
        available_variables=[], 
        stats_path="/path"
    )
    
    mock_facade.scan_vector_entries.assert_called_with("/path", "vec", "stats.txt")
    # Execution continues because mock rerun doesn't stop it, so we check ANY call
    mock_streamlit.success.assert_any_call("Found 2 entries!")
    mock_streamlit.rerun.assert_called()

def test_variable_editor_vector_stats_checkboxes(mock_streamlit):
    vars_config = [{"name": "vec", "type": "vector", "_id": "1", "vectorEntries": []}]
    
    mock_streamlit.text_input.return_value = "vec"
    mock_streamlit.selectbox.return_value = "vector"
    mock_streamlit.radio.return_value = "Vector Statistics"
    
    # Checkboxes: total=True, mean=False
    def checkbox_side_effect(label, **kwargs):
        if "total" in label: return True
        return False
    mock_streamlit.checkbox.side_effect = checkbox_side_effect
    
    updated = UIComponents.variable_editor(vars_config)
    
    assert updated[0]["useSpecialMembers"] is True
    assert updated[0]["vectorEntries"] == ["total"]
