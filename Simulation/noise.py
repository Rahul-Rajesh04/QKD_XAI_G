__author__ = "Rahul Rajesh 2360445"

import numpy as np
import core as bb
from manager import QKDExperiment

class NoisyAlice(bb.Alice):
    def __init__(self, n_qubits, p_fail):
        super().__init__(n_qubits)
        self.p_fail = p_fail

    def prepare_qubits(self):
        super().prepare_qubits()
        
        fail_mask = (self.bases == 1) & (np.random.random(self.n) < self.p_fail)
        
        if np.any(fail_mask):
            states_to_fix = self.state_matrix[:, fail_mask]
            reverted_states = bb.H_GATE @ states_to_fix
            self.state_matrix[:, fail_mask] = reverted_states

class NoisyBob(bb.Bob):
    def __init__(self, n_qubits, p_fail):
        super().__init__(n_qubits)
        self.p_fail = p_fail
        
    def measure_qubits(self, state_matrix):
        self.bases = np.random.randint(0, 2, self.n)
        current_states = state_matrix.copy()

        diag_indices = (self.bases == 1)
        fail_mask = (np.random.random(self.n) < self.p_fail)
        effective_rotation_mask = diag_indices & (~fail_mask)
        
        if np.any(effective_rotation_mask):
            cols = current_states[:, effective_rotation_mask]
            current_states[:, effective_rotation_mask] = bb.H_GATE @ cols

        prob_zero = np.abs(current_states[0, :]) ** 2
        rng = np.random.random(self.n)
        self.measured_bits = np.where(rng < prob_zero, 0, 1)

class NoisyQuantumChannel(bb.QuantumChannel):
    def transmit(self, state_matrix):
        fluctuation = np.random.uniform(-0.25, 0.25)
        current_noise_rate = 0.15 * (1 + fluctuation)
        
        n_qubits = state_matrix.shape[1]
        num_errors = int(n_qubits * current_noise_rate)
        
        if num_errors > 0:
            error_indices = np.random.choice(n_qubits, num_errors, replace=False)
            state_matrix[:, error_indices] = state_matrix[::-1, error_indices]
            
        return state_matrix

class NoisyQKDExperiment(QKDExperiment):
    def __init__(self, n_qubits, p_fail):
        super().__init__(n_qubits)
        self.p_fail = p_fail
        
    def build_phase(self):
        self.alice = NoisyAlice(self.n, self.p_fail)
        self.bob = NoisyBob(self.n, self.p_fail)
        self.q_channel = NoisyQuantumChannel()
        self.c_channel = bb.ClassicalChannel()