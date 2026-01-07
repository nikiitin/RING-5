import os
import sys

# Add src to path
sys.path.insert(0, os.getcwd())

from src.parsing.stats_scanner import StatsScanner


def create_dummy_stats(filename):
    with open(filename, "w") as f:
        f.write("--- Begin Simulation Statistics ---\n")
        f.write("simTicks 1000 # Number of ticks\n")
        f.write("system.cpu.ipc 1.5 # IPC\n")
        f.write("system.cpu.dcache.overall_misses::total 500 # Total misses\n")
        f.write("system.cpu.dcache.overall_misses::cpu0 250 # Misses for cpu0\n")
        f.write("system.mem_ctrl.dram.rank0.averagePower 10.5 # Average power\n")
        f.write("system.config.param=value\n")
        f.write("system.dist::mean 5.5 10% 10% # Distribution mean\n")


def test_scanner():
    filename = "test_stats.txt"
    create_dummy_stats(filename)

    try:
        vars_found = StatsScanner.scan_file(filename)
        print(f"Found {len(vars_found)} variables.")

        expected = {
            "simTicks": "scalar",
            "system.cpu.ipc": "scalar",
            "system.cpu.dcache.overall_misses": "vector",
            "system.mem_ctrl.dram.rank0.averagePower": "scalar",
            "system.config.param": "configuration",
            "system.dist": "distribution",  # or vector depending on regex precedence
        }

        for v in vars_found:
            name = v["name"]
            vtype = v["type"]
            print(f"  {name}: {vtype}")

            if name in expected:
                if expected[name] != vtype:
                    print(f"ERROR: Expected {expected[name]} for {name}, got {vtype}")
                else:
                    print(f"OK: {name}")
            else:
                print(f"Unexpected variable: {name}")

            if "entries" in v:
                print(f"    Entries: {v['entries']}")

    finally:
        if os.path.exists(filename):
            os.remove(filename)


if __name__ == "__main__":
    test_scanner()
