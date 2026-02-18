import pandas as pd
import numpy as np
import pickle
import shap
import matplotlib.pyplot as plt
import os

# --- CONFIGURATION ---
FEATURES = [
    'qber_overall', 
    'qber_rectilinear', 
    'qber_diagonal',
    'detector_voltage', 
    'timing_jitter', 
    'photon_count_rate'
]

# Define where to save the images
RESULTS_DIR = "Results/Forensic_Evidence"

def explain_predictions():
    print("--- Phase 4: XAI Explanation (High-Res & Organized) ---")
    
    # 1. Load the Model
    model_path = "Models/rf_model_v3.pkl"
    if not os.path.exists(model_path):
        print("Error: Model not found! Run model_training.py first.")
        return
        
    with open(model_path, "rb") as f:
        rf_model = pickle.load(f)
    
    print("Initializing SHAP Explainer...")
    explainer = shap.TreeExplainer(rf_model)
    
    # Ensure Results folder exists
    os.makedirs(RESULTS_DIR, exist_ok=True)
    print(f" -> Saving all evidence to: {RESULTS_DIR}/")
    
    # --- HELPER: ROBUST PLOTTER ---
    def generate_plot(attack_name, csv_filename, clean_name):
        print(f"\nExplaining {attack_name}...")
        data_path = f"Datasets/Processed/{csv_filename}"
        
        if not os.path.exists(data_path):
            print(f"Skipping {attack_name} (File not found)")
            return

        # Load Data
        df = pd.read_csv(data_path)
        # Sample 100 rows for speed
        X_sample = df[FEATURES].sample(n=100, random_state=42)
        
        # Get SHAP values
        print(" -> Calculating SHAP values...")
        shap_values = explainer.shap_values(X_sample, check_additivity=False)
        
        # Identify the correct index for the attack class
        class_names = rf_model.classes_
        try:
            target_index = np.where(class_names == attack_name)[0][0]
        except IndexError:
            print(f"Error: Class '{attack_name}' not found!")
            return

        # Handle SHAP data formats (List vs Array)
        shap_values_target = None
        if isinstance(shap_values, list):
            shap_values_target = shap_values[target_index]
        elif isinstance(shap_values, np.ndarray) and len(shap_values.shape) == 3:
            if shap_values.shape[0] == len(X_sample): 
                shap_values_target = shap_values[:, :, target_index]
            else:
                shap_values_target = shap_values[target_index]
        else:
            shap_values_target = shap_values[target_index]

        # --- PLOT 1: Executive Summary (Bar Chart) ---
        plt.figure(figsize=(10, 6))
        shap.summary_plot(
            shap_values_target, 
            X_sample, 
            feature_names=FEATURES,
            show=False,
            plot_type="bar"
        )
        plt.title(f"Primary Indicators: {clean_name}", fontsize=14)
        plt.tight_layout()
        
        bar_filename = f"Evidence_{clean_name}_Summary.png"
        save_path = os.path.join(RESULTS_DIR, bar_filename)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f" -> Saved summary to '{save_path}'")
        plt.close()

        # --- PLOT 2: Technical Deep-Dive (Beeswarm) ---
        plt.figure(figsize=(12, 8))
        shap.summary_plot(
            shap_values_target, 
            X_sample, 
            feature_names=FEATURES,
            show=False,
            plot_type="dot"
        )
        plt.title(f"Forensic Fingerprint: {clean_name}", fontsize=14)
        plt.tight_layout()
        
        dot_filename = f"Evidence_{clean_name}_Detailed.png"
        save_path = os.path.join(RESULTS_DIR, dot_filename)
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f" -> Saved detailed plot to '{save_path}'")
        plt.close()

    # --- RUN EXPLANATIONS ---
    # We use "Clean Names" for the files so they look professional
    generate_plot("attack_timeshift", "attack_timeshift.csv", "TimeShift_Attack")
    generate_plot("attack_blinding", "attack_blinding.csv", "Blinding_Attack")

    print("\n--- XAI Generation Complete ---")

if __name__ == "__main__":
    explain_predictions()