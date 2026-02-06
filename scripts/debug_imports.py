try:
    print("Importing src.web.ui.plotting...")

    print("SUCCESS: BasePlot imported")
except Exception:
    import traceback

    print("FAILED: BasePlot import failed")
    traceback.print_exc()

try:
    print("\nImporting src.web.state_manager...")

    print("SUCCESS: StateManager imported")
except Exception:
    import traceback

    print("FAILED: StateManager import failed")
    traceback.print_exc()

try:
    print("\nImporting app.py...")

    print("SUCCESS: app.py imported")
except Exception:
    import traceback

    print("FAILED: app.py import failed")
    traceback.print_exc()
