# -*- coding: utf-8 -*-
"""
Optimized Noise Models for BB84
-------------------------------
File: Simulation/noise.py
Improvements:
- Vectorized Noise Injection (Instant speed)
- Corrected Linear Algebra (Failure to rotate vs Bit flipping)
"""

import numpy as np

# CRITICAL UPDATES: Import from new file names
import core as bb
from manager import QKDExperiment

class NoisyAlice(bb.Alice):
    def __init__(self, n_qubits, p_fail):
        super().__init__(n_qubits)
        self.p_fail = p_fail

    def prepare_qubits(self):
        # 1. Generate perfect qubits first (using Base Alice)
        super().prepare_qubits()
        
        # 2. Simulate Hardware Failure (P_H_FAIL)
        # Failure Scenario: Alice INTENDED to rotate to Diagonal, but hardware stuck at Rectilinear.
        # Logic: If Basis=1, we already applied H in step 1. 
        # To simulate "failure to rotate", we apply H again (H*H = I) to undo it.
        
        # Find bits where Basis=1 AND Random Roll < P_Fail
        # Create a boolean mask of "Failed Hardware Events"
        fail_mask = (self.bases == 1) & (np.random.random(self.n) < self.p_fail)
        
        if np.any(fail_mask):
            # Extract columns that need "undoing"
            states_to_fix = self.state_matrix[:, fail_mask]
            # Apply H again to revert them to standard basis
            reverted_states = bb.H_GATE @ states_to_fix
            # Update matrix
            self.state_matrix[:, fail_mask] = reverted_states


class NoisyBob(bb.Bob):
    def __init__(self, n_qubits, p_fail):
        super().__init__(n_qubits)
        self.p_fail = p_fail
        
    def measure_qubits(self, state_matrix):
        # We override measurement to inject failure BEFORE the standard measure logic
        
        # Note: Bob's hardware failure logic is tricky to vectorize cleanly 
        # because the Base Bob generates bases INSIDE measure_qubits.
        # So we reimplement the measurement logic here with noise.
        
        self.bases = np.random.randint(0, 2, self.n)
        current_states = state_matrix.copy()

        # Identify where Bob WANTS to rotate (Diagonal)
        diag_indices = (self.bases == 1)
        
        # Identify where Hardware FAILS to rotate
        # (Bob wants Diagonal, but Hardware stays Rectilinear)
        # So effective rotation mask is: (Basis=1) AND NOT (Failure)
        fail_mask = (np.random.random(self.n) < self.p_fail)
        effective_rotation_mask = diag_indices & (~fail_mask)
        
        # Apply Rotation only where hardware worked
        if np.any(effective_rotation_mask):
            cols = current_states[:, effective_rotation_mask]
            current_states[:, effective_rotation_mask] = bb.H_GATE @ cols

        # Standard Born Rule & Collapse
        prob_zero = np.abs(current_states[0, :]) ** 2
        rng = np.random.random(self.n)
        self.measured_bits = np.where(rng < prob_zero, 0, 1)


class NoisyQuantumChannel(bb.QuantumChannel):
    def transmit(self, state_matrix):
        # Calculate variable noise rate (Environmental fluctuation)
        # Range: ~11% to ~19%
        fluctuation = np.random.uniform(-0.25, 0.25)
        current_noise_rate = 0.15 * (1 + fluctuation)
        
        # Determine how many bits to flip
        n_qubits = state_matrix.shape[1]
        num_errors = int(n_qubits * current_noise_rate)
        
        if num_errors > 0:
            # Pick random indices to corrupt
            error_indices = np.random.choice(n_qubits, num_errors, replace=False)
            
            # Apply X-Gate (Bit Flip)
            # Efficient NumPy swap: Row 0 <-> Row 1
            # |0> ([1,0]) becomes |1> ([0,1])
            state_matrix[:, error_indices] = state_matrix[::-1, error_indices]
            
        return state_matrix


class NoisyQKDExperiment(QKDExperiment):
    def __init__(self, n_qubits, p_fail):
        super().__init__(n_qubits)
        self.p_fail = p_fail
        
    def build_phase(self):
        # Inject the Noisy Actors
        self.alice = NoisyAlice(self.n, self.p_fail)
        self.bob = NoisyBob(self.n, self.p_fail)
        self.q_channel = NoisyQuantumChannel()
        self.c_channel = bb.ClassicalChannel()