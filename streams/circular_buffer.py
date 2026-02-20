"""
streams/circular_buffer.py
Fixed-size circular (ring) buffer for accumulating raw QKD events
and extracting micro-sifted 6-dimensional feature vectors.

The buffer holds at most `maxlen` events (default 500). When full, the
oldest event is automatically evicted on push. Feature extraction runs
in O(W) where W = maxlen ≈ 500, well within real-time constraints.

Usage:
    buf = EventBuffer(maxlen=500)
    buf.push(event_dict)
    if buf.is_ready:
        features_df = buf.extract_features()
"""
__author__ = "Rahul Rajesh 2360445"

from collections import deque
import numpy as np
import pandas as pd

WINDOW_SIZE: int = 500

FEATURE_COLUMNS: list[str] = [
    "qber_overall",
    "qber_rectilinear",
    "qber_diagonal",
    "detector_voltage",
    "timing_jitter",
    "photon_count_rate",
]


class EventBuffer:
    """
    Circular buffer of raw QKD event dicts.

    Each event dict must contain:
        alice_bit (int), alice_basis (int), bob_basis (int), bob_bit (int),
        detector_voltage (float), timing_jitter (float).

    When the buffer reaches `maxlen` events, `is_ready` returns True and
    `extract_features()` computes the six-dimensional fingerprint vector.
    """

    def __init__(self, maxlen: int = WINDOW_SIZE) -> None:
        self._buf: deque[dict] = deque(maxlen=maxlen)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(self, event: dict) -> None:
        """Append one event to the buffer (evicts oldest if full)."""
        self._buf.append(event)

    @property
    def is_ready(self) -> bool:
        """True when the buffer holds exactly `maxlen` events."""
        return len(self._buf) == self._buf.maxlen

    @property
    def fill_level(self) -> int:
        """Current number of events stored (0 … maxlen)."""
        return len(self._buf)

    def extract_features(self) -> pd.DataFrame | None:
        """
        Compute the micro-sifted 6-dimensional feature vector from the current
        window of events. Returns None if the buffer is not yet full.

        Feature computation:
          qber_overall     = (errors in sifted window) / (sifted bit count)
          qber_rectilinear = errors in rectilinear-basis sifted bits / count
          qber_diagonal    = errors in diagonal-basis sifted bits / count
          detector_voltage = mean APD voltage over the window
          timing_jitter    = mean APD jitter over the window
          photon_count_rate = fraction of events where Bob received a click
                             (= n_sifted / total_events)

        Returns:
            Single-row pd.DataFrame with columns matching FEATURE_COLUMNS,
            or None if the buffer is not full.
        """
        if not self.is_ready:
            return None

        events: list[dict] = list(self._buf)
        n: int = len(events)

        alice_basis: np.ndarray = np.array([e["alice_basis"] for e in events], dtype=np.int_)
        bob_basis:   np.ndarray = np.array([e["bob_basis"]   for e in events], dtype=np.int_)
        alice_bit:   np.ndarray = np.array([e["alice_bit"]   for e in events], dtype=np.int_)
        bob_bit:     np.ndarray = np.array([e["bob_bit"]     for e in events], dtype=np.int_)
        voltages:    np.ndarray = np.array([e["detector_voltage"] for e in events], dtype=np.float64)
        jitters:     np.ndarray = np.array([e["timing_jitter"]    for e in events], dtype=np.float64)

        # Sifting
        match:    np.ndarray = alice_basis == bob_basis
        error:    np.ndarray = (alice_bit  != bob_bit) & match
        is_rect:  np.ndarray = alice_basis == 0
        is_diag:  np.ndarray = alice_basis == 1

        n_sifted:   int = int(match.sum())
        n_err:      int = int(error.sum())
        n_err_r:    int = int((error & is_rect).sum())
        n_err_d:    int = int((error & is_diag).sum())
        n_count_r:  int = int((match & is_rect).sum())
        n_count_d:  int = int((match & is_diag).sum())

        qber_o: float = n_err   / n_sifted  if n_sifted  > 0 else 0.0
        qber_r: float = n_err_r / n_count_r if n_count_r > 0 else 0.0
        qber_d: float = n_err_d / n_count_d if n_count_d > 0 else 0.0

        count_rate: float = n_sifted / n  # fraction of detected + sifted events

        return pd.DataFrame([{
            "qber_overall":      qber_o,
            "qber_rectilinear":  qber_r,
            "qber_diagonal":     qber_d,
            "detector_voltage":  float(voltages.mean()),
            "timing_jitter":     float(jitters.mean()),
            "photon_count_rate": count_rate,
        }])
