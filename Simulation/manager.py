# -*- coding: utf-8 -*-
"""
Experiment Manager (Orchestrator)
---------------------------------
File: Simulation/manager.py
"""

# CRITICAL UPDATE: Import from the new 'core.py' file
import core as bb

class QKDExperiment:
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.alice = None
        self.bob = None
        self.q_channel = None
        self.c_channel = None
        
        # Results storage
        self.final_key_alice = None
        self.final_key_bob = None
        self.error_rate = 0.0

    def build_phase(self):
        """Initialize the entities."""
        self.alice = bb.Alice(self.n)
        self.bob = bb.Bob(self.n)
        self.q_channel = bb.QuantumChannel()
        self.c_channel = bb.ClassicalChannel()

    def run_phase(self):
        """
        The Quantum Transmission Phase.
        1. Alice prepares N qubits.
        2. Channel transmits them.
        3. Bob measures them.
        """
        # 1. Alice creates states
        self.alice.prepare_qubits()
        
        # 2. Transmission (Channel might add noise/attacks later)
        # We pass the matrix directly now (Vectorized)
        states_in_transit = self.q_channel.transmit(self.alice.state_matrix)
        
        # 3. Bob measures
        self.bob.measure_qubits(states_in_transit)

    def key_generation_phase(self):
        """
        Sifting (Basis Reconciliation).
        Alice and Bob exchange bases and discard mismatches.
        """
        # Alice tells Bob her bases, Bob sifts his key
        self.bob.sift_key(self.alice.bases)
        
        # Bob tells Alice his bases, Alice sifts her key
        self.alice.sift_key(self.bob.bases)
        
        self.final_key_alice = self.alice.key
        self.final_key_bob = self.bob.key

    def validation_phase(self, check_ratio=0.5):
        """
        Error Check.
        They sacrifice a portion of the key to estimate QBER.
        """
        if len(self.final_key_alice) == 0:
            print("Warning: No key bits generated (Sifting yielded 0 bits).")
            return

        # Determine how many bits to check
        n_check = int(len(self.final_key_alice) * check_ratio)
        
        # Slice the arrays
        check_a = self.final_key_alice[:n_check]
        check_b = self.final_key_bob[:n_check]
        
        # Calculate Error Rate
        self.error_rate = self.c_channel.calc_error_rate(check_a, check_b)
        
        # Keep the remaining secure key
        self.final_key_alice = self.final_key_alice[n_check:]
        self.final_key_bob = self.final_key_bob[n_check:]

    def execute(self):
        """Runs the full protocol in order."""
        self.build_phase()
        self.run_phase()
        self.key_generation_phase()
        self.validation_phase()
        return self.error_rate