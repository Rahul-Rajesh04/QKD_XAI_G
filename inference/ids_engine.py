"""
inference/ids_engine.py
Dual-model inference engine for the QKD Real-Time IDS.

Implements a confidence-gated cascade:
  1. One-Class SVM (OCSVM) — novelty gate. Flags out-of-distribution events
     before the RF even sees them.
  2. Random Forest (RF) — multi-class classifier for known threat types.
  3. Combined verdict logic — escalates to "POTENTIAL ZERO-DAY" when both
     the SVM flags the event AND the RF confidence is below threshold.

Usage:
    engine = IDSEngine()
    result = engine.infer(features_df)
    print(result["verdict"], result["rf_confidence"])
"""
__author__ = "Rahul Rajesh 2360445"

import pickle
import os
import sys
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

# Ensure project root is on sys.path regardless of launch location
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.logging_config import get_logger

log = get_logger("qkd.inference")

# Default model paths relative to project root
_RF_MODEL_PATH:  str = "Models/rf_model_v3.pkl"
_SVM_MODEL_PATH: str = "Models/svm_model_v3.pkl"

# Feature column ordering must match training
FEATURES: list[str] = [
    "qber_overall",
    "qber_rectilinear",
    "qber_diagonal",
    "detector_voltage",
    "timing_jitter",
    "photon_count_rate",
]


@dataclass
class InferenceResult:
    """
    Structured output from a single dual-model inference call.

    Attributes:
        verdict:       Final human-readable classification string.
        rf_prediction: Raw class label from the Random Forest.
        rf_confidence: Max class probability from predict_proba() (0.0–1.0).
        class_probs:   Probability dict {class_label: probability}.
        svm_anomaly:   True if the OCSVM flagged this sample as out-of-distribution.
        flagged:       True if the verdict is not 'normal' or 'uncertain'.
    """
    verdict:       str
    rf_prediction: str
    rf_confidence: float
    class_probs:   dict[str, float]
    svm_anomaly:   bool
    flagged:       bool


class IDSEngine:
    """
    Loads and wraps both trained models to provide a single infer() entry point.

    The confidence_threshold controls the boundary between a confirmed
    classification and an "UNCERTAIN" fallback that escalates to the operator.
    """

    def __init__(
        self,
        rf_path:  str   = _RF_MODEL_PATH,
        svm_path: str   = _SVM_MODEL_PATH,
        confidence_threshold: float = 0.70,
    ) -> None:
        """
        Load both models from disk.

        Args:
            rf_path:   Path to rf_model_v3.pkl
            svm_path:  Path to svm_model_v3.pkl
            confidence_threshold: RF max-probability below which the verdict
                                  is marked as UNCERTAIN (default 70%).
        """
        if not os.path.exists(rf_path):
            raise FileNotFoundError(
                f"Random Forest model not found at '{rf_path}'. "
                "Run model_training.py first."
            )
        if not os.path.exists(svm_path):
            raise FileNotFoundError(
                f"One-Class SVM model not found at '{svm_path}'. "
                "Run model_training.py first."
            )

        with open(rf_path, "rb") as f:
            self._rf = pickle.load(f)
        with open(svm_path, "rb") as f:
            self._svm = pickle.load(f)

        self.confidence_threshold: float = confidence_threshold
        log.info(
            f"IDSEngine loaded | RF classes={self._rf.classes_.tolist()} | "
            f"confidence_threshold={confidence_threshold:.0%}"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def infer(self, features: pd.DataFrame) -> InferenceResult:
        """
        Run the dual-model cascade on a single-row feature DataFrame.

        Step 1 — OCSVM novelty gate:
            svm.predict() returns +1 (in-distribution) or -1 (anomaly).
        Step 2 — RF classification with probability:
            rf.predict_proba() returns a probability vector over all 4 classes.
        Step 3 — Combined verdict:
            If SVM=anomaly AND RF thinks 'normal' with low confidence → ZERO-DAY.
            If RF confidence < threshold → UNCERTAIN.
            Otherwise → RF's top prediction.

        Args:
            features: Single-row pd.DataFrame with columns matching FEATURES.

        Returns:
            InferenceResult dataclass with all decision signals.
        """
        X: pd.DataFrame = features[FEATURES]

        # ---- Step 1: OCSVM Novelty Gate ----------------------------------
        svm_result: int     = int(self._svm.predict(X)[0])
        svm_anomaly: bool   = svm_result == -1

        # ---- Step 2: RF Classification -----------------------------------
        rf_proba: np.ndarray         = self._rf.predict_proba(X)[0]
        rf_pred:  str                = str(self._rf.classes_[rf_proba.argmax()])
        rf_conf:  float              = float(rf_proba.max())
        class_probs: dict[str, float] = {
            str(cls): float(prob)
            for cls, prob in zip(self._rf.classes_, rf_proba)
        }

        # ---- Step 3: Combined Verdict ------------------------------------
        verdict: str
        flagged: bool

        if svm_anomaly and rf_pred == "normal" and rf_conf < self.confidence_threshold:
            verdict = "POTENTIAL ZERO-DAY — ESCALATE TO OPERATOR"
            flagged = True
            log.warning(
                f"ZERO-DAY ANOMALY | SVM=anomaly | RF={rf_pred} | "
                f"confidence={rf_conf:.1%}"
            )

        elif rf_conf < self.confidence_threshold:
            verdict = f"UNCERTAIN ({rf_pred})"
            flagged = True
            log.warning(
                f"LOW CONFIDENCE | RF={rf_pred} | confidence={rf_conf:.1%} | "
                f"SVM={'ANOMALY' if svm_anomaly else 'NORMAL'}"
            )

        elif rf_pred != "normal":
            verdict = rf_pred
            flagged = True
            log.warning(
                f"ATTACK DETECTED | {rf_pred} | confidence={rf_conf:.1%} | "
                f"SVM={'ANOMALY' if svm_anomaly else 'NORMAL'}"
            )

        else:
            verdict = "normal"
            flagged = False
            log.debug(f"Normal | confidence={rf_conf:.1%} | SVM={'ANOMALY' if svm_anomaly else 'OK'}")

        return InferenceResult(
            verdict=verdict,
            rf_prediction=rf_pred,
            rf_confidence=rf_conf,
            class_probs=class_probs,
            svm_anomaly=svm_anomaly,
            flagged=flagged,
        )
