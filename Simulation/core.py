__author__ = "Rahul Rajesh 2360445"

import numpy as np

KET_0 = np.array([1.0, 0.0])
KET_1 = np.array([0.0, 1.0])

K = 1.0 / np.sqrt(2.0)
H_GATE = np.array([[K, K], [K, -K]])  

class Alice:
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.bits = None      
        self.bases = None     
        self.key = None       
        
        self.state_matrix = np.zeros((2, self.n))

    def prepare_qubits(self):
        self.bits = np.random.randint(0, 2, self.n)
        self.bases = np.random.randint(0, 2, self.n)

        self.state_matrix[0, :] = (self.bits == 0).astype(float)
        self.state_matrix[1, :] = (self.bits == 1).astype(float)

        diag_indices = np.where(self.bases == 1)[0]
        
        if len(diag_indices) > 0:
            states_to_rotate = self.state_matrix[:, diag_indices]
            rotated_states = H_GATE @ states_to_rotate
            self.state_matrix[:, diag_indices] = rotated_states

    def sift_key(self, bob_bases):
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
        self.bases = np.random.randint(0, 2, self.n)
        
        current_states = state_matrix.copy()

        diag_indices = np.where(self.bases == 1)[0]
        if len(diag_indices) > 0:
            states_to_rotate = current_states[:, diag_indices]
            current_states[:, diag_indices] = H_GATE @ states_to_rotate

        prob_zero = np.abs(current_states[0, :]) ** 2

        rng = np.random.random(self.n)
        
        self.measured_bits = np.where(rng < prob_zero, 0, 1)

    def sift_key(self, alice_bases):
        match_mask = (self.bases == alice_bases)
        self.key = self.measured_bits[match_mask]
        return self.key


class QuantumChannel:
    def transmit(self, state_matrix):
        return state_matrix

class ClassicalChannel:
    @staticmethod
    def calc_error_rate(key_a, key_b):
        if len(key_a) == 0: return 0.0
        
        errors = np.count_nonzero(key_a != key_b)
        return errors / len(key_a)