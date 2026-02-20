"""
Simulation/core_real.py
Density-matrix quantum physics kernel.
Implements single-qubit quantum states as 2×2 complex density matrices (ρ)
with depolarizing noise, projective measurement (Born rule + Lüders collapse),
von Neumann entropy, and state fidelity.
"""
__author__ = "Rahul Rajesh 2360445"

import numpy as np
from numpy.typing import NDArray
from scipy.linalg import logm  # noqa: F401 (available for future use)

# ---------------------------------------------------------------------------
# Pauli matrices and Hadamard gate
# ---------------------------------------------------------------------------
I: NDArray[np.complex128] = np.array([[1, 0], [0, 1]], dtype=complex)
X: NDArray[np.complex128] = np.array([[0, 1], [1, 0]], dtype=complex)
Y: NDArray[np.complex128] = np.array([[0, -1j], [1j, 0]], dtype=complex)
Z: NDArray[np.complex128] = np.array([[1, 0], [0, -1]], dtype=complex)
H: NDArray[np.complex128] = (1 / np.sqrt(2)) * np.array([[1, 1], [1, -1]], dtype=complex)


class QState:
    """
    Single-qubit quantum state represented as a 2×2 density matrix ρ.

    Provides:
      - Construction from a physical label ('H','V','D','A')
      - Unitary evolution:  ρ → U ρ U†
      - Depolarizing noise: ρ → (1−p)ρ + p(I/2)
      - Projective measurement with Lüders state collapse
      - von Neumann entropy
      - State fidelity with a target label
    """

    def __init__(self, matrix: NDArray[np.complex128] | None = None) -> None:
        if matrix is None:
            # Default: |0⟩⟨0|  (horizontal polarisation)
            self.rho: NDArray[np.complex128] = np.array([[1, 0], [0, 0]], dtype=complex)
        else:
            self.rho = np.array(matrix, dtype=complex)
            self.rho = self.rho / np.trace(self.rho)   # enforce unit trace

    @classmethod
    def from_label(cls, label: str) -> "QState":
        """
        Construct a pure state density matrix from a polarisation label.

        Args:
            label: One of 'H' (horizontal), 'V' (vertical),
                   'D' (diagonal +45°), 'A' (anti-diagonal −45°).

        Returns:
            QState with ρ = |ψ⟩⟨ψ|.
        """
        ket_map: dict[str, NDArray[np.complex128]] = {
            'H': np.array([[1], [0]], dtype=complex),
            'V': np.array([[0], [1]], dtype=complex),
            'D': (1 / np.sqrt(2)) * np.array([[1], [1]], dtype=complex),
            'A': (1 / np.sqrt(2)) * np.array([[1], [-1]], dtype=complex),
        }
        if label not in ket_map:
            raise ValueError(f"Unknown label '{label}'. Valid labels: {list(ket_map.keys())}")
        ket = ket_map[label]
        return cls(np.outer(ket, ket.conj()))

    def apply_unitary(self, U: NDArray[np.complex128]) -> None:
        """Apply a unitary gate U: ρ → U ρ U†."""
        self.rho = U @ self.rho @ U.conj().T

    def apply_depolarizing_noise(self, p: float) -> None:
        """
        Apply the single-qubit depolarizing channel with noise parameter p ∈ [0, 1].
        ρ → (1 − p) ρ + p (I/2)
        At p=0: identity. At p=1: completely mixed state.
        """
        self.rho = (1 - p) * self.rho + p * (I / 2.0)

    def measure(self, basis: str) -> int:
        """
        Perform a projective measurement and collapse the state (Lüders rule).

        Args:
            basis: 'rectilinear' (Z-basis: |H⟩/|V⟩) or 'diagonal' (X-basis: |D⟩/|A⟩).

        Returns:
            Measurement outcome: 0 or 1.
        """
        P0: NDArray[np.complex128]
        P1: NDArray[np.complex128]

        if basis == 'rectilinear':
            P0 = np.array([[1, 0], [0, 0]], dtype=complex)
            P1 = np.array([[0, 0], [0, 1]], dtype=complex)
        elif basis == 'diagonal':
            d  = (1 / np.sqrt(2)) * np.array([[1], [1]], dtype=complex)
            a  = (1 / np.sqrt(2)) * np.array([[1], [-1]], dtype=complex)
            P0 = np.outer(d, d.conj())
            P1 = np.outer(a, a.conj())
        else:
            raise ValueError(f"Unknown basis '{basis}'. Use 'rectilinear' or 'diagonal'.")

        prob_0: float = float(np.real(np.trace(P0 @ self.rho)))
        prob_1: float = float(np.real(np.trace(P1 @ self.rho)))

        total: float = prob_0 + prob_1
        prob_0, prob_1 = prob_0 / total, prob_1 / total

        result: int = int(np.random.choice([0, 1], p=[prob_0, prob_1]))

        # Lüders collapse: ρ' = (P ρ P) / Tr(P ρ)
        projector = P0 if result == 0 else P1
        norm      = float(np.real(np.trace(projector @ self.rho)))
        if norm > 1e-15:
            self.rho = (projector @ self.rho @ projector) / norm
        else:
            self.rho = projector

        return result

    def get_entropy(self) -> float:
        """
        Compute the von Neumann entropy S(ρ) = −Tr(ρ log₂ ρ) in bits.
        Returns 0 for a pure state, 1 for the fully mixed state.
        """
        evals: NDArray[np.float64] = np.linalg.eigvalsh(self.rho)
        evals = evals[evals > 1e-10]          # discard numerical noise near 0
        return float(-np.sum(evals * np.log2(evals)))

    def get_fidelity(self, target_label: str) -> float:
        """
        Compute the fidelity F(ρ, σ) = Tr(σ ρ) with a target pure state σ.

        Args:
            target_label: Label of the target pure state ('H','V','D','A').

        Returns:
            Fidelity in [0, 1].
        """
        target = QState.from_label(target_label)
        return float(np.real(np.trace(target.rho @ self.rho)))


if __name__ == "__main__":
    print("--- PHYSICS KERNEL TEST ---")
    q = QState.from_label('H')
    print(f"Init Entropy:       {q.get_entropy():.4f}")
    q.apply_depolarizing_noise(0.2)
    print(f"Post-Noise Entropy: {q.get_entropy():.4f}")
    res = q.measure('rectilinear')
    print(f"Measurement:        {res}")
    print(f"Final Entropy:      {q.get_entropy():.4f}")