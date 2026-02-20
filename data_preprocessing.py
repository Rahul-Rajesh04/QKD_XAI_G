__author__ = "Rahul Rajesh 2360445"

import pandas as pd
import numpy as np
import os

def calculate_v3_features(df, window_size=500):
    print("   -> Calculating Micro-Sifting stats...")
    
    df['sifted'] = df['basis_match']
    
    is_rect = df['alice_basis'] == 0
    is_diag = df['alice_basis'] == 1
    
    df['error_rect'] = df['error'] & is_rect
    df['error_diag'] = df['error'] & is_diag
    
    r_sifted = df['sifted'].rolling(window=window_size).sum()
    r_error_total = df['error'].rolling(window=window_size).sum()
    r_error_rect = df['error_rect'].rolling(window=window_size).sum()
    r_error_diag = df['error_diag'].rolling(window=window_size).sum()
    
    r_count_rect = (df['sifted'] & is_rect).rolling(window=window_size).sum()
    r_count_diag = (df['sifted'] & is_diag).rolling(window=window_size).sum()

    df['qber_overall'] = (r_error_total / r_sifted).fillna(0.0).replace([np.inf, -np.inf], 0.0)
    df['qber_rectilinear'] = (r_error_rect / r_count_rect).fillna(0.0).replace([np.inf, -np.inf], 0.0)
    df['qber_diagonal'] = (r_error_diag / r_count_diag).fillna(0.0).replace([np.inf, -np.inf], 0.0)

    features = [
        'qber_overall', 
        'qber_rectilinear', 
        'qber_diagonal',
        'detector_voltage', 
        'timing_jitter', 
        'photon_count_rate',
        'label'
    ]
    
    df_final = df[features].dropna()
    
    return df_final

def process_file(filename):
    input_path = f"Datasets/Raw/{filename}"
    output_path = f"Datasets/Processed/{filename}"
    
    if not os.path.exists(input_path):
        print(f"Skipping {filename} (File not found)")
        return

    print(f"Processing {filename}...")
    df = pd.read_csv(input_path)
    
    df_processed = calculate_v3_features(df, window_size=500)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_processed.to_csv(output_path, index=False)
    print(f" -> Saved {len(df_processed)} fingerprint vectors to {output_path}")

def main():
    print("--- Phase 2: Feature Engineering (v3.0) ---")
    
    process_file("normal_data.csv")
    process_file("attack_intercept.csv")
    process_file("attack_blinding.csv")
    process_file("attack_timeshift.csv")
    
    print("--- Processing Complete ---")

if __name__ == "__main__":
    main()