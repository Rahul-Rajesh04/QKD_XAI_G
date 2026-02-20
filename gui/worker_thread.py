"""
gui/worker_thread.py
QThread-based simulation + inference worker for the QKD IDS dashboard.

Runs the full pipeline (quantum simulation → circular buffer → IDSEngine)
inside a dedicated thread so the GUI main thread is never blocked.
Communicates results back to the dashboard via PyQt6 signals (type-safe,
cross-thread).

Architecture:
    IDSWorker (QThread)
        └── asyncio event loop (run inside QThread.run())
                ├── quantum_event_stream()  [producer coroutine]
                ├── EventBuffer             [in-memory window]
                └── IDSEngine.infer()       [dual RF+SVM inference]
                -> emits result_ready signal → GUI slot (safe update)
"""
__author__ = "Rahul Rajesh 2360445"

import asyncio
import sys
import os

# Ensure project root is on sys.path regardless of launch location
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.logging_config import get_logger

log = get_logger("qkd.gui")

# Guard: only import PyQt6 if available.
# The worker can also be tested headlessly without PyQt6 installed.
try:
    from PyQt6.QtCore import QThread, pyqtSignal, QObject
    _PYQT_AVAILABLE = True
except ImportError:
    _PYQT_AVAILABLE = False
    log.warning(
        "PyQt6 not found. gui/worker_thread.py will run in headless-test mode only. "
        "Install PyQt6 (pip install PyQt6) to enable the live dashboard."
    )

# Adjust path so sibling packages resolve correctly regardless of cwd
_SIM_PATH = os.path.join(_PROJECT_ROOT, 'Simulation')
if _SIM_PATH not in sys.path:
    sys.path.insert(0, _SIM_PATH)

from streams.quantum_producer import quantum_event_stream
from streams.circular_buffer import EventBuffer
from inference.ids_engine import IDSEngine, InferenceResult
from explain_logic import analyze_incident  # type: ignore[import]


# ---------------------------------------------------------------------------
# Worker — runs in a separate QThread
# ---------------------------------------------------------------------------

if _PYQT_AVAILABLE:
    class IDSWorker(QThread):
        """
        Background worker thread for the QKD IDS.

        Signals:
            result_ready (dict): Emitted after every inference cycle with:
                "verdict"       (str)   — final classification label
                "rf_prediction" (str)   — raw RF class label
                "rf_confidence" (float) — RF max-class probability
                "svm_anomaly"   (bool)  — True if OCSVM flagged this sample
                "flagged"       (bool)  — True if verdict is not 'normal'
                "vitals"        (dict)  — voltage, jitter, qber readings
                "report"        (str)   — human-readable forensic narrative
        """
        result_ready = pyqtSignal(dict)   # cross-thread signal (GUI-safe)

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

        # ----------------------------------------------------------------

        def run(self) -> None:
            """Entry point for the QThread. Runs an asyncio event loop internally."""
            log.info(
                f"IDSWorker started | attack={self.attack_mode} | "
                f"intensity={self.intensity_mode}"
            )
            asyncio.run(self._async_pipeline())

        def stop(self) -> None:
            """Signal the worker to stop after the current inference cycle."""
            self._running = False
            self.quit()

        # ----------------------------------------------------------------

        async def _async_pipeline(self) -> None:
            """Coroutine: event generator → buffer → inference → signal emit."""
            engine = IDSEngine()
            buffer = EventBuffer(maxlen=self.window_size)

            async for event in quantum_event_stream(
                attack_mode    = self.attack_mode,
                intensity_mode = self.intensity_mode,
                noise_p        = self.noise_p,
            ):
                if not self._running:
                    break

                buffer.push(event)

                if buffer.is_ready:
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

                    # Emit to GUI thread via Qt signal (thread-safe)
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
    # Headless stub — allows the rest of the codebase to import this module
    # and run tests without PyQt6 installed.
    class IDSWorker:  # type: ignore[no-redef]
        """Stub used when PyQt6 is not installed."""

        def __init__(self, **kwargs) -> None:
            log.warning("IDSWorker stub active — PyQt6 not installed.")

        def start(self) -> None:
            log.warning("IDSWorker.start() called but PyQt6 is unavailable.")

        def stop(self) -> None:
            pass
