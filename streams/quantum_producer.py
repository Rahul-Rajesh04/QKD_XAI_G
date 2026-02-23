__author__ = "Rahul Rajesh 2360445"

import asyncio
import sys
import os
import numpy as np

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_SIM_PATH = os.path.join(_PROJECT_ROOT, 'Simulation')
if _SIM_PATH not in sys.path:
    sys.path.insert(0, _SIM_PATH)

import components as hardware
import core_real as phys

from config.logging_config import get_logger

log = get_logger("qkd.simulation")

async def quantum_event_stream(
    attack_mode: str = "none",
    intensity_mode: str = "single_photon",
    noise_p: float = 0.04,
    state_controller: dict = None,
) -> "asyncio.AsyncGenerator[dict, None]":
    
    laser = hardware.LaserSource()
    detector = hardware.APD_Detector()
    detector.set_attack_mode(attack_mode)

    alice_basis_choices = [0, 1]
    t: float = 0.0

    log.info(
        f"Quantum event stream started | attack={attack_mode} | "
        f"intensity={intensity_mode} | noise_p={noise_p:.3f}"
    )

    while True:
        current_attack = attack_mode
        current_intensity = intensity_mode
        
        if state_controller and state_controller.get("active", False):
            current_attack = state_controller["attack_mode"]
            current_intensity = state_controller["intensity_mode"]
            state_controller["remaining"] -= 1
            if state_controller["remaining"] <= 0:
                state_controller["active"] = False

        detector.set_attack_mode(current_attack)

        alice_bit: int = int(np.random.randint(0, 2))
        alice_basis: int = int(np.random.choice(alice_basis_choices))

        label_map: dict[tuple[int, int], str] = {
            (0, 0): 'H',
            (1, 0): 'V',
            (0, 1): 'D',
            (1, 1): 'A',
        }
        
        q_state, flux = laser.emit(label_map[(alice_bit, alice_basis)], current_intensity)

        if current_intensity != "blinding":
            q_state.apply_depolarizing_noise(noise_p)

        bob_basis: int = int(np.random.choice(alice_basis_choices))
        basis_str: str = 'rectilinear' if bob_basis == 0 else 'diagonal'

        result: int | None = detector.detect(q_state, flux, basis_str, t)

        t += 1e-6

        if current_attack == "timeshift":
            c_rate = float(np.random.normal(0.15, 0.02))
        elif current_intensity == "blinding":
            c_rate = float(np.random.normal(0.99, 0.005))
        else:
            c_rate = float(np.random.normal(0.25, 0.02))

        if result is not None:
            yield {
                "alice_bit":        alice_bit,
                "alice_basis":      alice_basis,
                "bob_basis":        bob_basis,
                "bob_bit":          result,
                "detector_voltage": detector.current_voltage,
                "timing_jitter":    detector.current_jitter,
                "photon_count_rate": c_rate,
            }

        await asyncio.sleep(0)