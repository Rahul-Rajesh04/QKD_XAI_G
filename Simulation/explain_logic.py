"""
Simulation/explain_logic.py
Deterministic forensic text reporter.
Translates a model prediction and live APD hardware vitals into a human-readable
incident report grounding the AI's decision in physical causation.
"""
__author__ = "Rahul Rajesh 2360445"


def analyze_incident(prediction: str, vitals: dict[str, float]) -> str:
    """
    Generate a deterministic forensic incident report from a model prediction
    and real-time hardware telemetry readings.

    Args:
        prediction: Model's class label string — one of:
                    'normal', 'attack_blinding', 'attack_timeshift',
                    'attack_intercept'.
        vitals:     Dictionary with keys:
                    'voltage'  — mean APD bias voltage reading (Volts)
                    'jitter'   — mean timing jitter reading (nanoseconds)
                    'qber'     — current QBER (float in [0.0, 1.0])

    Returns:
        Multi-line forensic report string suitable for logging or GUI display.
    """
    v: float = vitals['voltage']
    j: float = vitals['jitter']
    q: float = vitals['qber']

    report: list[str] = []
    report.append(f"FORENSIC ANALYSIS: [{prediction.upper()}]")

    if prediction == "attack_blinding":
        report.append("CRITICAL THREAT: DETECTOR SATURATION")
        report.append("  Reasoning: The AI detected a physical saturation signature.")

        if v > 5.0:
            report.append(
                f"  - Evidence A: Voltage Spike ({v:.2f} V). "
                "Detectors forced into Linear Mode (normal: ~3.3 V)."
            )
        if j < 0.2:
            report.append(
                f"  - Evidence B: Zero Jitter ({j:.2f} ns). "
                "Signal is continuous-wave (CW), not pulsed (normal: ~1.2 ns)."
            )
        report.append("  -> Conclusion: Eve is blinding the detectors to force deterministic switching.")

    elif prediction == "attack_timeshift":
        report.append("SOPHISTICATED THREAT: TIMING ANOMALY")
        report.append("  Reasoning: The AI detected an efficiency mismatch indicating timing offsets.")

        if j < 0.5:
            report.append(
                f"  - Evidence A: Unnatural Precision ({j:.2f} ns). "
                "Real thermal jitter should be >1.0 ns."
            )
        if v < 0.6:
            report.append(
                f"  - Evidence B: Low Count Rate ({v:.2f} V). "
                "Pulses are hitting the detector gate edge."
            )
        report.append(
            "  -> Conclusion: Eve is shifting pulses to exploit the detector's "
            "temporal efficiency curve."
        )

    elif prediction == "attack_intercept":
        report.append("QUANTUM THREAT: INTERCEPT-RESEND DETECTED")
        report.append("  Reasoning: QBER is statistically elevated beyond the noise floor.")
        report.append(
            f"  - Evidence A: QBER = {q:.2%} "
            f"(calibrated noise floor: ~4.0%, intercept-resend signature: ~25.0%)."
        )
        report.append(
            "  -> Conclusion: Eve is measuring and re-preparing photons, "
            "introducing detectable quantum errors."
        )

    elif prediction == "normal":
        if q > 0.08:
            report.append("WARNING: NEAR-CRITICAL NOISE LEVELS")
            report.append(
                f"  - Status: System is Safe, but QBER ({q:.2%}) is "
                "approaching the abort threshold (11%)."
            )
            report.append("  - Action: Check for eavesdropping attempts or fiber damage.")
        elif q > 0.05:
            report.append("CAUTION: SUSPICIOUS ACTIVITY")
            report.append(
                f"  - Status: QBER is elevated ({q:.2%}). "
                "Likely dirty fiber connections or connector contamination."
            )
        else:
            report.append("SYSTEM SECURE")
            report.append(
                f"  - Status: Nominal Operation. QBER ({q:.2%}) is within safety limits."
            )

    else:
        report.append(f"UNKNOWN CLASSIFICATION: '{prediction}'")
        report.append("  - Action: Manual inspection required.")

    # Cross-feature anomaly flag — high voltage but normal jitter suggests
    # hardware malfunction or solar/RF interference, not a blinding attack
    if prediction != "attack_blinding" and v > 5.0 and j > 1.0:
        report.append(
            "ANOMALY: High Voltage but Normal Jitter detected. "
            "Possible solar interference or device malfunction — not a Blinding attack pattern."
        )

    return "\n".join(report)