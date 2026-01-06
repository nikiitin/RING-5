import os
import sys

# Add src to path
sys.path.insert(0, os.getcwd())

from src.web.facade import BackendFacade


def test_parser_integration():
    facade = BackendFacade()

    # Mock variables
    variables = [
        {
            "name": "test_vector",
            "type": "vector",
            "vectorEntries": ["entry1", "entry2"],
            "useSpecialMembers": False,
        }
    ]

    # Create dummy stats file
    stats_dir = "test_stats_dir"
    os.makedirs(stats_dir, exist_ok=True)
    with open(f"{stats_dir}/stats.txt", "w") as f:
        f.write("test_vector::entry1 100\n")
        f.write("test_vector::entry2 200\n")

    output_dir = "test_output"
    os.makedirs(output_dir, exist_ok=True)

    try:
        print("Running parser integration test...")
        facade.parse_gem5_stats(
            stats_path=stats_dir,
            stats_pattern="stats.txt",
            compress=False,
            variables=variables,
            output_dir=output_dir,
        )
        print("Parser finished successfully.")
    except Exception as e:
        print(f"Parser failed: {e}")
    finally:
        # Cleanup
        import shutil

        if os.path.exists(stats_dir):
            shutil.rmtree(stats_dir)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir)


if __name__ == "__main__":
    test_parser_integration()
