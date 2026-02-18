import pandas as pd
import numpy as np
import os

def calculate_v3_features(df, window_size=50):
    """
    Transforms raw event logs into the 6-Dimensional "Superhuman" Fingerprint.
    """
    print("   -> Calculating Micro-Sifting stats...")
    
    # 1. Filter for Sifted Bits (Basis Match = 1)
    # We only calculate QBER on bits where bases matched.
    df['sifted'] = df['basis_match']
    
    # 2. Identify Basis Types (0=Rectilinear, 1=Diagonal)
    is_rect = df['alice_basis'] == 0
    is_diag = df['alice_basis'] == 1
    
    # 3. Calculate Errors per Basis
    df['error_rect'] = df['error'] & is_rect
    df['error_diag'] = df['error'] & is_diag
    
    # 4. Rolling Window Aggregation (Simulating Micro-Sifting Blocks)
    # We sum up errors and matches over the last 'window_size' events
    r_sifted = df['sifted'].rolling(window=window_size).sum()
    r_error_total = df['error'].rolling(window=window_size).sum()
    r_error_rect = df['error_rect'].rolling(window=window_size).sum()
    r_error_diag = df['error_diag'].rolling(window=window_size).sum()
    
    # Count how many rect/diag events occurred in the window
    r_count_rect = (df['sifted'] & is_rect).rolling(window=window_size).sum()
    r_count_diag = (df['sifted'] & is_diag).rolling(window=window_size).sum()

    # 5. Compute QBERs (Handling division by zero)
    df['qber_overall'] = (r_error_total / r_sifted).fillna(0.0).replace([np.inf, -np.inf], 0.0)
    df['qber_rectilinear'] = (r_error_rect / r_count_rect).fillna(0.0).replace([np.inf, -np.inf], 0.0)
    df['qber_diagonal'] = (r_error_diag / r_count_diag).fillna(0.0).replace([np.inf, -np.inf], 0.0)

    # 6. Pass-through Hardware Vitals (These are already real-time from data_generation)
    # No calculation needed, just keeping them.
    
    # 7. Clean Data & Select Features
    features = [
        'qber_overall', 
        'qber_rectilinear', 
        'qber_diagonal',
        'detector_voltage', 
        'timing_jitter', 
        'photon_count_rate',
        'label'
    ]
    
    # Drop the first few rows where rolling window is incomplete (NaNs)
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
    
    df_processed = calculate_v3_features(df, window_size=100)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_processed.to_csv(output_path, index=False)
    print(f" -> Saved {len(df_processed)} fingerprint vectors to {output_path}")

def main():
    print("--- Phase 2: Feature Engineering (v3.0) ---")
    
    # Process ALL 4 datasets (including the new attacks)
    process_file("normal_data.csv")
    process_file("attack_intercept.csv")
    process_file("attack_blinding.csv")
    process_file("attack_timeshift.csv")
    
    print("--- Processing Complete ---")

if __name__ == "__main__":
    main()