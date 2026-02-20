__author__ = "Rahul Rajesh 2360445"

import numpy as np
from scipy.linalg import logm

I = np.array([[1, 0], [0, 1]], dtype=complex)
X = np.array([[0, 1], [1, 0]], dtype=complex)
Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z = np.array([[1, 0], [0, -1]], dtype=complex)
H = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)

class QState:
    def __init__(self, matrix=None):
        if matrix is None:
            self.rho = np.array([[1, 0], [0, 0]], dtype=complex)
        else:
            self.rho = np.array(matrix, dtype=complex)
            self.rho = self.rho / np.trace(self.rho)

    @classmethod
    def from_label(cls, label):
        if label == 'H': ket = np.array([[1], [0]])
        elif label == 'V': ket = np.array([[0], [1]])
        elif label == 'D': ket = (1 / np.sqrt(2)) * np.array([[1], [1]])
        elif label == 'A': ket = (1 / np.sqrt(2)) * np.array([[1], [-1]])
        else: raise ValueError(f"Unknown label: {label}")
        return cls(np.outer(ket, ket.conj()))

    def apply_unitary(self, U):
        self.rho = U @ self.rho @ U.conj().T

    def apply_depolarizing_noise(self, p):
        noise = 0.5 * I
        self.rho = (1 - p) * self.rho + p * noise

    def measure(self, basis):
        if basis == 'rectilinear':
            P0 = np.array([[1, 0], [0, 0]])
            P1 = np.array([[0, 0], [0, 1]])
        elif basis == 'diagonal':
            d = (1/np.sqrt(2)) * np.array([[1], [1]])
            a = (1/np.sqrt(2)) * np.array([[1], [-1]])
            P0 = np.outer(d, d.conj())
            P1 = np.outer(a, a.conj())
        else:
            raise ValueError("Unknown basis")

        prob_0 = np.real(np.trace(P0 @ self.rho))
        prob_1 = np.real(np.trace(P1 @ self.rho))
        
        total = prob_0 + prob_1
        prob_0, prob_1 = prob_0/total, prob_1/total

        result = np.random.choice([0, 1], p=[prob_0, prob_1])
        if result == 0:
            self.rho = P0 / np.trace(P0 @ self.rho)
        else:
            self.rho = P1 / np.trace(P1 @ self.rho)
        return result

    def get_entropy(self):
        evals = np.linalg.eigvalsh(self.rho)
        evals = evals[evals > 1e-10]
        return -np.sum(evals * np.log2(evals))

    def get_fidelity(self, target_label):
        target = QState.from_label(target_label)
        return np.real(np.trace(target.rho @ self.rho))

if __name__ == "__main__":
    print("--- PHYSICS KERNEL TEST ---")
    q = QState.from_label('H')
    print(f"Init Entropy: {q.get_entropy():.4f}")
    
    q.apply_depolarizing_noise(0.2)
    print(f"Post-Noise Entropy: {q.get_entropy():.4f}")
    
    res = q.measure('rectilinear')
    print(f"Measurement: {res}")
    print(f"Final Entropy: {q.get_entropy():.4f}")