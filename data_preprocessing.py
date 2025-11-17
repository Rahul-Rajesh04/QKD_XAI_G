import pandas as pd
import numpy as np
import os

def calculate_features(df, window_size=100):
    """
    Computes derived features for the QKD dataset.
    1. Simulated Time: Assumes 1ms gap between pulses.
    2. Rolling QBER: The error rate over the last 'window_size' events.
    """
    # --- 1. Simulate Time ---
    # Convert index to seconds (1ms per pulse)
    df['time_sec'] = df['timestamp_idx'] * 0.001
    
    # --- 2. Calculate Rolling QBER ---
    # Calculate rolling sums for Errors and Matches (Sifted events)
    r_error = df['error'].rolling(window=window_size, min_periods=1).sum()
    r_match = df['basis_match'].rolling(window=window_size, min_periods=1).sum()
    
    # Calculate QBER (Errors / Matches)
    df['qber_rolling'] = r_error / r_match
    
    # Handle edge cases:
    # 1. Fill initial NaNs (start of file) with 0.0
    # 2. Replace Infinity (division by zero if no matches yet) with 0.0
    df['qber_rolling'] = df['qber_rolling'].fillna(0.0).replace([np.inf, -np.inf], 0.0)
    
    return df

def process_file(input_csv, output_csv):
    if not os.path.exists(input_csv):
        print(f"Skipping {input_csv}: File not found.")
        return

    print(f"Processing {input_csv}...")
    df = pd.read_csv(input_csv)
    
    # Add features
    df_processed = calculate_features(df, window_size=50)
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    
    # Save processed file
    df_processed.to_csv(output_csv, index=False)
    print(f" -> Saved to {output_csv}")
    print(f"    Avg QBER: {df_processed['qber_rolling'].mean():.4f}")

def main():
    print("--- Phase 2: Feature Engineering ---")
    
    # Process all datasets: Read Raw -> Save Processed
    process_file("Datasets/Raw/normal_data.csv", "Datasets/Processed/normal_data.csv")
    process_file("Datasets/Raw/attack_intercept.csv", "Datasets/Processed/attack_intercept.csv")
    process_file("Datasets/Raw/normal_noiseless.csv", "Datasets/Processed/normal_noiseless.csv")
    
    print("--- Processing Complete ---")

if __name__ == "__main__":
    main()