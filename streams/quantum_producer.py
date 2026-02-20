"""
streams/quantum_producer.py
Async generator that emits a continuous stream of raw QKD event dicts
directly from the physics engine, without touching the filesystem.

Usage:
    async for event in quantum_event_stream(attack_mode="none"):
        buffer.push(event)
"""
__author__ = "Rahul Rajesh 2360445"

import asyncio
import sys
import os
import numpy as np

# Ensure project root is on sys.path regardless of launch location
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Allow imports from the Simulation package
_SIM_PATH = os.path.join(_PROJECT_ROOT, 'Simulation')
if _SIM_PATH not in sys.path:
    sys.path.insert(0, _SIM_PATH)

import components as hardware   # type: ignore[import]
import core_real as phys        # type: ignore[import]

from config.logging_config import get_logger

log = get_logger("qkd.simulation")


async def quantum_event_stream(
    attack_mode:    str   = "none",
    intensity_mode: str   = "single_photon",
    noise_p:        float = 0.04,
) -> "asyncio.AsyncGenerator[dict, None]":
    """
    Infinite async generator that emits one raw event dict per simulated photon pulse.

    Yields a dict with the following keys:
        alice_bit         (int)   — Alice's random bit
        alice_basis       (int)   — Alice's basis (0=rectilinear, 1=diagonal)
        bob_basis         (int)   — Bob's randomly chosen measurement basis
        bob_bit           (int)   — Bob's measurement outcome (0 or 1)
        detector_voltage  (float) — Current APD bias voltage (V)
        timing_jitter     (float) — Current APD timing jitter (ns)

    The generator runs indefinitely. Cancel the enclosing task to stop it.

    Args:
        attack_mode:    'none', 'timeshift'. Blinding is triggered via intensity.
        intensity_mode: 'single_photon' or 'blinding'.
        noise_p:        Depolarizing noise probability on the channel (default 4%).
    """
    laser    = hardware.LaserSource()
    detector = hardware.APD_Detector()
    detector.set_attack_mode(attack_mode)

    # Alice and Bob bases are chosen independently per pulse
    alice_basis_choices = [0, 1]   # 0 = rectilinear, 1 = diagonal

    t: float = 0.0  # simulation time in seconds

    log.info(
        f"Quantum event stream started | attack={attack_mode} | "
        f"intensity={intensity_mode} | noise_p={noise_p:.3f}"
    )

    while True:
        # ---- Alice's side ------------------------------------------------
        alice_bit:   int = int(np.random.randint(0, 2))
        alice_basis: int = int(np.random.choice(alice_basis_choices))

        # Map bit + basis to a polarisation label
        label_map: dict[tuple[int, int], str] = {
            (0, 0): 'H',  # bit=0, rectilinear
            (1, 0): 'V',  # bit=1, rectilinear
            (0, 1): 'D',  # bit=0, diagonal
            (1, 1): 'A',  # bit=1, diagonal
        }
        q_state, flux = laser.emit(label_map[(alice_bit, alice_basis)], intensity_mode)

        # Apply channel noise (depolarizing)
        q_state.apply_depolarizing_noise(noise_p)

        # ---- Bob's side --------------------------------------------------
        bob_basis: int = int(np.random.choice(alice_basis_choices))
        basis_str: str = 'rectilinear' if bob_basis == 0 else 'diagonal'

        result: int | None = detector.detect(q_state, flux, basis_str, t)

        t += 1e-6  # advance simulation clock

        if result is not None:
            yield {
                "alice_bit":        alice_bit,
                "alice_basis":      alice_basis,
                "bob_basis":        bob_basis,
                "bob_bit":          result,
                "detector_voltage": detector.current_voltage,
                "timing_jitter":    detector.current_jitter,
            }

        # Yield control to the event loop so GUI / inference tasks can run
        await asyncio.sleep(0)
