__author__ = "Rahul Rajesh 2360445"

import manager as expt

def main():
    SIZE_TX = 1000
    
    print(f"--- Running Noiseless Simulation (N={SIZE_TX}) ---")
    
    experiment = expt.QKDExperiment(SIZE_TX)
    
    final_error_rate = experiment.execute()
    
    print("Execution Complete.")
    print(f"Final Error Rate: {final_error_rate * 100:.2f}%")
    print(f"Secure Key Length: {len(experiment.final_key_alice)}")

if __name__ == '__main__':
    main()