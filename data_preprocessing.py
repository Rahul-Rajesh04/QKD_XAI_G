"""
data_preprocessing.py
Phase 2: Feature Engineering (v3.0)
Applies a 500-event rolling micro-sifting window to extract six-dimensional
feature vectors from raw QKD event logs.
"""
__author__ = "Rahul Rajesh 2360445"

import pandas as pd
import numpy as np
import os

from config.logging_config import configure_logging, get_logger

configure_logging()
log = get_logger("qkd.preprocess")


def calculate_v3_features(df: pd.DataFrame, window_size: int = 500) -> pd.DataFrame:
    """
    Apply rolling micro-sifting over a window of `window_size` events.
    Produces three QBER variants (overall, rectilinear, diagonal) merged
    with instantaneous APD hardware vitals.

    Args:
        df: Raw event DataFrame with columns alice_bit, alice_basis,
            bob_basis, bob_bit, basis_match, error, detector_voltage,
            timing_jitter, photon_count_rate, label.
        window_size: Number of consecutive events per rolling window (~500).

    Returns:
        Processed DataFrame with 7 columns (6 features + label), NaN rows dropped.
    """
    log.debug(f"Calculating micro-sifting stats (window={window_size})...")

    df['sifted'] = df['basis_match']

    is_rect = df['alice_basis'] == 0
    is_diag = df['alice_basis'] == 1

    # CRITICAL: only count errors on SIFTED events (basis_match=1).
    # The raw `error` column is non-zero even when bases mismatch
    # (Bob's bit is random there), which would inflate QBER to ~50%.
    sifted_mask      = df['sifted'].astype(bool)
    sifted_error     = df['error'] & sifted_mask

    df['error_rect'] = sifted_error & is_rect
    df['error_diag'] = sifted_error & is_diag

    r_sifted      = df['sifted'].rolling(window=window_size).sum()
    r_error_total = sifted_error.rolling(window=window_size).sum()
    r_error_rect  = df['error_rect'].rolling(window=window_size).sum()
    r_error_diag  = df['error_diag'].rolling(window=window_size).sum()

    r_count_rect  = (sifted_mask & is_rect).rolling(window=window_size).sum()
    r_count_diag  = (sifted_mask & is_diag).rolling(window=window_size).sum()

    df['qber_overall']     = (r_error_total / r_sifted    ).fillna(0.0).replace([np.inf, -np.inf], 0.0)
    df['qber_rectilinear'] = (r_error_rect  / r_count_rect).fillna(0.0).replace([np.inf, -np.inf], 0.0)
    df['qber_diagonal']    = (r_error_diag  / r_count_diag).fillna(0.0).replace([np.inf, -np.inf], 0.0)

    features = [
        'qber_overall',
        'qber_rectilinear',
        'qber_diagonal',
        'detector_voltage',
        'timing_jitter',
        'photon_count_rate',
        'label',
    ]

    df_final = df[features].dropna()
    log.debug(f"Feature extraction complete: {len(df_final):,} vectors produced.")
    return df_final


def process_file(filename: str) -> None:
    """Process a single raw CSV file and save the feature-engineered result."""
    input_path  = f"Datasets/Raw/{filename}"
    output_path = f"Datasets/Processed/{filename}"

    if not os.path.exists(input_path):
        log.warning(f"Skipping '{filename}' — file not found at {input_path}")
        return

    log.info(f"Processing '{filename}'...")
    df = pd.read_csv(input_path)
    log.debug(f"  Loaded {len(df):,} raw events from {input_path}")

    df_processed = calculate_v3_features(df, window_size=500)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df_processed.to_csv(output_path, index=False)
    log.info(f"  Saved {len(df_processed):,} fingerprint vectors to '{output_path}'")


def main() -> None:
    log.info("--- Phase 2: Feature Engineering (v3.0) ---")

    process_file("normal_data.csv")
    process_file("attack_intercept.csv")
    process_file("attack_blinding.csv")
    process_file("attack_timeshift.csv")

    log.info("--- Processing Complete ---")


if __name__ == "__main__":
    main()