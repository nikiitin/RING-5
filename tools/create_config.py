#!/usr/bin/env python3
"""
Quick configuration generator for RING-5.
Interactive script to create configuration files easily.
"""
import json
import sys
from pathlib import Path


def ask(question, default=None):
    """Ask user a question."""
    if default:
        response = input(f"{question} [{default}]: ").strip()
        return response if response else default
    else:
        return input(f"{question}: ").strip()


def ask_yes_no(question, default=True):
    """Ask yes/no question."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{question} [{default_str}]: ").strip().lower()
    
    if not response:
        return default
    
    return response in ['y', 'yes']


def main():
    """Main interactive configuration generator."""
    print("=" * 60)
    print("RING-5 Configuration Generator")
    print("=" * 60)
    print()
    
    # Basic paths
    output_path = ask("Output directory path", "./output")
    stats_path = ask("gem5 stats directory path", "/path/to/gem5/stats")
    
    # Variables
    print("\n--- Variables to Extract ---")
    print("Enter variable names (one per line, empty line to finish)")
    print("Format: name type [rename]")
    print("Types: scalar, vector, distribution, configuration")
    print("Example: simTicks scalar")
    print("Example: system.cpu.ipc scalar ipc")
    print()
    
    variables = []
    while True:
        var_input = input("Variable: ").strip()
        if not var_input:
            break
        
        parts = var_input.split()
        if len(parts) < 2:
            print("  Invalid format. Need: name type [rename]")
            continue
        
        var = {
            "name": parts[0],
            "type": parts[1]
        }
        
        if len(parts) > 2:
            var["rename"] = parts[2]
        
        variables.append(var)
        print(f"  ✓ Added: {var}")
    
    # Add common configuration variables if not already added
    var_names = [v["name"] for v in variables]
    if "benchmark_name" not in var_names:
        if ask_yes_no("Add benchmark_name variable?", True):
            variables.append({"name": "benchmark_name", "type": "configuration"})
    
    if "random_seed" not in var_names:
        if ask_yes_no("Add random_seed variable?", True):
            variables.append({"name": "random_seed", "type": "configuration"})
    
    # Data managers
    print("\n--- Data Managers ---")
    seeds_reducer = ask_yes_no("Enable seeds reducer (combine random seeds)?", True)
    
    outlier_removal = ask_yes_no("Enable outlier removal?", False)
    outlier_config = None
    if outlier_removal:
        column = ask("Column to check for outliers", "simTicks")
        method = ask("Method (iqr or zscore)", "iqr")
        threshold = ask("Threshold", "1.5")
        outlier_config = {
            "enabled": True,
            "column": column,
            "method": method,
            "threshold": float(threshold)
        }
    
    normalize = ask_yes_no("Enable normalization?", False)
    normalize_config = None
    if normalize:
        print("Baseline configuration (key=value pairs, empty to finish):")
        baseline = {}
        while True:
            kv = input("  ").strip()
            if not kv:
                break
            if '=' in kv:
                k, v = kv.split('=', 1)
                baseline[k.strip()] = v.strip()
        
        columns_str = ask("Columns to normalize (comma-separated)", "simTicks")
        columns = [c.strip() for c in columns_str.split(',')]
        
        groupby_str = ask("Group by columns (comma-separated)", "benchmark_name")
        groupby = [c.strip() for c in groupby_str.split(',')]
        
        normalize_config = {
            "enabled": True,
            "baseline": baseline,
            "columns": columns,
            "groupBy": groupby
        }
    
    # Plots
    print("\n--- Plots ---")
    add_plots = ask_yes_no("Add plots interactively?", True)
    
    plots = []
    if add_plots:
        while True:
            print("\nAvailable plot types:")
            print("  bar, line, heatmap, grouped_bar, stacked_bar, box, violin, scatter")
            
            plot_type = ask("Plot type (empty to finish)").strip()
            if not plot_type:
                break
            
            filename = ask("Output filename (no extension)", f"{plot_type}_plot")
            x_var = ask("X-axis variable")
            y_var = ask("Y-axis variable")
            hue_var = ask("Hue/grouping variable (optional)", "")
            
            title = ask("Plot title", "")
            xlabel = ask("X-axis label", "")
            ylabel = ask("Y-axis label", "")
            
            plot = {
                "type": plot_type,
                "output": {
                    "filename": filename,
                    "format": "png",
                    "dpi": 300
                },
                "data": {
                    "x": x_var,
                    "y": y_var
                },
                "style": {
                    "title": title,
                    "xlabel": xlabel,
                    "ylabel": ylabel,
                    "width": 10,
                    "height": 6,
                    "grid": True,
                    "theme": "whitegrid"
                }
            }
            
            if hue_var:
                plot["data"]["hue"] = hue_var
            
            # Ask about aggregation
            if ask_yes_no("Add aggregation?", False):
                method = ask("Aggregation method (mean/median/geomean/sum)", "mean")
                groupby_str = ask("Group by (comma-separated)")
                groupby = [c.strip() for c in groupby_str.split(',')]
                
                plot["data"]["aggregate"] = {
                    "method": method,
                    "groupBy": groupby
                }
            
            plots.append(plot)
            print(f"  ✓ Plot added: {filename}")
    
    # Build configuration
    config = {
        "outputPath": output_path,
        "parseConfig": {
            "parser": "gem5_stats",
            "statsPath": stats_path,
            "statsPattern": "**/stats.txt",
            "compress": False,
            "variables": variables
        },
        "dataManagers": {
            "seedsReducer": seeds_reducer
        },
        "plots": plots
    }
    
    if outlier_config:
        config["dataManagers"]["outlierRemover"] = outlier_config
    
    if normalize_config:
        config["dataManagers"]["normalizer"] = normalize_config
    
    # Save configuration
    print("\n--- Save Configuration ---")
    config_file = ask("Configuration filename", "config.json")
    
    config_path = Path(config_file)
    if config_path.exists():
        if not ask_yes_no(f"File {config_file} exists. Overwrite?", False):
            print("Cancelled.")
            return
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print()
    print("=" * 60)
    print(f"✓ Configuration saved to: {config_path}")
    print()
    print("Next steps:")
    print(f"  1. Validate: python ring5.py validate --config {config_file}")
    print(f"  2. Run analysis: python ring5.py analyze --config {config_file}")
    print("=" * 60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        sys.exit(1)
