"""
tests/test_explain_logic.py
Pytest unit tests for Simulation/explain_logic.py (deterministic forensic reporter).

Tests verify that the text report is fully deterministic — same inputs must
always produce the same output — and that physical evidence strings are correct
for each prediction class and vital reading combination.

Run with:
    conda activate qkd_env
    pytest tests/test_explain_logic.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Simulation'))

import pytest
import explain_logic  # type: ignore[import]

analyze = explain_logic.analyze_incident


class TestDeterminism:
    """The function must be purely deterministic (no randomness)."""

    def test_same_input_same_output_normal(self) -> None:
        vitals = {"voltage": 3.3, "jitter": 1.2, "qber": 0.04}
        assert analyze("normal", vitals) == analyze("normal", vitals)

    def test_same_input_same_output_blinding(self) -> None:
        vitals = {"voltage": 9.0, "jitter": 0.1, "qber": 0.01}
        assert analyze("attack_blinding", vitals) == analyze("attack_blinding", vitals)

    def test_same_input_same_output_timeshift(self) -> None:
        vitals = {"voltage": 3.3, "jitter": 0.05, "qber": 0.03}
        assert analyze("attack_timeshift", vitals) == analyze("attack_timeshift", vitals)


class TestBlindingReport:
    """Reports for Blinding attack must cite voltage spike and zero jitter."""

    def _saturation_vitals(self) -> dict:
        return {"voltage": 9.04, "jitter": 0.09, "qber": 0.01}

    def test_header_contains_blinding(self) -> None:
        report = analyze("attack_blinding", self._saturation_vitals())
        assert "ATTACK_BLINDING" in report.upper()

    def test_voltage_evidence_present(self) -> None:
        report = analyze("attack_blinding", self._saturation_vitals())
        assert "Evidence A" in report
        assert "9.04" in report

    def test_jitter_evidence_present(self) -> None:
        report = analyze("attack_blinding", self._saturation_vitals())
        assert "Evidence B" in report
        assert "0.09" in report

    def test_conclusion_mentions_blinding(self) -> None:
        report = analyze("attack_blinding", self._saturation_vitals())
        assert "blinding" in report.lower() or "Conclusion" in report

    def test_no_false_anomaly_flag_for_blinding(self) -> None:
        """The cross-feature anomaly flag should NOT fire for a genuine Blinding event."""
        report = analyze("attack_blinding", {"voltage": 9.0, "jitter": 0.1, "qber": 0.01})
        assert "solar interference" not in report.lower()


class TestTimeShiftReport:
    """Reports for Time-Shift attack must cite unnatural jitter precision."""

    def _ts_vitals(self) -> dict:
        return {"voltage": 3.3, "jitter": 0.05, "qber": 0.03}

    def test_header_contains_timeshift(self) -> None:
        report = analyze("attack_timeshift", self._ts_vitals())
        assert "ATTACK_TIMESHIFT" in report.upper()

    def test_jitter_evidence_present(self) -> None:
        report = analyze("attack_timeshift", self._ts_vitals())
        assert "Evidence A" in report
        assert "0.05" in report

    def test_conclusion_mentions_timing(self) -> None:
        report = analyze("attack_timeshift", self._ts_vitals())
        assert "Conclusion" in report


class TestNormalReport:
    """Normal predictions must produce tiered status messages."""

    def test_secure_below_5pct(self) -> None:
        report = analyze("normal", {"voltage": 3.3, "jitter": 1.2, "qber": 0.03})
        assert "SYSTEM SECURE" in report

    def test_caution_between_5_and_8pct(self) -> None:
        report = analyze("normal", {"voltage": 3.3, "jitter": 1.2, "qber": 0.06})
        assert "CAUTION" in report

    def test_warning_above_8pct(self) -> None:
        report = analyze("normal", {"voltage": 3.3, "jitter": 1.2, "qber": 0.09})
        assert "WARNING" in report

    def test_qber_value_appears_in_report(self) -> None:
        """The actual QBER percentage must be printed in the report."""
        report = analyze("normal", {"voltage": 3.3, "jitter": 1.2, "qber": 0.09})
        assert "9.00%" in report


class TestInterceptReport:
    """Intercept-Resend prediction must produce a quantum-threat report."""

    def test_header_contains_intercept(self) -> None:
        report = analyze("attack_intercept", {"voltage": 3.3, "jitter": 1.2, "qber": 0.25})
        assert "INTERCEPT" in report.upper()

    def test_qber_evidence_cited(self) -> None:
        report = analyze("attack_intercept", {"voltage": 3.3, "jitter": 1.2, "qber": 0.25})
        assert "Evidence A" in report
        assert "25.00%" in report


class TestUnknownPrediction:
    """Unknown labels must produce an 'UNKNOWN CLASSIFICATION' fallback."""

    def test_unknown_label_fallback(self) -> None:
        report = analyze("attack_novel", {"voltage": 3.3, "jitter": 1.2, "qber": 0.05})
        assert "UNKNOWN" in report.upper()
        assert "Manual inspection" in report


class TestCrossFeatureAnomaly:
    """High voltage + normal jitter on a non-blinding prediction must trigger the anomaly flag."""

    def test_anomaly_flag_fires_for_high_voltage_normal_jitter(self) -> None:
        report = analyze("normal", {"voltage": 7.0, "jitter": 1.5, "qber": 0.04})
        assert "ANOMALY" in report
        assert "solar interference" in report.lower() or "malfunction" in report.lower()
