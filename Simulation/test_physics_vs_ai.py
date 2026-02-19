import numpy as np
import pandas as pd
import pickle
import os
import sys
import random # <--- NEW: For randomization

# --- SETUP PATHS ---
sys.path.append(os.path.dirname(__file__))
import core_real as phys
import components as hardware

# --- CONFIGURATION ---
MODEL_PATH = "Models/rf_model_v3.pkl"

def load_ai_brain():
    if not os.path.exists(MODEL_PATH):
        print(f"CRITICAL ERROR: AI Brain not found at {MODEL_PATH}")
        sys.exit(1)
    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)
    print(f"-> AI Brain Loaded successfully.")
    return model

def run_lab_experiment(label, intensity_mode, attack_mode="none", apply_noise=False):
    print(f"\n--- EXPERIMENT: {label} ---")
    
    # 1. Initialize Lab Equipment
    laser = hardware.LaserSource()
    bob_spd = hardware.APD_Detector()
    bob_spd.set_attack_mode(attack_mode) 
    
    # 2. Run Transmission (1000 pulses)
    n_pulses = 1000
    results = []
    voltages = []
    jitters = []
    
    for _ in range(n_pulses):
        # A. Alice Emits
        q_state, flux = laser.emit('H', intensity_mode)
        
        # B. Fiber Noise
        if apply_noise:
            q_state.apply_depolarizing_noise(0.04) 
        
        # C. Bob Detects
        res = bob_spd.detect(q_state, flux, 'rectilinear')
        
        # Collect Hardware Vitals
        voltages.append(bob_spd.current_voltage)
        jitters.append(bob_spd.current_jitter)
        if res is not None:
            results.append(res)

    # 3. Aggregate Data
    avg_voltage = np.mean(voltages)
    avg_jitter = np.mean(jitters)
    
    # QBER Calculation
    error_count = sum(r for r in results if r == 1)
    total_received = len(results)
    qber = error_count / total_received if total_received > 0 else 0.0
    count_rate = total_received / n_pulses

    # PRINT LAB RESULTS
    print(f"-> LAB RESULTS: Voltage={avg_voltage:.2f}V | Jitter={avg_jitter:.2f}ns | QBER={qber:.2f}")

    # 4. AI Input Vector
    ai_input = pd.DataFrame([{
        'qber_overall': qber,
        'qber_rectilinear': qber, 
        'qber_diagonal': qber,    
        'detector_voltage': avg_voltage,
        'timing_jitter': avg_jitter,
        'photon_count_rate': count_rate
    }])
    
    return ai_input, qber

def main():
    print("=== QUANTUM LAB: PHYSICS vs AI SHOWDOWN (RANDOMIZED) ===")
    ai_model = load_ai_brain()
    summary_report = []

    # --- DEFINE TEST CASES ---
    test_cases = [
        {
            "name": "Safe Transmission",
            "intensity": "single_photon",
            "attack": "none",
            "noise": True,
            "expected": "normal"
        },
        {
            "name": "Time-Shift Attack",
            "intensity": "single_photon",
            "attack": "timeshift",
            "noise": False,
            "expected": "attack_timeshift"
        },
        {
            "name": "Blinding Attack",
            "intensity": "blinding",
            "attack": "none",
            "noise": False,
            "expected": "attack_blinding"
        }
    ]

    # --- THE RANDOMIZER ---
    print(f"-> Shuffling {len(test_cases)} scenarios to prove AI robustness...\n")
    random.shuffle(test_cases)

    # --- EXECUTION LOOP ---
    for case in test_cases:
        input_data, qber = run_lab_experiment(case["name"], case["intensity"], attack_mode=case["attack"], apply_noise=case["noise"])
        
        # AI PREDICTION
        pred = ai_model.predict(input_data)[0]
        print(f"-> AI DIAGNOSIS: [{pred.upper()}]")
        
        # VERIFICATION
        is_correct = (pred == case["expected"])
        status_icon = "✅ PASS" if is_correct else "❌ FAIL"
        
        summary_report.append({
            "Scenario": case["name"], 
            "Prediction": pred, 
            "QBER": qber, 
            "Status": status_icon
        })

    # --- FINAL EXECUTIVE SUMMARY ---
    print("\n" + "="*65)
    print(f"{'SCENARIO (Random Order)':<20} | {'AI DIAGNOSIS':<20} | {'QBER':<6} | {'STATUS':<6}")
    print("-" * 65)
    
    for row in summary_report:
        note = ""
        if row['QBER'] > 0.05 and row['QBER'] < 0.11:
            note = "[SUSPICIOUS]"
        elif row['QBER'] > 0.11:
            note = "[CRITICAL]"
            
        print(f"{row['Scenario']:<20} | {row['Prediction'].upper():<20} | {row['QBER']:.2f}   | {row['Status']} {note}")
    
    print("="*65)

if __name__ == "__main__":
    main()