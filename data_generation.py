import pandas as pd
import numpy as np
import os
import sys

# --- PATH FIX: Add 'Simulation' folder to Python's search path ---
# This allows us to import the files inside Simulation/ without editing them
current_dir = os.path.dirname(os.path.abspath(__file__))
simulation_dir = os.path.join(current_dir, 'Simulation')
sys.path.append(simulation_dir)

# --- NOW WE CAN IMPORT NORMALLY ---
import qkd_experiment_base as expt
import qkd_noise_model
import qkd_eavesdropping_2
import qkd_bb84_base

# Alias the experiment classes
NoiselessExperiment = expt.qkd_experiment
NoisyExperiment = qkd_noise_model.noisy_qkd_experiment
EveExperiment = qkd_eavesdropping_2.eve_qkd_experiment

class QKDLoggerMixin:
    def execute_and_log(self, csv_filename, label):
        """
        Runs the simulation and logs per-event data to a CSV.
        """
        print(f"Running simulation for '{label}' data...")

        self.build_phase()
        self.run_phase()

        print(f"Simulation complete. Logging {self.SIZE_TX} events...")

        events = []
        for i in range(self.SIZE_TX):
            try:
                alice_bit = self.a0.states_seq_a[i]
                alice_basis = self.a0.basis_seq_a[i]
                bob_basis = self.b0.basis_seq_b[i]
                bob_bit = self.b0.meas_seq_b[i]
            except (IndexError, AttributeError):
                print(f"Error at index {i}. Aborting log.")
                return

            # Compute per-event logic
            basis_match = 1 if alice_basis == bob_basis else 0
            error = 1 if (basis_match == 1 and alice_bit != bob_bit) else 0

            events.append({
                'timestamp_idx': i,
                'alice_bit': alice_bit,
                'alice_basis': alice_basis,
                'bob_basis': bob_basis,
                'bob_bit': bob_bit,
                'basis_match': basis_match,
                'error': error
            })

        if not events:
            print("No events logged.")
            return

        df = pd.DataFrame(events)
        df['label'] = label

        # Ensure directory exists
        os.makedirs(os.path.dirname(csv_filename), exist_ok=True)
        
        df.to_csv(csv_filename, index=False)
        print(f"Saved {len(df)} events to {csv_filename}")

# --- Create Logged Classes ---
class LoggedNoiseless(QKDLoggerMixin, NoiselessExperiment): pass
class LoggedNoisy(QKDLoggerMixin, NoisyExperiment): pass
class LoggedEve(QKDLoggerMixin, EveExperiment): pass

def main():
    print("--- Phase 1: Data Generation (1 Million Events) ---")

    # 1. Normal Data (Upscaled to 1 Million) - Training Data
    # This simulates realistic device noise (3% error rate)
    e1 = LoggedNoisy(SIZE_TX=1000000, P_H_FAIL=0.03)
    e1.execute_and_log(csv_filename="Datasets/Raw/normal_data.csv", label="normal")

    # 2. Attack Data (Upscaled to 1 Million) - Test Data
    # This simulates an active Intercept-Resend attack (~25% error rate)
    e2 = LoggedEve(SIZE_TX=1000000)
    e2.execute_and_log(csv_filename="Datasets/Raw/attack_intercept.csv", label="attack_intercept")

    # 3. Noiseless Baseline (Small) - Sanity Check
    # This simulates perfect theoretical physics (0% error rate)
    e3 = LoggedNoiseless(SIZE_TX=10000)
    e3.execute_and_log(csv_filename="Datasets/Raw/normal_noiseless.csv", label="normal_noiseless")

    print("--- Data generation complete ---")

if __name__ == '__main__':
    # Fix for qkd_noise_model relying on main execution context
    import qkd_bb84_base
    main()