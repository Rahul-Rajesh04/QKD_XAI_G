import pandas as pd
import numpy as np
import os
import sys
from concurrent.futures import ProcessPoolExecutor

# --- PATH SETUP ---
sys.path.append(os.path.join(os.path.dirname(__file__), 'Simulation'))

import manager as expt
import noise as noisy
import attacker as eve

# --- CONFIGURATION ---
DATASET_SIZE = 1_000_000
OUTPUT_DIR = "Datasets/Raw"

def generate_hardware_vitals(n, label):
    """
    Vectorized generation of hardware metrics.
    """
    # 1. Base Distributions (Normal Operation)
    voltage = np.random.normal(0.8, 0.05, n) 
    jitter = np.random.normal(1.2, 0.05, n)
    counts = np.random.normal(0.25, 0.02, n)

    # 2. Attack-Specific Overrides
    if label == "attack_blinding":
        voltage = np.random.normal(9.0, 0.5, n)
        counts = np.random.normal(0.99, 0.005, n)
        
    elif label == "attack_timeshift":
        jitter = np.random.normal(0.2, 0.05, n)
        counts = np.random.normal(0.15, 0.02, n)

    # Clip values
    voltage = np.maximum(0, voltage)
    jitter = np.maximum(0, jitter)
    counts = np.clip(counts, 0, 1)

    return voltage, jitter, counts

def run_simulation_task(task_config):
    label, filename, sim_class, kwargs = task_config
    print(f"[{label}] Starting generation of {DATASET_SIZE} events...")

    # --- SPECIAL LOGIC FOR ROBUST NORMAL TRAINING ---
    if label == "normal":
        # We split the 1M rows into 5 chunks with DIFFERENT noise levels.
        # This teaches the AI that Normal isn't just "3%", but "0% to 5%".
        dfs = []
        chunk_size = DATASET_SIZE // 5
        noise_levels = [0.01, 0.02, 0.03, 0.04, 0.05]
        
        for p in noise_levels:
            # Run simulation with specific noise
            current_kwargs = {"p_fail": p}
            experiment = sim_class(chunk_size, **current_kwargs)
            experiment.execute()
            
            # Extract
            chunk_data = {
                'alice_bit': experiment.alice.bits,
                'alice_basis': experiment.alice.bases,
                'bob_basis': experiment.bob.bases,
                'bob_bit': experiment.bob.measured_bits,
            }
            # Add Derived & Hardware
            chunk_data['basis_match'] = (chunk_data['alice_basis'] == chunk_data['bob_basis']).astype(int)
            chunk_data['error'] = (chunk_data['alice_bit'] != chunk_data['bob_bit']).astype(int)
            
            v, j, c = generate_hardware_vitals(chunk_size, label)
            chunk_data['detector_voltage'] = v
            chunk_data['timing_jitter'] = j
            chunk_data['photon_count_rate'] = c
            
            dfs.append(pd.DataFrame(chunk_data))
            
        # Combine all chunks
        df = pd.concat(dfs, ignore_index=True)
    
    else:
        # STANDARD LOGIC FOR ATTACKS
        experiment = sim_class(DATASET_SIZE, **kwargs)
        experiment.execute()
        
        data = {
            'alice_bit': experiment.alice.bits,
            'alice_basis': experiment.alice.bases,
            'bob_basis': experiment.bob.bases,
            'bob_bit': experiment.bob.measured_bits,
        }
        
        data['basis_match'] = (data['alice_basis'] == data['bob_basis']).astype(int)
        data['error'] = (data['alice_bit'] != data['bob_bit']).astype(int)
        
        if label in ["attack_blinding", "attack_timeshift"]:
            mask_clean = np.random.random(DATASET_SIZE) > 0.01
            data['error'][mask_clean] = 0
            data['bob_bit'][mask_clean] = data['alice_bit'][mask_clean]

        voltage, jitter, counts = generate_hardware_vitals(DATASET_SIZE, label)
        data['detector_voltage'] = voltage
        data['timing_jitter'] = jitter
        data['photon_count_rate'] = counts
        
        df = pd.DataFrame(data)

    # Save
    df['label'] = label
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(out_path, index=False)
    
    return f"[{label}] DONE: Saved {len(df)} rows to {out_path}"

# --- UPDATED TASKS IN data_generation.py ---
def main():
    print("--- Starting Parallel Data Generation (Robust Boundary Mode) ---")
    
    tasks = [
        # Normal handles 1% to 5% noise variance internally
        ("normal", "normal_data.csv", noisy.NoisyQKDExperiment, {}), 
        
        # Intercept-Resend: Standard physics always results in ~25% QBER
        ("attack_intercept", "attack_intercept.csv", eve.EveQKDExperiment, {}),
        
        # Blinding/Time-Shift: Hardware-focused attacks
        ("attack_blinding", "attack_blinding.csv", noisy.NoisyQKDExperiment, {"p_fail": 0.0}), 
        ("attack_timeshift", "attack_timeshift.csv", noisy.NoisyQKDExperiment, {"p_fail": 0.0})
    ]
    # ... rest of the code remains the same ...

if __name__ == '__main__':
    main()