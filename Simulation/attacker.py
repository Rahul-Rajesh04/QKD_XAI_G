__author__ = "Rahul Rajesh 2360445"

import numpy as np
import core as bb
from manager import QKDExperiment

class Eve(bb.Bob):
    def __init__(self, n_qubits):
        super().__init__(n_qubits)
        self.reprepared_states = None

    def intercept_and_resend(self, state_matrix):
        self.measure_qubits(state_matrix)
        
        self.reprepared_states = np.zeros((2, self.n))
        
        self.reprepared_states[0, :] = (self.measured_bits == 0).astype(float)
        self.reprepared_states[1, :] = (self.measured_bits == 1).astype(float)
        
        diag_indices = np.where(self.bases == 1)[0]
        if len(diag_indices) > 0:
            states_to_rotate = self.reprepared_states[:, diag_indices]
            self.reprepared_states[:, diag_indices] = bb.H_GATE @ states_to_rotate
            
        return self.reprepared_states

class EveQuantumChannel(bb.QuantumChannel):
    def __init__(self, n_qubits):
        self.eve = Eve(n_qubits)
        
    def transmit(self, state_matrix):
        return self.eve.intercept_and_resend(state_matrix)

class EveQKDExperiment(QKDExperiment):
    def build_phase(self):
        super().build_phase()
        self.q_channel = EveQuantumChannel(self.n)