"""
tests/test_preprocessing.py
Pytest unit tests for data_preprocessing.py (micro-sifting feature engineering).

Tests verify correctness of the rolling-window QBER calculation,
output schema, absence of NaN/Inf, and boundary conditions.

Run with:
    conda activate qkd_env
    pytest tests/test_preprocessing.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
import pandas as pd
import pytest

from data_preprocessing import calculate_v3_features


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------

def _make_df(
    n: int = 1000,
    error_rate: float = 0.0,
    basis_match_rate: float = 0.5,
    voltage: float = 3.3,
    jitter: float = 1.2,
    counts: float = 0.25,
    label: str = "normal",
) -> pd.DataFrame:
    """Build a synthetic raw-event DataFrame with controlled error rate."""
    np.random.seed(42)
    alice_basis = np.random.randint(0, 2, n)
    bob_basis   = alice_basis.copy()

    # Introduce deliberate basis mismatches
    mismatch_mask = np.random.random(n) > basis_match_rate
    bob_basis[mismatch_mask] = 1 - alice_basis[mismatch_mask]

    alice_bit = np.random.randint(0, 2, n)
    bob_bit   = alice_bit.copy()

    # Introduce errors only on sifted bits
    match_mask  = alice_basis == bob_basis
    error_mask  = match_mask & (np.random.random(n) < error_rate)
    bob_bit[error_mask] = 1 - alice_bit[error_mask]

    return pd.DataFrame({
        "alice_bit":          alice_bit,
        "alice_basis":        alice_basis,
        "bob_basis":          bob_basis,
        "bob_bit":            bob_bit,
        "basis_match":        match_mask.astype(int),
        "error":              (alice_bit != bob_bit).astype(int),
        "detector_voltage":   np.full(n, voltage),
        "timing_jitter":      np.full(n, jitter),
        "photon_count_rate":  np.full(n, counts),
        "label":              label,
    })


# ----------------------------------------------------------------
# Tests: Output Schema
# ----------------------------------------------------------------

class TestOutputSchema:
    def test_output_columns_exact(self) -> None:
        """Output DataFrame must have exactly the 7 expected columns."""
        df      = _make_df(n=1000)
        result  = calculate_v3_features(df, window_size=100)
        expected = {
            "qber_overall", "qber_rectilinear", "qber_diagonal",
            "detector_voltage", "timing_jitter", "photon_count_rate", "label",
        }
        assert set(result.columns) == expected

    def test_output_row_count_less_than_or_equal_input(self) -> None:
        """
        Rolling window with fillna(0.0) means NaNs are pre-filled before dropna().
        Output can equal n when there are no remaining NaN rows.
        Invariant: output rows must be <= n and >= n - window_size.
        """
        n, w   = 1000, 100
        df     = _make_df(n=n)
        result = calculate_v3_features(df, window_size=w)
        assert len(result) <= n
        assert len(result) >= n - w


# ----------------------------------------------------------------
# Tests: QBER Correctness
# ----------------------------------------------------------------

class TestQBERValues:
    def test_zero_error_yields_zero_qber(self) -> None:
        """With error_rate=0, all three QBER columns must be 0.0."""
        df     = _make_df(n=1000, error_rate=0.0)
        result = calculate_v3_features(df, window_size=100)
        assert (result["qber_overall"] == 0.0).all()
        assert (result["qber_rectilinear"] == 0.0).all()
        assert (result["qber_diagonal"] == 0.0).all()

    def test_high_error_rate_detected(self) -> None:
        """With error_rate≈0.25, rolling QBER should exceed 0.10 in the steady state."""
        df     = _make_df(n=2000, error_rate=0.25)
        result = calculate_v3_features(df, window_size=100)
        steady = result.iloc[50:]   # skip warmup edge effects
        assert steady["qber_overall"].mean() > 0.10

    def test_qber_values_in_unit_interval(self) -> None:
        """All QBER values must lie in [0, 1]."""
        df     = _make_df(n=1000, error_rate=0.15)
        result = calculate_v3_features(df, window_size=100)
        for col in ("qber_overall", "qber_rectilinear", "qber_diagonal"):
            assert result[col].between(0.0, 1.0).all(), f"Out-of-range values in '{col}'"


# ----------------------------------------------------------------
# Tests: Data Quality
# ----------------------------------------------------------------

class TestDataQuality:
    def test_no_nan_in_output(self) -> None:
        """Output DataFrame must not contain any NaN values."""
        df     = _make_df(n=1000)
        result = calculate_v3_features(df, window_size=100)
        assert not result.isnull().any().any()

    def test_no_inf_in_output(self) -> None:
        """Output DataFrame must not contain any Inf values."""
        df      = _make_df(n=1000)
        result  = calculate_v3_features(df, window_size=100)
        numeric = result.select_dtypes(include="number")
        assert not np.isinf(numeric.values).any()

    def test_hardware_vitals_passthrough(self) -> None:
        """Hardware vitals should appear verbatim in the output (constant test)."""
        df     = _make_df(n=1000, voltage=9.0, jitter=0.05, counts=0.99)
        result = calculate_v3_features(df, window_size=100)
        assert (result["detector_voltage"] == 9.0).all()
        assert (result["timing_jitter"]    == 0.05).all()
        assert (result["photon_count_rate"] == 0.99).all()
