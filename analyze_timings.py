import os
import glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from pathlib import Path

# Configuration
DATA_DIR = "parallel_probing_times"
FILE_PATTERN = "Prime-Probe_timings*.txt"
NUM_SETS = 64

def read_timing_file(filepath):
    """
    Read a timing file and extract baseline, post-event, and delta cycles.
    Returns lists of (baseline, post_event, delta) tuples.
    """
    data = []
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line and line.isdigit() == False:  # Skip empty lines and the final delimiter
                    parts = line.split()
                    if len(parts) == 3:
                        try:
                            baseline = int(parts[0])
                            post_event = int(parts[1])
                            delta = int(parts[2])
                            data.append((baseline, post_event, delta))
                        except ValueError:
                            continue
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
    return data

def load_all_timing_data():
    """
    Load all timing files and organize data by cache set.
    Returns a dictionary with set number as key and list of (baseline, post_event, delta) as value.
    """
    timing_data = {}
    
    # Find all timing files
    files = sorted(glob.glob(os.path.join(DATA_DIR, FILE_PATTERN)))
    
    for filepath in files:
        # Extract set number from filename
        filename = os.path.basename(filepath)
        try:
            set_num = int(filename.replace("Prime-Probe_timings", "").replace(".txt", ""))
            data = read_timing_file(filepath)
            if data:
                timing_data[set_num] = data
        except ValueError:
            continue
    
    return timing_data

def create_summary_statistics(timing_data):
    """
    Create summary statistics for each cache set.
    Returns a dictionary with statistics.
    """
    stats = {}
    for set_num in sorted(timing_data.keys()):
        data = timing_data[set_num]
        baselines = [d[0] for d in data]
        deltas = [d[2] for d in data]
        
        stats[set_num] = {
            'baseline_mean': np.mean(baselines),
            'baseline_std': np.std(baselines),
            'baseline_min': np.min(baselines),
            'baseline_max': np.max(baselines),
            'delta_mean': np.mean(deltas),
            'delta_std': np.std(deltas),
            'delta_min': np.min(deltas),
            'delta_max': np.max(deltas),
            'num_samples': len(data)
        }
    
    return stats
    
def remove_outliers(timing_data):
    """
    Remove data points for each set where the baseline or post_event measurement is an outlier
    """
    new_timing_data = dict.fromkeys(timing_data.keys())
    for set, data in timing_data.items():
        new_timing_data[set] = []
        np_data = np.array(data)
        Q1 = np.percentile(np_data, 25, 0)
        Q3 = np.percentile(np_data, 75, 0)
        lower_bound_baseline = Q1[0] - 300
        upper_bound_baseline = Q3[0] + 300
        lower_bound_probe = Q1[1] - 300
        upper_bound_probe = Q3[1] + 300
        for measurement in data:
            if measurement[0] > lower_bound_baseline and measurement[0] < upper_bound_baseline and measurement[1] > lower_bound_probe and measurement[1] < upper_bound_probe:
                new_timing_data[set].append(measurement)
            else:
                print(f'Removing: {measurement}')
    return new_timing_data

def plot_baseline_and_delta_overview(timing_data, stats):
    """
    Create a figure showing average baseline and delta for each cache set.
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    
    sets = sorted(stats.keys())
    baseline_means = [stats[s]['baseline_mean'] for s in sets]
    delta_means = [stats[s]['delta_mean'] for s in sets]
    
    # Baseline cycles per set
    axes[0].bar(sets, baseline_means, color='steelblue', alpha=0.7, edgecolor='black')
    axes[0].set_xlabel('Cache Set', fontsize=11)
    axes[0].set_ylabel('Average Baseline Cycles', fontsize=11)
    axes[0].set_title('Average Baseline Cycles by Cache Set', fontsize=12, fontweight='bold')
    axes[0].grid(axis='y', alpha=0.3)
    axes[0].set_xticks(range(0, NUM_SETS, 8))
    
    # Delta cycles per set
    axes[1].bar(sets, delta_means, color='coral', alpha=0.7, edgecolor='black')
    axes[1].set_xlabel('Cache Set', fontsize=11)
    axes[1].set_ylabel('Average Delta Cycles', fontsize=11)
    axes[1].set_title('Average Delta Cycles by Cache Set', fontsize=12, fontweight='bold')
    axes[1].grid(axis='y', alpha=0.3)
    axes[1].set_xticks(range(0, NUM_SETS, 8))
    
    plt.tight_layout()
    return fig

def plot_distribution_analysis(timing_data, stats):
    """
    Create box plots showing the distribution of baseline and delta for each cache set.
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    
    sets = sorted(timing_data.keys())
    
    # Baseline distributions
    baseline_data = [np.array([d[0] for d in timing_data[s]]) for s in sets]
    bp1 = axes[0].boxplot(baseline_data, labels=sets, patch_artist=True)
    for patch in bp1['boxes']:
        patch.set_facecolor('steelblue')
        patch.set_alpha(0.7)
    axes[0].set_xlabel('Cache Set', fontsize=11)
    axes[0].set_ylabel('Baseline Cycles', fontsize=11)
    axes[0].set_title('Distribution of Baseline Cycles by Cache Set', fontsize=12, fontweight='bold')
    axes[0].grid(axis='y', alpha=0.3)
    
    # Delta distributions
    delta_data = [np.array([d[2] for d in timing_data[s]]) for s in sets]
    bp2 = axes[1].boxplot(delta_data, labels=sets, patch_artist=True)
    for patch in bp2['boxes']:
        patch.set_facecolor('coral')
        patch.set_alpha(0.7)
    axes[1].set_xlabel('Cache Set', fontsize=11)
    axes[1].set_ylabel('Delta Cycles', fontsize=11)
    axes[1].set_title('Distribution of Delta Cycles by Cache Set', fontsize=12, fontweight='bold')
    axes[1].grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    return fig

def plot_baseline_vs_delta_scatter(timing_data):
    """
    Create individual scatter plots showing the relationship between baseline and delta for each cache set.
    Returns a list of (filename, figure) tuples.
    """
    plots = []
    sets = sorted(timing_data.keys())
    
    for set_num in sets:
        fig, ax = plt.subplots(figsize=(8, 6))
        
        data = timing_data[set_num]
        baselines = np.array([d[0] for d in data])
        deltas = np.array([d[2] for d in data])
        
        ax.scatter(baselines, deltas, alpha=0.6, s=50, color='purple', edgecolors='black', linewidth=0.5)
        ax.set_xlabel('Baseline Cycles', fontsize=12)
        ax.set_ylabel('Delta Cycles', fontsize=12)
        ax.set_title(f'Cache Set {set_num}: Baseline vs Delta', fontsize=13, fontweight='bold')
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plots.append((f"scatter_set_{set_num:02d}.png", fig))
    
    return plots

def plot_time_series(timing_data):
    """
    Create individual time series plots showing baseline and delta over trials for each cache set.
    Returns a list of (filename, figure) tuples.
    """
    plots = []
    sets = sorted(timing_data.keys())
    
    for set_num in sets:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        data = timing_data[set_num]
        # baselines = np.array([d[0] for d in data])
        deltas = np.array([d[2] for d in data])
        trials = np.arange(len(data))
        
        # ax.plot(trials, baselines, label='Baseline', alpha=0.7, linewidth=1.5, color='steelblue')
        ax.plot(trials, deltas, label='Delta', alpha=0.7, linewidth=1.5, color='coral')
        ax.set_title(f'Cache Set {set_num}: Time Series of Cycle Deltas', fontsize=13, fontweight='bold')
        ax.set_xlabel('Trial Number', fontsize=12)
        ax.set_ylabel('Cycles', fontsize=12)
        ax.legend(fontsize=11, loc='best')
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        plots.append((f"timeseries_set_{set_num:02d}.png", fig))
    
    return plots

def plot_anomalies(timing_data, stats):
    """
    Identify and highlight cache sets with unusual behavior.
    """
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))
    
    sets = sorted(stats.keys())
    baseline_means = [stats[s]['baseline_mean'] for s in sets]
    delta_means = [stats[s]['delta_mean'] for s in sets]
    
    # Calculate statistics for anomaly detection
    baseline_overall_mean = np.mean(baseline_means)
    baseline_overall_std = np.std(baseline_means)
    delta_overall_mean = np.mean(delta_means)
    delta_overall_std = np.std(delta_means)
    
    # Color code by anomaly
    baseline_colors = ['red' if abs(b - baseline_overall_mean) > 2 * baseline_overall_std 
                       else 'steelblue' for b in baseline_means]
    delta_colors = ['red' if abs(d - delta_overall_mean) > 2 * delta_overall_std 
                    else 'coral' for d in delta_means]
    
    axes[0].bar(sets, baseline_means, color=baseline_colors, alpha=0.7, edgecolor='black')
    axes[0].axhline(baseline_overall_mean, color='black', linestyle='--', label=f'Mean: {baseline_overall_mean:.1f}')
    axes[0].axhline(baseline_overall_mean + 2*baseline_overall_std, color='red', linestyle=':', label='±2σ')
    axes[0].axhline(baseline_overall_mean - 2*baseline_overall_std, color='red', linestyle=':')
    axes[0].set_xlabel('Cache Set', fontsize=11)
    axes[0].set_ylabel('Average Baseline Cycles', fontsize=11)
    axes[0].set_title('Baseline Cycles with Anomaly Detection (Red = Outliers)', fontsize=12, fontweight='bold')
    axes[0].grid(axis='y', alpha=0.3)
    axes[0].legend(fontsize=10)
    axes[0].set_xticks(range(0, NUM_SETS, 8))
    
    axes[1].bar(sets, delta_means, color=delta_colors, alpha=0.7, edgecolor='black')
    axes[1].axhline(delta_overall_mean, color='black', linestyle='--', label=f'Mean: {delta_overall_mean:.1f}')
    axes[1].axhline(delta_overall_mean + 2*delta_overall_std, color='red', linestyle=':', label='±2σ')
    axes[1].axhline(delta_overall_mean - 2*delta_overall_std, color='red', linestyle=':')
    axes[1].set_xlabel('Cache Set', fontsize=11)
    axes[1].set_ylabel('Average Delta Cycles', fontsize=11)
    axes[1].set_title('Delta Cycles with Anomaly Detection (Red = Outliers)', fontsize=12, fontweight='bold')
    axes[1].grid(axis='y', alpha=0.3)
    axes[1].legend(fontsize=10)
    axes[1].set_xticks(range(0, NUM_SETS, 8))
    
    plt.tight_layout()
    return fig

def main():
    """
    Main function to load data and generate all visualizations.
    """
    print("Loading timing data...")
    timing_data = load_all_timing_data()
    
    if not timing_data:
        print("No timing data found. Ensure the 'pwd_vector_cache_times' directory exists with timing files.")
        return
    
    print(f"Successfully loaded data from {len(timing_data)} cache sets")
    timing_data = remove_outliers(timing_data)
    
    # Calculate statistics
    print("Calculating statistics...")
    stats = create_summary_statistics(timing_data)
    
    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS FOR ALL CACHE SETS")
    print("="*60)
    for set_num in sorted(stats.keys()):
        s = stats[set_num]
        print(f"\nCache Set {set_num}:")
        print(f"  Baseline: {s['baseline_mean']:7.1f} ± {s['baseline_std']:5.1f} cycles (min: {s['baseline_min']:3d}, max: {s['baseline_max']:3d})")
        print(f"  Delta:    {s['delta_mean']:7.1f} ± {s['delta_std']:5.1f} cycles (min: {s['delta_min']:3d}, max: {s['delta_max']:3d})")
    print("="*60 + "\n")
    
    # Generate plots
    print("Generating visualizations...")
    
    plots = [
        ("baseline_delta_overview.png", plot_baseline_and_delta_overview(timing_data, stats)),
        ("distribution_analysis.png", plot_distribution_analysis(timing_data, stats)),
        ("anomaly_detection.png", plot_anomalies(timing_data, stats)),
    ]
    
    # Add individual scatter plots for each set
    plots.extend(plot_baseline_vs_delta_scatter(timing_data))
    
    # Add individual time series plots for each set
    plots.extend(plot_time_series(timing_data))
    
    # Save plots
    for filename, fig in plots:
        filepath = os.path.join(DATA_DIR, filename)
        fig.savefig(filepath, dpi=150, bbox_inches='tight')
        print(f"  ✓ Saved {filename}")
    
    plt.show()
    print("\nAll visualizations have been generated and saved to the output directory.")

if __name__ == "__main__":
    main()
