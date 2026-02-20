__author__ = "Rahul Rajesh 2360445"

import core as bb

class QKDExperiment:
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.alice = None
        self.bob = None
        self.q_channel = None
        self.c_channel = None
        
        self.final_key_alice = None
        self.final_key_bob = None
        self.error_rate = 0.0

    def build_phase(self):
        self.alice = bb.Alice(self.n)
        self.bob = bb.Bob(self.n)
        self.q_channel = bb.QuantumChannel()
        self.c_channel = bb.ClassicalChannel()

    def run_phase(self):
        self.alice.prepare_qubits()
        states_in_transit = self.q_channel.transmit(self.alice.state_matrix)
        self.bob.measure_qubits(states_in_transit)

    def key_generation_phase(self):
        self.bob.sift_key(self.alice.bases)
        self.alice.sift_key(self.bob.bases)
        self.final_key_alice = self.alice.key
        self.final_key_bob = self.bob.key

    def validation_phase(self, check_ratio=0.5):
        if len(self.final_key_alice) == 0:
            print("Warning: No key bits generated (Sifting yielded 0 bits).")
            return

        n_check = int(len(self.final_key_alice) * check_ratio)
        
        check_a = self.final_key_alice[:n_check]
        check_b = self.final_key_bob[:n_check]
        
        self.error_rate = self.c_channel.calc_error_rate(check_a, check_b)
        
        self.final_key_alice = self.final_key_alice[n_check:]
        self.final_key_bob = self.final_key_bob[n_check:]

    def execute(self):
        self.build_phase()
        self.run_phase()
        self.key_generation_phase()
        self.validation_phase()
        return self.error_rate