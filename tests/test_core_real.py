"""
tests/test_core_real.py
Pytest unit tests for Simulation/core_real.py (density-matrix physics kernel).

Tests verify fundamental quantum mechanical invariants that must hold
regardless of any future code changes.

Run with:
    conda activate qkd_env
    pytest tests/test_core_real.py -v
"""
import sys
import os

# Ensure Simulation/ is on the path when running from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Simulation'))

import numpy as np
import pytest

import core_real as phys  # type: ignore[import]

QState = phys.QState


class TestQStatePureProperties:
    """Properties that must hold for freshly prepared pure states."""

    def test_from_label_H_trace_is_one(self) -> None:
        """Density matrix of |H⟩ must have trace = 1."""
        q = QState.from_label('H')
        assert np.trace(q.rho) == pytest.approx(1.0, abs=1e-9)

    def test_from_label_purity_is_one(self) -> None:
        """Pure state must satisfy Tr(ρ²) = 1."""
        for label in ('H', 'V', 'D', 'A'):
            q = QState.from_label(label)
            purity = float(np.real(np.trace(q.rho @ q.rho)))
            assert purity == pytest.approx(1.0, abs=1e-9), f"Failed for label '{label}'"

    def test_pure_state_zero_entropy(self) -> None:
        """A pure state must have von Neumann entropy = 0 bits."""
        q = QState.from_label('H')
        assert q.get_entropy() == pytest.approx(0.0, abs=1e-9)

    def test_fidelity_pure_state_with_itself(self) -> None:
        """Fidelity of a state with itself must be exactly 1.0."""
        for label in ('H', 'V', 'D', 'A'):
            q = QState.from_label(label)
            assert q.get_fidelity(label) == pytest.approx(1.0, abs=1e-9)

    def test_fidelity_H_with_V_is_zero(self) -> None:
        """|H⟩ and |V⟩ are orthogonal — fidelity must be 0."""
        q = QState.from_label('H')
        assert q.get_fidelity('V') == pytest.approx(0.0, abs=1e-9)

    def test_fidelity_H_with_d_is_half(self) -> None:
        """F(|H⟩, |D⟩) = |⟨H|D⟩|² = 0.5 (45-degree overlap)."""
        q = QState.from_label('H')
        assert q.get_fidelity('D') == pytest.approx(0.5, abs=1e-9)

    def test_unknown_label_raises(self) -> None:
        """from_label should raise ValueError for an unrecognised label."""
        with pytest.raises(ValueError, match="Unknown label"):
            QState.from_label('X')


class TestDepolarizingNoise:
    """von Neumann entropy and purity under depolarizing noise."""

    def test_maximally_mixed_state_entropy_is_one(self) -> None:
        """Full depolarising (p=1) → maximally mixed state → entropy = 1 bit."""
        q = QState.from_label('H')
        q.apply_depolarizing_noise(p=1.0)
        assert q.get_entropy() == pytest.approx(1.0, abs=1e-6)

    def test_entropy_monotone_with_noise(self) -> None:
        """Entropy must increase monotonically as depolarizing strength grows."""
        entropies = []
        for p in np.linspace(0.0, 1.0, 21):
            q = QState.from_label('H')
            q.apply_depolarizing_noise(p)
            entropies.append(q.get_entropy())
        for i in range(len(entropies) - 1):
            assert entropies[i] <= entropies[i + 1] + 1e-9

    def test_density_matrix_trace_preserved_after_noise(self) -> None:
        """Trace must remain 1 after noise application."""
        q = QState.from_label('D')
        q.apply_depolarizing_noise(0.3)
        assert np.real(np.trace(q.rho)) == pytest.approx(1.0, abs=1e-9)

    def test_density_matrix_hermitian_after_noise(self) -> None:
        """ρ must be Hermitian (ρ = ρ†) after noise application."""
        q = QState.from_label('V')
        q.apply_depolarizing_noise(0.15)
        np.testing.assert_allclose(q.rho, q.rho.conj().T, atol=1e-9)

    def test_purity_decreases_with_noise(self) -> None:
        """Tr(ρ²) must decrease (or stay equal) as noise increases."""
        purities = []
        for p in np.linspace(0.0, 1.0, 11):
            q = QState.from_label('H')
            q.apply_depolarizing_noise(p)
            purities.append(float(np.real(np.trace(q.rho @ q.rho))))
        for i in range(len(purities) - 1):
            assert purities[i] >= purities[i + 1] - 1e-9


class TestMeasurement:
    """Projective measurement properties."""

    def test_measurement_outcome_binary(self) -> None:
        """Measurement outcome must be 0 or 1."""
        for _ in range(50):
            q = QState.from_label('D')
            result = q.measure('rectilinear')
            assert result in (0, 1)

    def test_post_measurement_entropy_is_zero(self) -> None:
        """After measurement, the state must collapse to a pure state (S=0)."""
        q = QState.from_label('D')
        q.measure('rectilinear')
        assert q.get_entropy() == pytest.approx(0.0, abs=1e-6)

    def test_post_measurement_trace_is_one(self) -> None:
        """Collapsed state must still have trace = 1."""
        q = QState.from_label('H')
        q.measure('diagonal')
        assert np.real(np.trace(q.rho)) == pytest.approx(1.0, abs=1e-9)

    def test_unknown_basis_raises(self) -> None:
        """measure() must raise ValueError for an unsupported basis string."""
        q = QState.from_label('H')
        with pytest.raises(ValueError, match="Unknown basis"):
            q.measure('circular')
