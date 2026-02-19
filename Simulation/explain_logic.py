# Simulation/explain_logic.py

def analyze_incident(prediction, vitals):
    """
    Analyzes the AI prediction + Hardware Vitals to generate a detailed forensic report.
    Args:
        prediction (str): AI output (normal, attack_blinding, attack_timeshift)
        vitals (dict): {'voltage': float, 'jitter': float, 'qber': float}
    """
    v = vitals['voltage']
    j = vitals['jitter']
    q = vitals['qber']
    
    report = []
    report.append(f"🔎 FORENSIC ANALYSIS: [{prediction.upper()}]")
    
    # --- 1. BLINDING ATTACK (High Energy) ---
    if prediction == "attack_blinding":
        report.append("🔴 CRITICAL THREAT: DETECTOR SATURATION")
        report.append("   Reasoning: The AI detected a physical saturation signature.")
        
        if v > 5.0:
            report.append(f"   - Evidence A: Voltage Spike ({v:.2f}V). Detectors forced into Linear Mode.")
        if j < 0.2:
            report.append(f"   - Evidence B: Zero Jitter ({j:.2f}ns). Signal is continuous (CW), not pulsed.")
            
        report.append("   -> Conclusion: Eve is blinding the detectors to force deterministic switching.")

    # --- 2. TIME-SHIFT ATTACK (Timing Manipulation) ---
    elif prediction == "attack_timeshift":
        report.append("🟠 SOPHISTICATED THREAT: TIMING ANOMALY")
        report.append("   Reasoning: The AI detected an efficiency mismatch indicating timing offsets.")
        
        if j < 0.5:
            report.append(f"   - Evidence A: Unnatural Precision ({j:.2f}ns). Real thermal jitter should be >1.0ns.")
        if v < 0.6:
            report.append(f"   - Evidence B: Low Count Rate ({v:.2f}V). Pulses are hitting the gate edge.")
            
        report.append("   -> Conclusion: Eve is shifting pulses to exploit the detector's temporal efficiency curve.")

    # --- 3. NORMAL OPERATION (Safe but potentially noisy) ---
    elif prediction == "normal":
        if q > 0.08: # >8% QBER
            report.append("🟡 WARNING: NEAR-CRITICAL NOISE LEVELS")
            report.append(f"   - Status: System is Safe, but QBER ({q:.2%}) is approaching the hacking threshold (11%).")
            report.append("   - Action: Check for eavesdropping attempts or fiber damage.")
        elif q > 0.05: # >5% QBER
            report.append("🟡 CAUTION: SUSPICIOUS ACTIVITY")
            report.append(f"   - Status: QBER is elevated ({q:.2%}). Likely dirty fiber connections.")
        else:
            report.append("🟢 SYSTEM SECURE")
            report.append(f"   - Status: Nominal Operation. QBER ({q:.2%}) is within safety limits.")

    # --- 4. HYBRID CHECKS (The "Super AI" Logic) ---
    # Independent flags for contradictory data
    if v > 5.0 and j > 1.0:
         report.append("⚠️ ANOMALY: High Voltage but Normal Jitter. Possible solar interference or device malfunction.")
    
    return "\n".join(report)