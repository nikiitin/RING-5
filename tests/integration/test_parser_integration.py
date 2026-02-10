import os

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
        parse_futures = facade.submit_parse_async(
            stats_path=stats_dir,
            stats_pattern="stats.txt",
            variables=variables,
            output_dir=output_dir,
        )

        # Wait for completion
        parse_results = []
        for future in parse_futures:
            result = future.result(timeout=10)
            if result:
                parse_results.append(result)

        csv_path = facade.finalize_parsing(output_dir, parse_results)
        print(f"Parser finished successfully. CSV: {csv_path}")
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
