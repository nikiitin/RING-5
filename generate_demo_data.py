#!/usr/bin/env python3
"""
Quick Demo Script for RING-5 Web Application
Generates sample data and demonstrates features.
"""
import pandas as pd
import numpy as np
from pathlib import Path

def generate_sample_data():
    """Generate sample gem5 statistics data for demo."""
    
    # Benchmarks
    benchmarks = ['bzip2', 'gcc', 'mcf', 'hmmer']
    
    # Configurations
    configs = ['baseline', 'opt_l1', 'opt_l2', 'opt_both']
    
    # Seeds
    seeds = [1, 2, 3, 4, 5]
    
    # Generate data
    data = []
    for benchmark in benchmarks:
        for config in configs:
            for seed in seeds:
                # Simulate performance metrics
                base_ipc = np.random.uniform(1.0, 2.5)
                base_l1_miss = np.random.uniform(0.05, 0.15)
                base_l2_miss = np.random.uniform(0.01, 0.05)
                
                # Apply config effects
                if config == 'opt_l1':
                    ipc = base_ipc * 1.1
                    l1_miss_rate = base_l1_miss * 0.7
                    l2_miss_rate = base_l2_miss
                elif config == 'opt_l2':
                    ipc = base_ipc * 1.15
                    l1_miss_rate = base_l1_miss
                    l2_miss_rate = base_l2_miss * 0.6
                elif config == 'opt_both':
                    ipc = base_ipc * 1.25
                    l1_miss_rate = base_l1_miss * 0.7
                    l2_miss_rate = base_l2_miss * 0.6
                else:  # baseline
                    ipc = base_ipc
                    l1_miss_rate = base_l1_miss
                    l2_miss_rate = base_l2_miss
                
                data.append({
                    'benchmark': benchmark,
                    'config': config,
                    'seed': seed,
                    'ipc': round(ipc + np.random.normal(0, 0.05), 3),
                    'l1_miss_rate': round(l1_miss_rate + np.random.normal(0, 0.01), 4),
                    'l2_miss_rate': round(l2_miss_rate + np.random.normal(0, 0.005), 4),
                    'cycles': int(np.random.uniform(1e9, 5e9)),
                    'instructions': int(np.random.uniform(1e9, 10e9))
                })
    
    df = pd.DataFrame(data)
    return df


def main():
    """Generate and save sample data."""
    print("🎯 Generating Sample Data for RING-5 Demo")
    print("=" * 50)
    
    # Generate data
    df = generate_sample_data()
    
    # Save to examples directory
    output_dir = Path(__file__).parent / 'examples'
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / 'sample_gem5_stats.csv'
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ Sample data saved to: {output_file}")
    print(f"   Rows: {len(df)}")
    print(f"   Columns: {len(df.columns)}")
    
    # Show preview
    print("\n📊 Data Preview:")
    print(df.head(10))
    
    print("\n📈 Statistics:")
    print(df.describe())
    
    print("\n" + "=" * 50)
    print("🚀 Ready to demo!")
    print("\n1. Launch app: streamlit run app.py")
    print(f"2. Upload: {output_file}")
    print("3. Configure pipeline:")
    print("   - Normalize: baseline config")
    print("   - Mean: geomean by config")
    print("   - Sort: custom config order")
    print("4. Generate plots!")
    print("=" * 50)


if __name__ == '__main__':
    main()
