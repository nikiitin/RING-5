"""
Simplified RING-5 main entry point.
Pure Python implementation for gem5 data analysis and visualization.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Any

from src.config.config_manager import ConfigValidator, ConfigTemplateGenerator
from src.data_management.dataManagerFactory import DataManagerFactory
from src.data_management.dataManager import DataManager
from src.plotting.plot_engine import PlotManager


class RING5Analyzer:
    """Main analyzer class for RING-5."""
    
    def __init__(self, config_path: str):
        """
        Initialize analyzer with configuration file.
        
        Args:
            config_path: Path to JSON configuration file
        """
        self.config_path = config_path
        self.config = self._load_and_validate_config()
        
        self.output_dir = Path(self.config['outputPath'])
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.csv_path = self.output_dir / "results.csv"
        self.work_csv = Path("/tmp/ring5_work.csv")
    
    def _load_and_validate_config(self) -> Dict[str, Any]:
        """Load and validate configuration file."""
        print(f"Loading configuration from: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        
        # Validate configuration
        try:
            validator = ConfigValidator()
            validator.validate(config)
            print("✓ Configuration is valid")
        except Exception as e:
            print(f"✗ Configuration validation failed: {e}")
            errors = validator.get_errors(config)
            if errors:
                print("\nValidation errors:")
                for error in errors:
                    print(f"  - {error}")
            sys.exit(1)
        
        return config
    
    def parse_data(self, skip_parse: bool = False):
        """
        Parse gem5 stats files.
        
        Args:
            skip_parse: Skip parsing if CSV already exists
        """
        if skip_parse and self.csv_path.exists():
            print(f"Skipping parse, using existing CSV: {self.csv_path}")
            return
        
        print("\n=== Parsing gem5 stats files ===")
        
        # TODO: Implement gem5 stats parser
        # For now, check if CSV exists
        if not self.csv_path.exists():
            print(f"ERROR: CSV file not found: {self.csv_path}")
            print("Please run data parsing first or provide a CSV file.")
            sys.exit(1)
    
    def manage_data(self):
        """Apply data management operations."""
        print("\n=== Processing data ===")
        
        # Copy CSV to work file
        import shutil
        shutil.copy(self.csv_path, self.work_csv)
        print(f"Working with temporary CSV: {self.work_csv}")
        
        # Get data managers from configuration
        data_managers_config = self.config.get('dataManagers', {})
        
        if not data_managers_config:
            print("No data managers configured")
            return
        
        # Create a minimal AnalyzerInfo-like object for compatibility
        class ConfigAdapter:
            def __init__(self, work_csv, config):
                self._work_csv = work_csv
                self._config = config
            
            def getWorkCsv(self):
                return str(self._work_csv)
            
            def getCategoricalColumns(self):
                # Will be populated by DataManager
                return []
        
        info = ConfigAdapter(self.work_csv, self.config)
        
        # Get and execute data managers
        managers = DataManagerFactory.getDataManager(info, data_managers_config)
        
        if managers:
            print(f"Executing {len(managers)} data manager(s)")
            for manager in managers:
                manager()
            DataManager.persist()
            print("✓ Data management complete")
        else:
            print("No data managers to execute")
    
    def generate_plots(self):
        """Generate plots from configuration."""
        print("\n=== Generating plots ===")
        
        plots_config = self.config.get('plots', [])
        
        if not plots_config:
            print("No plots configured")
            return
        
        # Create plot manager
        plot_manager = PlotManager(
            str(self.work_csv),
            str(self.output_dir / "plots")
        )
        
        # Generate all plots
        plot_manager.generate_plots(plots_config)
        print("✓ Plot generation complete")
    
    def run(self, skip_parse: bool = False):
        """
        Run the complete analysis pipeline.
        
        Args:
            skip_parse: Skip data parsing step
        """
        print("=" * 60)
        print("RING-5: gem5 Data Analyzer")
        print("=" * 60)
        
        try:
            # Parse data
            self.parse_data(skip_parse)
            
            # Manage data
            self.manage_data()
            
            # Generate plots
            self.generate_plots()
            
            print("\n" + "=" * 60)
            print("✓ Analysis complete!")
            print(f"Output directory: {self.output_dir}")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n✗ Error during analysis: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
        
        finally:
            # Cleanup
            if self.work_csv.exists():
                self.work_csv.unlink()


def create_template_command(args):
    """Create a configuration template."""
    print("Creating configuration template...")
    
    config = ConfigTemplateGenerator.create_minimal_config(
        args.output_path,
        args.stats_path
    )
    
    # Add some example variables
    ConfigTemplateGenerator.add_variable(config, "simTicks", "scalar")
    ConfigTemplateGenerator.add_variable(config, "benchmark_name", "configuration")
    ConfigTemplateGenerator.add_variable(config, "config_description", "configuration")
    ConfigTemplateGenerator.add_variable(config, "random_seed", "configuration")
    
    # Enable seeds reducer
    if args.seeds_reducer:
        ConfigTemplateGenerator.enable_seeds_reducer(config)
    
    # Add example plot
    if args.add_example_plot:
        plot = ConfigTemplateGenerator.create_plot_config(
            "bar",
            "benchmark_name",
            "simTicks",
            "execution_time",
            title="Execution Time by Benchmark",
            xlabel="Benchmark",
            ylabel="Execution Time",
            grid=True
        )
        config['plots'].append(plot)
    
    # Save configuration
    ConfigTemplateGenerator.save_config(config, args.config_file)
    print(f"✓ Template created: {args.config_file}")


def validate_command(args):
    """Validate a configuration file."""
    print(f"Validating configuration: {args.config_file}")
    
    try:
        validator = ConfigValidator()
        validator.validate_file(args.config_file)
        print("✓ Configuration is valid!")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        
        with open(args.config_file, 'r') as f:
            config = json.load(f)
        
        errors = validator.get_errors(config)
        if errors:
            print("\nValidation errors:")
            for error in errors:
                print(f"  - {error}")
        
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="RING-5: gem5 Data Analyzer (Pure Python Edition)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run analysis with configuration file
  python ring5.py analyze -c config.json
  
  # Skip parsing if CSV already exists
  python ring5.py analyze -c config.json --skip-parse
  
  # Create a configuration template
  python ring5.py create-template -o ./output -s /path/to/stats
  
  # Validate a configuration file
  python ring5.py validate -c config.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Run data analysis')
    analyze_parser.add_argument(
        '-c', '--config',
        dest='config_file',
        required=True,
        help='Configuration JSON file'
    )
    analyze_parser.add_argument(
        '-s', '--skip-parse',
        action='store_true',
        help='Skip data parsing if CSV exists'
    )
    
    # Create template command
    template_parser = subparsers.add_parser(
        'create-template',
        help='Create configuration template'
    )
    template_parser.add_argument(
        '-o', '--output-path',
        default='./output',
        help='Output directory path'
    )
    template_parser.add_argument(
        '-s', '--stats-path',
        default='/path/to/gem5/stats',
        help='Path to gem5 stats files'
    )
    template_parser.add_argument(
        '-c', '--config-file',
        default='config.json',
        help='Output configuration file name'
    )
    template_parser.add_argument(
        '--seeds-reducer',
        action='store_true',
        help='Enable seeds reducer in template'
    )
    template_parser.add_argument(
        '--add-example-plot',
        action='store_true',
        help='Add an example plot to template'
    )
    
    # Validate command
    validate_parser = subparsers.add_parser(
        'validate',
        help='Validate configuration file'
    )
    validate_parser.add_argument(
        '-c', '--config',
        dest='config_file',
        required=True,
        help='Configuration JSON file to validate'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == 'analyze':
        analyzer = RING5Analyzer(args.config_file)
        analyzer.run(skip_parse=args.skip_parse)
    
    elif args.command == 'create-template':
        create_template_command(args)
    
    elif args.command == 'validate':
        validate_command(args)


if __name__ == '__main__':
    main()
