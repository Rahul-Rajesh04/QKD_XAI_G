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

def run_lab_experiment(label, intensity_mode, attack_mode="none", apply_noise=False):
    laser = hardware.LaserSource()
    bob_spd = hardware.APD_Detector()
    bob_spd.set_attack_mode(attack_mode) 
    
    n_pulses = 5000 
    
    results = []
    voltages = []
    jitters = []
    
    for i in range(n_pulses):
        q_state, flux = laser.emit('H', intensity_mode)
        
        if apply_noise:
             q_state.apply_depolarizing_noise(0.04)

        current_time_sim = i * 1e-6 
        res = bob_spd.detect(q_state, flux, 'rectilinear', current_time_sim)
        
        voltages.append(bob_spd.current_voltage)
        jitters.append(bob_spd.current_jitter)
        if res is not None:
            results.append(res)

    avg_voltage = np.mean(voltages)
    avg_jitter = np.mean(jitters)
    
    error_count = sum(r for r in results if r == 1)
    total_received = len(results)
    
    qber = error_count / total_received if total_received > 0 else 0.0
    count_rate = total_received / n_pulses

    ai_input = pd.DataFrame([{
        'qber_overall': qber,
        'qber_rectilinear': qber, 
        'qber_diagonal': qber,    
        'detector_voltage': avg_voltage,
        'timing_jitter': avg_jitter,
        'photon_count_rate': count_rate
    }])
    
    return ai_input, qber, avg_voltage, avg_jitter, total_received

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