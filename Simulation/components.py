"""
Simulation/components.py
Hardware component models for the QKD IDS Digital Twin.
Simulates:
  - LaserSource: photon emitter (single-photon / blinding intensity modes)
  - APD_Detector: Avalanche Photodiode with dark counts, dead time,
    saturation (Blinding attack), and timing efficiency mismatch (Time-Shift attack)
"""
__author__ = "Rahul Rajesh 2360445"

import numpy as np
import core_real as phys

# ---------------------------------------------------------------------------
# Physical constants for the APD model
# ---------------------------------------------------------------------------
CONSTANTS: dict[str, float] = {
    'dark_count_prob': 1e-5,    # Probability of a dark count per gate
    'dead_time':       10e-6,   # Detector dead time in seconds (10 µs)
    'jitter_normal_ns': 0.200,  # Normal thermal jitter std-dev (ns)
    'jitter_attack_ns': 0.050,  # Time-Shift attack jitter std-dev (ns)
}


class LaserSource:
    """
    Simulates Alice's photon emitter at 1550 nm.

    Supports two intensity modes:
    - 'single_photon': weak coherent pulse (photon_flux ≈ 0.1)
    - 'blinding':      CW bright laser (photon_flux ≈ 10⁹), saturates APDs
    """

    def __init__(self, wavelength: int = 1550) -> None:
        self.wavelength: int = wavelength

    def emit(
        self,
        label: str,
        intensity_mode: str = 'single_photon',
    ) -> tuple[phys.QState, float]:
        """
        Prepare a quantum state and return it alongside the photon flux.

        Args:
            label:          Polarisation label ('H', 'V', 'D', 'A').
            intensity_mode: 'single_photon' or 'blinding'.

        Returns:
            Tuple of (QState, photon_flux).
        """
        q_state = phys.QState.from_label(label)

        photon_flux: float
        if intensity_mode == 'single_photon':
            photon_flux = 0.1
        elif intensity_mode == 'blinding':
            photon_flux = 1e9    # exceeds APD saturation limit → linear mode
        else:
            photon_flux = 0.1

        return q_state, photon_flux


class APD_Detector:
    """
    Geiger-mode Avalanche Photodiode (APD) detector model.

    Simulates:
      - Dark counts (probability 10⁻⁵ per gate)
      - Dead time (10 µs)
      - Detector saturation in Blinding attack (flux > 10⁷ → ~9.0 V, ~0.1 ns jitter)
      - Temporal efficiency mismatch in Time-Shift attack (~0.05 ns jitter, 15% count rate)
      - Zero-Day anomaly injection (~6.5 V, ~2.8 ns jitter, 25% count rate)
      - Normal Geiger-mode operation (~3.3 V, ~1.2 ns jitter, 25% efficiency)
    """

    def __init__(self, efficiency: float = 0.25) -> None:
        self.base_efficiency: float  = efficiency
        self.saturation_limit: float = 1e7         # photons/s → triggers linear mode
        self.attack_mode: str        = "none"

        self.last_click_time: float  = -1.0
        self.current_voltage: float  = 0.0
        self.current_jitter: float   = 0.0

    def set_attack_mode(self, mode: str) -> None:
        """Set the operating mode: 'none', 'timeshift', 'zeroday', or implicitly 'blinding' (via flux)."""
        self.attack_mode = mode

    def detect(
        self,
        q_state: phys.QState,
        incident_flux: float,
        basis: str,
        current_time: float = 0.0,
    ) -> int | None:
        """
        Attempt to detect a photon and record analog telemetry.

        Args:
            q_state:        Incoming quantum state.
            incident_flux:  Photon flux (photons/s). Values above saturation_limit
                            trigger APD linear mode (Blinding attack signature).
            basis:          Measurement basis: 'rectilinear' or 'diagonal'.
            current_time:   Simulation time in seconds (used for dead-time gating).

        Returns:
            Measurement outcome (0 or 1), or None if the detector did not fire
            (dead time, efficiency miss, or time-shift gate-edge rejection).
        """
        # -- Dead time gate -----------------------------------------------
        if current_time - self.last_click_time < CONSTANTS['dead_time']:
            return None

        # -- Dark count -------------------------------------------------------
        if np.random.random() < CONSTANTS['dark_count_prob']:
            self.current_voltage = float(np.random.normal(3.3, 0.2))
            self.current_jitter  = float(np.random.normal(1.2, 0.5))
            self.last_click_time = current_time
            return int(np.random.choice([0, 1]))

        measurement: int = q_state.measure(basis)

        # Rare detector bit-flip (~0.5% misread rate)
        if np.random.random() < 0.005:
            measurement = 1 - measurement

        # -- Detector Blinding (saturation) -----------------------------------
        if incident_flux > self.saturation_limit:
            self.current_voltage = float(np.random.normal(9.0, 0.05))
            self.current_jitter  = float(np.random.normal(0.1, 0.01))
            self.last_click_time = current_time
            return measurement

        # -- Time-Shift attack (efficiency mismatch) --------------------------
        elif self.attack_mode == "timeshift":
            self.current_voltage = float(np.random.normal(3.3, 0.2))
            self.current_jitter  = float(np.random.normal(CONSTANTS['jitter_attack_ns'], 0.01))
            if np.random.random() < 0.15:     # only 15% of pulses hit the gate
                self.last_click_time = current_time
                return measurement
            return None

        # -- Zero-Day anomaly injection ---------------------------------------
        elif self.attack_mode == "zeroday":
            self.current_voltage = float(np.random.normal(6.5, 0.1))
            self.current_jitter  = float(np.random.normal(2.8, 0.1))
            if np.random.random() < 0.25:
                self.last_click_time = current_time
                return measurement
            return None

        # -- Normal Geiger-mode operation -------------------------------------
        else:
            self.current_voltage = float(np.random.normal(3.3, 0.2))
            self.current_jitter  = float(np.random.normal(1.2, 0.2))
            if np.random.random() < self.base_efficiency:
                self.last_click_time = current_time
                return measurement
            return None


if __name__ == "__main__":
    print("--- HARDWARE COMPONENT TEST ---")
    bob = APD_Detector()
    print(f"Detector Ready. Dead Time = {CONSTANTS['dead_time'] * 1e6:.0f} µs")