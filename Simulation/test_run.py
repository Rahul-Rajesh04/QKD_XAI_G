# -*- coding: utf-8 -*-
"""
Optimized Noiseless QKD Execution (Test Script)
-----------------------------------------------
File: Simulation/test_run.py
"""

# CRITICAL UPDATE: Import from the new 'manager.py' file
import manager as expt

def main():
    # We can now easily handle 100,000+ qubits instantly thanks to vectorization
    SIZE_TX = 1000
    
    print(f"--- Running Noiseless Simulation (N={SIZE_TX}) ---")
    
    # Initialize the Experiment
    experiment = expt.QKDExperiment(SIZE_TX)
    
    # Run
    final_error_rate = experiment.execute()
    
    print(f"Execution Complete.")
    print(f"Final Error Rate: {final_error_rate * 100:.2f}%")
    print(f"Secure Key Length: {len(experiment.final_key_alice)}")

if __name__ == '__main__':
    main()