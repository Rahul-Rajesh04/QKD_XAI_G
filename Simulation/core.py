# -*- coding: utf-8 -*-
"""
Core Quantum Entities (Alice, Bob, Channels)
--------------------------------------------
File: Simulation/core.py
"""
import numpy as np

# --- QUANTUM CONSTANTS ---
# Standard Basis
KET_0 = np.array([1.0, 0.0])
KET_1 = np.array([0.0, 1.0])

# Diagonal Basis Constants (1/sqrt(2))
K = 1.0 / np.sqrt(2.0)
H_GATE = np.array([[K, K], [K, -K]])  # Hadamard Matrix

class Alice:
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.bits = None      # The secret bits (0 or 1)
        self.bases = None     # The bases (0=Rectilinear, 1=Diagonal)
        self.key = None       # The final sifted key
        
        # Pre-allocate state matrix (2 rows, n columns)
        self.state_matrix = np.zeros((2, self.n))

    def prepare_qubits(self):
        """
        Vectorized generation of qubits.
        1. Generates all random bits and bases at once.
        2. Creates the quantum states in a single matrix operation.
        """
        # 1. Random Generation
        self.bits = np.random.randint(0, 2, self.n)
        self.bases = np.random.randint(0, 2, self.n)

        # 2. Create States based on Bit values (Rectilinear default)
        # If bit is 0 -> [1, 0], If bit is 1 -> [0, 1]
        self.state_matrix[0, :] = (self.bits == 0).astype(float)
        self.state_matrix[1, :] = (self.bits == 1).astype(float)

        # 3. Apply Hadamard Rotation where Basis = 1 (Diagonal)
        # We find indices where basis is diagonal
        diag_indices = np.where(self.bases == 1)[0]
        
        if len(diag_indices) > 0:
            # Extract only the columns that need rotation
            states_to_rotate = self.state_matrix[:, diag_indices]
            # Apply matrix multiplication: H * State
            rotated_states = H_GATE @ states_to_rotate
            # Update the main matrix
            self.state_matrix[:, diag_indices] = rotated_states

    def sift_key(self, bob_bases):
        """Compares bases with Bob and keeps bits where bases match."""
        # Vectorized comparison (True/False array)
        match_mask = (self.bases == bob_bases)
        self.key = self.bits[match_mask]
        return self.key


class Bob:
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.bases = None
        self.measured_bits = None
        self.key = None
        
    def measure_qubits(self, state_matrix):
        """
        Vectorized measurement.
        1. Bob chooses bases.
        2. Applies H-gate to incoming states where Bob's basis is Diagonal.
        3. Calculates probability and collapses wave function.
        """
        self.bases = np.random.randint(0, 2, self.n)
        
        # Work on a copy so we don't modify the channel's data
        current_states = state_matrix.copy()

        # 1. Rotate Basis (if Bob measures in Diagonal)
        diag_indices = np.where(self.bases == 1)[0]
        if len(diag_indices) > 0:
            states_to_rotate = current_states[:, diag_indices]
            current_states[:, diag_indices] = H_GATE @ states_to_rotate

        # 2. Born Rule: Probability of measuring 0 is |amplitude_0|^2
        # current_states[0, :] is the top component (amplitude for 0)
        prob_zero = np.abs(current_states[0, :]) ** 2

        # 3. Collapse (Simulate measurement)
        # Generate N random numbers [0, 1]
        rng = np.random.random(self.n)
        
        # If random number < prob_zero, outcome is 0. Else 1.
        self.measured_bits = np.where(rng < prob_zero, 0, 1)

    def sift_key(self, alice_bases):
        """Compares bases with Alice and keeps bits where bases match."""
        match_mask = (self.bases == alice_bases)
        self.key = self.measured_bits[match_mask]
        return self.key


class QuantumChannel:
    """Base Channel - Perfectly transmits qubits."""
    def transmit(self, state_matrix):
        # In the base class, we just return the states as-is.
        return state_matrix

class ClassicalChannel:
    """Helper for comparing keys."""
    @staticmethod
    def calc_error_rate(key_a, key_b):
        if len(key_a) == 0: return 0.0
        
        # Vectorized error counting
        errors = np.count_nonzero(key_a != key_b)
        return errors / len(key_a)