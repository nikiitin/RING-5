try:
    print("Importing src.web.pages.ui.plotting...")
    from src.web.pages.ui.plotting.base_plot import BasePlot  # noqa: F401

    print("SUCCESS: BasePlot imported")
except Exception:
    import traceback

    print("FAILED: BasePlot import failed")
    traceback.print_exc()

try:
    print("\nImporting src.core.state.state_manager...")
    import src.core.state.state_manager  # noqa: F401

    print("SUCCESS: StateManager imported")
except Exception:
    import traceback

    print("FAILED: StateManager import failed")
    traceback.print_exc()

try:
    print("\nImporting app.py...")
    import app  # noqa: F401

    print("SUCCESS: app.py imported")
except Exception:
    import traceback

    print("FAILED: app.py import failed")
    traceback.print_exc()
