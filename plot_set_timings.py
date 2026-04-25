#!/usr/bin/env python3
"""
Script to plot Prime-Probe timing data by cache set.

Input: 
  - Directory containing timing files
  - Set number to analyze

Output:
  - Graph with one line per run of the given set
  - X-axis: Cycle number difference from first entry
  - Y-axis: Cycle delta (timing difference)
"""

import os
import glob
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

NUMBER_OF_SETS = 64

def read_timing_file(filepath):
    """
    Read a timing file with format '%ld %d' per line.
    
    Args:
        filepath: Path to the timing file
        
    Returns:
        tuple: (cycle_numbers, deltas) as lists
    """
    cycles = []
    deltas = []
    
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                    
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        cycle = int(parts[0])
                        delta = int(parts[1])
                        cycles.append(cycle)
                        deltas.append(delta)
                    except ValueError:
                        continue
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return None, None
    
    return cycles, deltas


def normalize_cycles(cycles):
    """
    Convert cycle numbers to differences from the first cycle.
    
    Args:
        cycles: List of cycle numbers
        
    Returns:
        List of cycle differences (first_cycle - current_cycle)
    """
    if not cycles:
        return []
    
    first_cycle = cycles[0]
    return [cycle - first_cycle for cycle in cycles]


def plot_set_timings(data_dir, set_number=None, run_number=None, output_file=None):
    """
    Plot all timing data for a specific cache set.
    
    Args:
        data_dir: Directory containing timing files
        set_number: Cache set number to analyze
        output_file: Optional output filename (default: Prime-Probe_set_{set_number}.png)
    """
    # Find all files matching the pattern Prime-Probe_timings*-{set_number}.txt
    pattern = os.path.join(data_dir, f"Prime-Probe_timings{'*' if run_number == None else run_number}-{'*' if set_number == None else set_number}.txt")
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"No timing files found for set {'all' if set_number == None else set_number} and run {'all' if run_number == None else run_number} in {data_dir}")
        raise FileNotFoundError
    
    print(f"Found {len(files)} timing files for set {'all' if set_number == None else set_number} and run {'all' if run_number == None else run_number}")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Process each file
    for filepath in files:
        # Extract run number from filename (Prime-Probe_timings{run}-{set}.txt)
        filename = os.path.basename(filepath)
        # Extract run number by parsing "Prime-Probe_timings{run}-{set}.txt"
        parts = filename.replace("Prime-Probe_timings", "").replace(".txt", "").split("-")
        file_run_number = parts[0]
        file_set_number = parts[1]
        
        cycles, deltas = read_timing_file(filepath)
        if cycles is None or len(cycles) == 0:
            print(f"Warning: Could not read data from {filepath}")
            continue
        
        # Normalize cycles
        cycle_diffs = normalize_cycles(cycles)
        
        # Plot
        # ax.plot(cycle_diffs, deltas, label=f"R{file_run_number}S{file_set_number}", linewidth=1.5, alpha=0.8)
        ax.scatter(cycle_diffs, deltas, label=f"R{file_run_number}S{file_set_number}")
    
    # Configure plot
    ax.set_xlabel("Cycle Number Difference from First Entry", fontsize=12)
    ax.set_ylabel("Cycle Delta (Timing Difference)", fontsize=12)
    ax.set_title(f"Prime-Probe Timing Data for Cache Set {'all' if set_number == None else set_number}", fontsize=14)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    
    # Save figure
    if output_file is None:
        output_file = data_dir + os.sep + f"Prime-Probe_set_{'all' if set_number == None else set_number}_run_{'all' if run_number == None else run_number}.png"
    
    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    print(f"Plot saved to {output_file}")
    plt.close()

def plot_cycle_variations(data_dir, set_number=None, output_file=None):
    """
    Plot variance in cycle measurements per set
    
    Args:
        data_dir: Directory containing timing files
        set_number: Cache set number to analyze
        output_file: Optional output filename (default: Prime-Probe_set_{set_number}.png)
    """
    # Find all files matching the pattern Prime-Probe_timings*-{set_number}.txt
    pattern = os.path.join(data_dir, f"Prime-Probe_timings*-{'*' if set_number == None else set_number}.txt")
    files = sorted(glob.glob(pattern))
    
    if not files:
        print(f"No timing files found for set {'all' if set_number == None else set_number} in {data_dir}")
        raise FileNotFoundError
    
    print(f"Found {len(files)} timing files for set {'all' if set_number == None else set_number}")
    
    # Create figure
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Dictionary to group deltas by set number
    set_deltas = {}
    
    # Process each file
    for filepath in files:
        # Extract run number from filename (Prime-Probe_timings{run}-{set}.txt)
        filename = os.path.basename(filepath)
        # Extract run number by parsing "Prime-Probe_timings{run}-{set}.txt"
        parts = filename.replace("Prime-Probe_timings", "").replace(".txt", "").split("-")
        file_run_number = parts[0]
        file_set_number = parts[1]
        
        cycles, deltas = read_timing_file(filepath)
        if cycles is None or len(cycles) == 0:
            print(f"Warning: Could not read data from {filepath}")
            continue
        
        # Group deltas by set number
        if file_set_number not in set_deltas:
            set_deltas[file_set_number] = []
        set_deltas[file_set_number].extend(deltas)
    
    # Prepare data for boxplot (sort sets numerically)
    sorted_sets = sorted(set_deltas.keys(), key=int)
    boxplot_data = [set_deltas[s] for s in sorted_sets]
    
    # Create boxplot
    ax.boxplot(boxplot_data, labels=sorted_sets)
        
    # Configure plot
    ax.set_xlabel("Set", fontsize=12)
    ax.set_ylabel("Cycle probe times", fontsize=12)
    ax.set_title(f"Traditional Prime-Probe Timing Data for Cache Set {'all' if set_number == None else set_number}", fontsize=14)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Save figure
    if output_file is None:
        output_file = data_dir + os.sep + f"Traditional_Prime-Probe_set_{'all' if set_number == None else set_number}.png"
    
    fig.tight_layout()
    fig.savefig(output_file, dpi=150)
    print(f"Plot saved to {output_file}")
    plt.close()

def main():
    parser = argparse.ArgumentParser(
        description="Plot Prime-Probe timing data by cache set"
    )
    parser.add_argument(
        "data_dir",
        help="Directory containing timing files"
    )
    parser.add_argument(
        "--set_number",
        type=int,
        help="Cache set number to analyze (dafault: all)"
    )
    parser.add_argument(
        "--run_number",
        type=int,
        help="Run number to look at"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output filename (default: Prime-Probe_set_{set_number}.png)"
    )
    parser.add_argument(
        "--plot_per_set",
        action="store_true",
        help="Group data by runs in each set"
    )
    parser.add_argument(
        "--plot_per_run",
        action="store_true",
        help="Group data by sets in each run"
    )
    parser.add_argument(
        "--plot_averages",
        action="store_true",
        help="Plot average cycle measurements for each set"
    )
    
    args = parser.parse_args()
    
    # Verify directory exists
    if not os.path.isdir(args.data_dir):
        print(f"Error: Directory not found: {args.data_dir}")
        return 1
        
    if (args.plot_averages):
        plot_cycle_variations(args.data_dir, args.set_number, args.output)
        return
    
    if (args.plot_per_set):
        for i in range(NUMBER_OF_SETS):
            plot_set_timings(args.data_dir, i, args.run_number, args.output)
    elif (args.plot_per_run):
        i = 0
        while True:
            try:
                plot_set_timings(args.data_dir, args.set_number, i, args.output)
            except FileNotFoundError:
                break
            i += 1
    else:          
        plot_set_timings(args.data_dir, args.set_number, args.run_number, args.output)
    return 0


if __name__ == "__main__":
    exit(main())
