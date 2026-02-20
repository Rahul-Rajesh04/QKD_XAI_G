"""
Simulation/core.py
Vectorized BB84 quantum engine.
Uses NumPy state matrices for high-throughput simulation of photon
encoding, channel transmission, measurement, and key sifting.
"""
__author__ = "Rahul Rajesh 2360445"

import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Basis kets and Hadamard gate (reused across all simulations)
# ---------------------------------------------------------------------------
KET_0: NDArray[np.float64] = np.array([1.0, 0.0])
KET_1: NDArray[np.float64] = np.array([0.0, 1.0])

_K: float = 1.0 / np.sqrt(2.0)
H_GATE: NDArray[np.float64] = np.array([[_K, _K], [_K, -_K]])


class Alice:
    """
    Alice's side of the BB84 protocol.
    Encodes bits onto photon states using randomly chosen bases
    (rectilinear=0, diagonal=1) via vectorized state matrix operations.
    """

    def __init__(self, n_qubits: int) -> None:
        self.n: int = n_qubits
        self.bits:         NDArray[np.int_] | None = None
        self.bases:        NDArray[np.int_] | None = None
        self.key:          NDArray[np.int_] | None = None
        self.state_matrix: NDArray[np.float64] = np.zeros((2, self.n))

    def prepare_qubits(self) -> None:
        """Randomly choose bits and bases, build state vectors, apply H for diagonal encoding."""
        self.bits  = np.random.randint(0, 2, self.n)
        self.bases = np.random.randint(0, 2, self.n)

        self.state_matrix[0, :] = (self.bits == 0).astype(float)
        self.state_matrix[1, :] = (self.bits == 1).astype(float)

        diag_indices: NDArray[np.intp] = np.where(self.bases == 1)[0]
        if len(diag_indices) > 0:
            states_to_rotate = self.state_matrix[:, diag_indices]
            self.state_matrix[:, diag_indices] = H_GATE @ states_to_rotate

    def sift_key(self, bob_bases: NDArray[np.int_]) -> NDArray[np.int_]:
        """Retain only bits where Alice's and Bob's bases matched."""
        match_mask = self.bases == bob_bases
        self.key   = self.bits[match_mask]
        return self.key


class Bob:
    """
    Bob's side of the BB84 protocol.
    Measures incoming photon states in a randomly chosen basis
    using the Born rule via vectorized probability computation.
    """

    def __init__(self, n_qubits: int) -> None:
        self.n: int = n_qubits
        self.bases:         NDArray[np.int_] | None = None
        self.measured_bits: NDArray[np.int_] | None = None
        self.key:           NDArray[np.int_] | None = None

    def measure_qubits(self, state_matrix: NDArray[np.float64]) -> None:
        """
        Randomly select measurement bases; apply H for diagonal basis;
        sample outcomes from the Born rule probability distribution.
        """
        self.bases = np.random.randint(0, 2, self.n)

        current_states: NDArray[np.float64] = state_matrix.copy()
        diag_indices: NDArray[np.intp] = np.where(self.bases == 1)[0]
        if len(diag_indices) > 0:
            current_states[:, diag_indices] = H_GATE @ current_states[:, diag_indices]

        prob_zero: NDArray[np.float64] = np.abs(current_states[0, :]) ** 2
        rng: NDArray[np.float64]       = np.random.random(self.n)
        self.measured_bits = np.where(rng < prob_zero, 0, 1)

    def sift_key(self, alice_bases: NDArray[np.int_]) -> NDArray[np.int_]:
        """Retain only bits where Bob's and Alice's bases matched."""
        match_mask = self.bases == alice_bases
        self.key   = self.measured_bits[match_mask]
        return self.key


class QuantumChannel:
    """Ideal (noiseless) quantum channel — pass-through only."""

    def transmit(self, state_matrix: NDArray[np.float64]) -> NDArray[np.float64]:
        return state_matrix


class ClassicalChannel:
    """Classical authenticated channel used for basis reconciliation."""

    @staticmethod
    def calc_error_rate(
        key_a: NDArray[np.int_],
        key_b: NDArray[np.int_],
    ) -> float:
        """Compute QBER between Alice's and Bob's sifted keys."""
        if len(key_a) == 0:
            return 0.0
        errors: int = int(np.count_nonzero(key_a != key_b))
        return errors / len(key_a)