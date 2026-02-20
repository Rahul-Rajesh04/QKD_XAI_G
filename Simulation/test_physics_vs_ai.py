__author__ = "Rahul Rajesh 2360445"

import numpy as np
import pandas as pd
import pickle
import os
import sys
import random
import warnings

os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings("ignore")

sys.path.append(os.path.dirname(__file__))
import core_real as phys
import components as hardware
import explain_logic

MODEL_PATH = "Models/rf_model_v3.pkl"

def load_ai_brain():
    if not os.path.exists(MODEL_PATH):
        print(f"CRITICAL ERROR: AI Brain not found at {MODEL_PATH}")
        sys.exit(1)
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    print("-> AI Brain Loaded successfully.")
    return model

def run_lab_experiment(label: str, intensity_mode: str, attack_mode: str = "none", apply_noise: bool = False):
    """
    Simulate a BB84 key exchange and return the AI feature vector.

    Uses genuinely random Alice/Bob bases so qber_rectilinear and qber_diagonal
    are computed from independent measurement sets, mirroring data_preprocessing.py.
    """
    laser   = hardware.LaserSource()
    bob_spd = hardware.APD_Detector()
    bob_spd.set_attack_mode(attack_mode)

    n_pulses = 5000

    alice_bits_l, alice_bases_l = [], []
    bob_bits_l,   bob_bases_l   = [], []
    voltages, jitters = [], []
    received_count = 0

    label_map = {(0, 0): 'H', (1, 0): 'V', (0, 1): 'D', (1, 1): 'A'}

    for i in range(n_pulses):
        a_bit   = int(np.random.randint(0, 2))
        a_basis = int(np.random.randint(0, 2))

        q_state, flux = laser.emit(label_map[(a_bit, a_basis)], intensity_mode)
        if apply_noise:
            q_state.apply_depolarizing_noise(0.04)

        b_basis   = int(np.random.randint(0, 2))
        basis_str = 'rectilinear' if b_basis == 0 else 'diagonal'

        # 15 µs > 10 µs APD dead time — ensures count rate matches training distributions
        current_time_sim = i * 15e-6

        res = bob_spd.detect(q_state, flux, basis_str, current_time_sim)

        voltages.append(bob_spd.current_voltage)
        jitters.append(bob_spd.current_jitter)

        if res is not None:
            alice_bits_l.append(a_bit)
            alice_bases_l.append(a_basis)
            bob_bits_l.append(res)
            bob_bases_l.append(b_basis)
            received_count += 1

    count_rate  = received_count / n_pulses
    avg_voltage = float(np.mean(voltages))
    avg_jitter  = float(np.mean(jitters))

    # Sift and compute per-basis QBER (mirrors data_preprocessing.py)
    ab = np.array(alice_bits_l);  aB = np.array(alice_bases_l)
    bb = np.array(bob_bits_l);    bB = np.array(bob_bases_l)

    match   = aB == bB
    error   = (ab != bb) & match
    is_rect = aB == 0
    is_diag = aB == 1

    n_sifted  = int(match.sum())
    qber_o = error.sum()   / n_sifted              if n_sifted > 0 else 0.0
    qber_r = (error & is_rect).sum() / (match & is_rect).sum() if (match & is_rect).sum() > 0 else 0.0
    qber_d = (error & is_diag).sum() / (match & is_diag).sum() if (match & is_diag).sum() > 0 else 0.0

    ai_input = pd.DataFrame([{
        'qber_overall':      float(qber_o),
        'qber_rectilinear':  float(qber_r),
        'qber_diagonal':     float(qber_d),
        'detector_voltage':  avg_voltage,
        'timing_jitter':     avg_jitter,
        'photon_count_rate': count_rate,
    }])

    return ai_input, float(qber_o), avg_voltage, avg_jitter, n_sifted



def main():
    print("\n" + "="*70)
    print("      QUANTUM LAB: PHYSICS vs AI SHOWDOWN (HIGH STATS MODE)")
    print("="*70)
    ai_model = load_ai_brain()
    summary_report = []

    test_cases = [
        {"name": "Safe Transmission", "intensity": "single_photon", "attack": "none", "noise": True, "expected": "normal"},
        {"name": "Time-Shift Attack", "intensity": "single_photon", "attack": "timeshift", "noise": True, "expected": "attack_timeshift"},
        {"name": "Blinding Attack", "intensity": "blinding", "attack": "none", "noise": True, "expected": "attack_blinding"}
    ]
    random.shuffle(test_cases)

    for case in test_cases:
        print(f"\n RUNNING SCENARIO: {case['name']}")
        print("-" * 30)
        
        input_data, qber, v, j, count = run_lab_experiment(case["name"], case["intensity"], attack_mode=case["attack"], apply_noise=case["noise"])
        
        print(f"   LAB VITALS: Voltage={v:.2f}V | Jitter={j:.2f}ns | QBER={qber:.2%} (Bits: {count})")

        pred = ai_model.predict(input_data)[0]
        
        vitals = {'voltage': v, 'jitter': j, 'qber': qber}
        report = explain_logic.analyze_incident(pred, vitals)
        print("\n" + report)
        
        is_correct = (pred == case["expected"])
        status_icon = "PASS" if is_correct else "FAIL"
        summary_report.append({
            "Scenario": case["name"], 
            "Prediction": pred.upper(), 
            "QBER": f"{qber:.2%}", 
            "Status": status_icon
        })

    print("\n\n" + "="*70)
    print(f"{'SCENARIO':<25} | {'AI DIAGNOSIS':<20} | {'QBER':<8} | {'STATUS'}")
    print("-" * 70)
    for row in summary_report:
        print(f"{row['Scenario']:<25} | {row['Prediction']:<20} | {row['QBER']:<8} | {row['Status']}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()