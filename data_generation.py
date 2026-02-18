import pandas as pd
import numpy as np
import os
import sys
from concurrent.futures import ProcessPoolExecutor

# --- PATH SETUP ---
# Ensure we can import from the Simulation folder
sys.path.append(os.path.join(os.path.dirname(__file__), 'Simulation'))

# --- UPDATED IMPORTS (Matching your new filenames) ---
import manager as expt
import noise as noisy
import attacker as eve

# --- CONFIGURATION ---
# 1 Million rows per dataset (Standard for ML)
DATASET_SIZE = 1_000_000
OUTPUT_DIR = "Datasets/Raw"

def generate_hardware_vitals(n, label):
    """
    Vectorized generation of hardware metrics (Voltage, Jitter, Counts).
    Returns 3 arrays of size n.
    """
    # 1. Base Distributions (Normal Operation)
    # Voltage ~ N(0.5, 0.02)
    voltage = np.random.normal(0.5, 0.02, n)
    # Jitter ~ N(1.2, 0.05)
    jitter = np.random.normal(1.2, 0.05, n)
    # Count Rate ~ N(0.4, 0.02)
    counts = np.random.normal(0.4, 0.02, n)

    # 2. Attack-Specific Overrides
    if label == "attack_blinding":
        # Blinding: Massive Voltage Spike (9V), Saturation (99%)
        voltage = np.random.normal(9.0, 0.5, n)
        counts = np.random.normal(0.99, 0.005, n)
        
    elif label == "attack_timeshift":
        # Time-Shift: Unnatural Precision (0.2ns), Low Efficiency (20%)
        jitter = np.random.normal(0.2, 0.05, n)
        counts = np.random.normal(0.2, 0.02, n)

    # Clip values to realistic physical bounds
    voltage = np.maximum(0, voltage)
    jitter = np.maximum(0, jitter)
    counts = np.clip(counts, 0, 1)

    return voltage, jitter, counts

def run_simulation_task(task_config):
    """
    Worker function to run one simulation and save to CSV.
    """
    label, filename, sim_class, kwargs = task_config
    print(f"[{label}] Starting generation of {DATASET_SIZE} events...")

    # 1. Run the Physics Simulation
    experiment = sim_class(DATASET_SIZE, **kwargs)
    experiment.execute()
    
    # 2. Extract Data (Vectorized)
    data = {
        'alice_bit': experiment.alice.bits,
        'alice_basis': experiment.alice.bases,
        'bob_basis': experiment.bob.bases,
        'bob_bit': experiment.bob.measured_bits,
    }
    
    # 3. Calculate Derived Metrics (Vectorized)
    data['basis_match'] = (data['alice_basis'] == data['bob_basis']).astype(int)
    data['error'] = (data['alice_bit'] != data['bob_bit']).astype(int)
    
    # 4. Handle "Spoofing" Attacks (Blinding/Time-Shift)
    if label in ["attack_blinding", "attack_timeshift"]:
        # Force Error = 0 for 99% of bits (Eve is controlling detectors)
        mask_clean = np.random.random(DATASET_SIZE) > 0.01
        data['error'][mask_clean] = 0
        data['bob_bit'][mask_clean] = data['alice_bit'][mask_clean]

    # 5. Generate Hardware Vitals
    voltage, jitter, counts = generate_hardware_vitals(DATASET_SIZE, label)
    data['detector_voltage'] = voltage
    data['timing_jitter'] = jitter
    data['photon_count_rate'] = counts
    
    # 6. Save to CSV
    df = pd.DataFrame(data)
    df['label'] = label
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(out_path, index=False)
    
    return f"[{label}] DONE: Saved {len(df)} rows to {out_path}"

def main():
    print("--- Starting Parallel Data Generation ---")
    
    # Define the 4 tasks
    tasks = [
        ("normal", "normal_data.csv", noisy.NoisyQKDExperiment, {"p_fail": 0.03}),
        ("attack_intercept", "attack_intercept.csv", eve.EveQKDExperiment, {}),
        ("attack_blinding", "attack_blinding.csv", noisy.NoisyQKDExperiment, {"p_fail": 0.0}), 
        ("attack_timeshift", "attack_timeshift.csv", noisy.NoisyQKDExperiment, {"p_fail": 0.0})
    ]

    # Run in parallel using all available CPU cores
    with ProcessPoolExecutor() as executor:
        results = list(executor.map(run_simulation_task, tasks))
        
    print("\n--- All Tasks Complete ---")
    for res in results:
        print(res)

if __name__ == '__main__':
    main()