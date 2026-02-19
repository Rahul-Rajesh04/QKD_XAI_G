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
    Vectorized generation of hardware metrics matches components.py Physics.
    """
    # 1. Base Distributions (Normal Operation)
    # Voltage: ~3.3V (Geiger Mode)
    # Jitter: ~1.2ns (Thermal Noise)
    # Efficiency: ~25%
    voltage = np.random.normal(3.3, 0.2, n) 
    jitter = np.random.normal(1.2, 0.2, n)
    counts = np.random.normal(0.25, 0.02, n)

    # 2. Attack-Specific Overrides
    if label == "attack_blinding":
        # Blinding: 
        # - Voltage Spikes to >8V (Saturation)
        # - Jitter drops to ~0.1ns (CW Laser = No Jitter)
        voltage = np.random.normal(9.0, 0.1, n)
        jitter = np.random.normal(0.1, 0.01, n)
        counts = np.random.normal(0.99, 0.005, n) # Saturation counts
        
    elif label == "attack_timeshift":
        # Time-Shift:
        # - Voltage is Normal (~3.3V)
        # - Jitter is suspicious (~0.05ns)
        # - Counts drop (~15%)
        voltage = np.random.normal(3.3, 0.2, n)
        jitter = np.random.normal(0.05, 0.01, n)
        counts = np.random.normal(0.15, 0.02, n)

    # Clip values to realistic physical bounds
    voltage = np.maximum(0, voltage)
    jitter = np.maximum(0, jitter)
    counts = np.clip(counts, 0, 1)

    return voltage, jitter, counts

def run_simulation_task(task_config):
    label, filename, sim_class, kwargs = task_config
    print(f"[{label}] Starting generation of {DATASET_SIZE} events...")

    # --- SIMULATION LOGIC ---
    if label == "normal":
        # Robust Normal Training (Variable Noise 1% to 5%)
        dfs = []
        chunk_size = DATASET_SIZE // 5
        noise_levels = [0.01, 0.02, 0.03, 0.04, 0.05]
        
        for p in noise_levels:
            current_kwargs = {"p_fail": p}
            experiment = sim_class(chunk_size, **current_kwargs)
            experiment.execute()
            
            chunk_data = {
                'alice_bit': experiment.alice.bits,
                'alice_basis': experiment.alice.bases,
                'bob_basis': experiment.bob.bases,
                'bob_bit': experiment.bob.measured_bits,
            }
            # Derived & Hardware
            chunk_data['basis_match'] = (chunk_data['alice_basis'] == chunk_data['bob_basis']).astype(int)
            chunk_data['error'] = (chunk_data['alice_bit'] != chunk_data['bob_bit']).astype(int)
            
            v, j, c = generate_hardware_vitals(chunk_size, label)
            chunk_data['detector_voltage'] = v
            chunk_data['timing_jitter'] = j
            chunk_data['photon_count_rate'] = c
            
            dfs.append(pd.DataFrame(chunk_data))
            
        df = pd.concat(dfs, ignore_index=True)
    
    else:
        # Standard logic for attacks
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
        
        # Spoofing for Blinding/TimeShift (Eve matches Alice)
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

def main():
    print("--- Starting Parallel Data Generation (Aligned Physics Mode) ---")
    
    tasks = [
        ("normal", "normal_data.csv", noisy.NoisyQKDExperiment, {}), 
        ("attack_intercept", "attack_intercept.csv", eve.EveQKDExperiment, {}),
        ("attack_blinding", "attack_blinding.csv", noisy.NoisyQKDExperiment, {"p_fail": 0.0}), 
        ("attack_timeshift", "attack_timeshift.csv", noisy.NoisyQKDExperiment, {"p_fail": 0.0})
    ]

    with ProcessPoolExecutor() as executor:
        results = list(executor.map(run_simulation_task, tasks))
        
    print("\n--- All Tasks Complete ---")
    for res in results:
        print(res)

if __name__ == '__main__':
    main()