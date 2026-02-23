__author__ = "Rahul Rajesh 2360445"

import asyncio
import sys
import os
import csv
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.logging_config import get_logger

log = get_logger("qkd.gui")

try:
    from PyQt6.QtCore import QThread, pyqtSignal, QObject
    _PYQT_AVAILABLE = True
except ImportError:
    _PYQT_AVAILABLE = False
    log.warning("PyQt6 not found. Running in headless-test mode.")

_SIM_PATH = os.path.join(_PROJECT_ROOT, 'Simulation')
if _SIM_PATH not in sys.path:
    sys.path.insert(0, _SIM_PATH)

from streams.quantum_producer import quantum_event_stream
from streams.circular_buffer import EventBuffer
from inference.ids_engine import IDSEngine, InferenceResult
from explain_logic import analyze_incident

if _PYQT_AVAILABLE:
    class IDSWorker(QThread):
        
        result_ready = pyqtSignal(dict)  

        def __init__(
            self,
            attack_mode:    str   = "none",
            intensity_mode: str   = "single_photon",
            noise_p:        float = 0.04,
            window_size:    int   = 500,
            parent: "QObject | None" = None,
        ) -> None:
            super().__init__(parent)
            self.attack_mode    = attack_mode
            self.intensity_mode = intensity_mode
            self.noise_p        = noise_p
            self.window_size    = window_size
            self._running       = True
            
            self.state_controller = {
                "active": False, 
                "attack_mode": "none", 
                "intensity_mode": "single_photon", 
                "remaining": 0
            }
            
            self._log_dir = os.path.join(_PROJECT_ROOT, "logs")
            os.makedirs(self._log_dir, exist_ok=True)
            self._telemetry_file = os.path.join(self._log_dir, "threat_telemetry.csv")
            
            self._init_telemetry_log()

        def _init_telemetry_log(self) -> None:
            if not os.path.exists(self._telemetry_file):
                with open(self._telemetry_file, mode='w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        "Timestamp", "System_Verdict", "Detected_Signature", 
                        "Confidence", "SVM_Triggered", "Voltage", "Jitter", "QBER"
                    ])

        def _log_threat(self, result: InferenceResult, vitals: dict) -> None:
            clean_verdict = result.verdict.replace("—", "-")
            
            if "ZERO-DAY" in clean_verdict:
                signature = "Unclassified_Anomaly"
                confidence = "100.00% (SVM Override)"
            else:
                signature = result.rf_prediction
                confidence = f"{result.rf_confidence * 100:.2f}%"

            v_str = f"{vitals['voltage']:.2f} V"
            j_str = f"{vitals['jitter']:.3f} ns"
            q_str = f"{vitals['qber'] * 100:.2f}%"

            with open(self._telemetry_file, mode='a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    clean_verdict,
                    signature,
                    confidence,
                    str(result.svm_anomaly),
                    v_str,
                    j_str,
                    q_str
                ])

        def inject_attack(self, attack: str, duration_events: int = 1500) -> None:
            intensity = "blinding" if attack == "blinding" else "single_photon"
            self.state_controller["attack_mode"] = attack
            self.state_controller["intensity_mode"] = intensity
            self.state_controller["remaining"] = duration_events
            self.state_controller["active"] = True

        def run(self) -> None:
            log.info(f"IDSWorker started | attack={self.attack_mode} | intensity={self.intensity_mode}")
            asyncio.run(self._async_pipeline())

        def stop(self) -> None:
            self._running = False
            self.quit()

        async def _async_pipeline(self) -> None:
            engine = IDSEngine()
            buffer = EventBuffer(maxlen=self.window_size)
            
            event_counter = 0

            async for event in quantum_event_stream(
                attack_mode    = self.attack_mode,
                intensity_mode = self.intensity_mode,
                noise_p        = self.noise_p,
                state_controller = self.state_controller,
            ):
                if not self._running:
                    break

                buffer.push(event)
                event_counter += 1

                if buffer.is_ready and event_counter % 50 == 0:
                    features = buffer.extract_features()
                    if features is None:
                        continue

                    result: InferenceResult = engine.infer(features)

                    vitals = {
                        "voltage": features["detector_voltage"].values[0],
                        "jitter":  features["timing_jitter"].values[0],
                        "qber":    features["qber_overall"].values[0],
                    }
                    narrative: str = analyze_incident(result.rf_prediction, vitals)

                    if result.flagged:
                        self._log_threat(result, vitals)

                    self.result_ready.emit({
                        "verdict":       result.verdict,
                        "rf_prediction": result.rf_prediction,
                        "rf_confidence": result.rf_confidence,
                        "svm_anomaly":   result.svm_anomaly,
                        "flagged":       result.flagged,
                        "vitals":        vitals,
                        "report":        narrative,
                        "class_probs":   result.class_probs,
                    })

else:
    class IDSWorker: 
        def __init__(self, **kwargs) -> None:
            pass
        def start(self) -> None:
            pass
        def stop(self) -> None:
            pass
        def inject_attack(self, attack: str, duration_events: int = 1500) -> None:
            pass