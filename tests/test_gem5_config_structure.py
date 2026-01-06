
import os
import unittest
import tempfile
import json
from src.data_parser.stats_scanner import StatsScanner

class TestGem5ConfigStructure(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.stats_file = os.path.join(self.test_dir, "stats.txt")
        self.config_file = os.path.join(self.test_dir, "config.json")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)

    def test_nested_config_matching(self):
        # Gem5 stats often contain short names or full names
        # config.json contains full hierarchy
        
        # Case 1: config.json has "system.cpu.htm_max_retries"
        # stats.txt has "htm_max_retries" (user's case?)
        # OR stats.txt has "system.cpu.htm_max_retries"
        
        # Let's test both scenarios
        
        with open(self.stats_file, "w") as f:
            f.write("standard_scalar 42\n")
            f.write("htm_max_retries 128\n")            # Short name
            f.write("system.cpu.branch_pred 1\n")       # Full name
            f.write("early_value_forwarding 1\n")       # Unique short name

        config_data = {
            "system": {
                "cpu": {
                    "htm_max_retries": 128,
                    "branch_pred": True
                },
                "mem_ctrl": {
                    "early_value_forwarding": True
                }
            }
        }
        
        with open(self.config_file, "w") as f:
            json.dump(config_data, f)

        # Scan
        results = StatsScanner.scan_file(self.stats_file)
        
        def get_type(name):
            for r in results:
                if r["name"] == name:
                    return r["type"]
            return None

        # Assertions
        # 1. Short name matching full config path ending with name
        print(f"htm_max_retries: {get_type('htm_max_retries')}")
        self.assertEqual(get_type("htm_max_retries"), "configuration")
        
        # 2. Full name matching full config path
        print(f"system.cpu.branch_pred: {get_type('system.cpu.branch_pred')}")
        self.assertEqual(get_type('system.cpu.branch_pred'), "configuration")
        
        # 3. Short name matching unique leaf in different branch
        print(f"early_value_forwarding: {get_type('early_value_forwarding')}")
        self.assertEqual(get_type("early_value_forwarding"), "configuration")

if __name__ == "__main__":
    unittest.main()
