# -*- coding: utf-8 -*-
"""
Attacker (Eve: Intercept-Resend)
--------------------------------
File: Simulation/attacker.py
"""
import numpy as np

# CRITICAL UPDATES: Import from new file names
import core as bb
from manager import QKDExperiment

class Eve(bb.Bob):
    """
    Eve is technically a 'Bob' (Receiver) who also acts as an 'Alice' (Sender).
    She measures everything and resends what she measured.
    """
    def __init__(self, n_qubits):
        super().__init__(n_qubits)
        self.reprepared_states = None

    def intercept_and_resend(self, state_matrix):
        # 1. Eve Measures the intercepted states
        # (This populates self.measured_bits and self.bases)
        self.measure_qubits(state_matrix)
        
        # 2. Eve Prepares NEW states based on her measurement
        # If she measured 0, she sends |0> (or |+> depending on HER basis)
        # If she measured 1, she sends |1> (or |->)
        
        # Initialize new state matrix
        self.reprepared_states = np.zeros((2, self.n))
        
        # Set computational basis states based on measurement
        # measured_bits is now an array of 0s and 1s
        self.reprepared_states[0, :] = (self.measured_bits == 0).astype(float)
        self.reprepared_states[1, :] = (self.measured_bits == 1).astype(float)
        
        # Apply Hadamard where Eve used Diagonal Basis
        diag_indices = np.where(self.bases == 1)[0]
        if len(diag_indices) > 0:
            states_to_rotate = self.reprepared_states[:, diag_indices]
            self.reprepared_states[:, diag_indices] = bb.H_GATE @ states_to_rotate
            
        return self.reprepared_states

class EveQuantumChannel(bb.QuantumChannel):
    def __init__(self, n_qubits):
        self.eve = Eve(n_qubits)
        
    def transmit(self, state_matrix):
        # The Attack:
        # 1. Eve intercepts inputs
        # 2. Eve measures and generates new states
        # 3. Eve sends THOSE new states to Bob
        return self.eve.intercept_and_resend(state_matrix)

class EveQKDExperiment(QKDExperiment):
    def build_phase(self):
        super().build_phase()
        # Replace the perfect channel with Eve's Channel
        self.q_channel = EveQuantumChannel(self.n)