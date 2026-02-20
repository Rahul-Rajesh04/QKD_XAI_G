"""
gui/main_window.py
PyQt6 IDS Dashboard — main application window.

Layout:
  ┌──────────────────────────────────────────────────────┐
  │  QKD Real-Time IDS Dashboard                         │
  ├──────────────────────────────────────────────────────┤
  │  [STATUS BANNER]  SYSTEM SECURE / ATTACK DETECTED    │
  ├────────────────┬─────────────────────────────────────┤
  │  Live Vitals   │  QBER Timeline (scrolling plot)      │
  │  Voltage: X.XV │                                      │
  │  Jitter:  X.Xns│                                      │
  │  QBER:   X.X%  │                                      │
  ├────────────────┴─────────────────────────────────────┤
  │  RF:  attack_blinding (99.8%)   SVM: ANOMALY         │
  ├──────────────────────────────────────────────────────┤
  │  Forensic Report text area                           │
  └──────────────────────────────────────────────────────┘

Usage:
    python gui/main_window.py [--attack none|timeshift|blinding]
"""
__author__ = "Rahul Rajesh 2360445"

import sys
import os
import argparse
import collections

# Ensure project root is on sys.path regardless of launch location
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from config.logging_config import configure_logging, get_logger

configure_logging()
log = get_logger("qkd.gui")

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget,
        QVBoxLayout, QHBoxLayout, QLabel,
        QTextEdit, QProgressBar, QSplitter,
        QFrame,
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont, QColor
    import pyqtgraph as pg         # pip install pyqtgraph
    _GUI_AVAILABLE = True
except ImportError as exc:
    _GUI_AVAILABLE = False
    log.error(
        f"GUI dependencies not available: {exc}. "
        "Run: pip install PyQt6 pyqtgraph"
    )

if _GUI_AVAILABLE:
    from gui.worker_thread import IDSWorker

    class IDSDashboard(QMainWindow):
        """
        Real-time IDS dashboard window.
        All widget updates happen in the main thread via the result_ready signal.
        """

        _HISTORY_LEN: int = 200   # Number of QBER points shown on the rolling plot

        # Alert colour palette
        _COLORS = {
            "normal":   ("#1e3a1e", "#4caf50"),   # dark green bg, bright green text
            "warning":  ("#3a2e00", "#ffca28"),   # amber
            "critical": ("#3a0d0d", "#ef5350"),   # red
        }

        def __init__(self, attack_mode: str = "none") -> None:
            super().__init__()
            self.setWindowTitle("QKD Real-Time IDS — Rahul Rajesh 2360445")
            self.resize(1100, 700)

            # Rolling QBER history for the plot
            self._qber_history: collections.deque[float] = collections.deque(
                [0.0] * self._HISTORY_LEN, maxlen=self._HISTORY_LEN
            )

            self._build_ui()
            self._start_worker(attack_mode)

        # ----------------------------------------------------------------
        # UI Construction
        # ----------------------------------------------------------------

        def _build_ui(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)
            root_layout = QVBoxLayout(central)
            root_layout.setSpacing(8)

            # ---- Status banner ------------------------------------------
            self._status_label = QLabel("⬤  INITIALISING…")
            self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._status_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
            self._status_label.setFixedHeight(48)
            self._set_status_style("warning")
            root_layout.addWidget(self._status_label)

            # ---- Middle row: vitals | QBER plot -------------------------
            mid_splitter = QSplitter(Qt.Orientation.Horizontal)

            vitals_frame = QFrame()
            vitals_frame.setFrameShape(QFrame.Shape.StyledPanel)
            vitals_frame.setFixedWidth(200)
            vitals_layout = QVBoxLayout(vitals_frame)
            vitals_layout.addWidget(QLabel("— Live Vitals —"))

            self._voltage_lbl = self._make_vital_label("Voltage:  — V")
            self._jitter_lbl  = self._make_vital_label("Jitter:   — ns")
            self._qber_lbl    = self._make_vital_label("QBER:     —")
            for lbl in (self._voltage_lbl, self._jitter_lbl, self._qber_lbl):
                vitals_layout.addWidget(lbl)

            vitals_layout.addStretch()

            # Buffer fill progress bar
            fill_label = QLabel("Buffer fill:")
            self._fill_bar = QProgressBar()
            self._fill_bar.setMaximum(500)
            self._fill_bar.setTextVisible(True)
            vitals_layout.addWidget(fill_label)
            vitals_layout.addWidget(self._fill_bar)

            mid_splitter.addWidget(vitals_frame)

            # QBER rolling plot
            self._plot_widget = pg.PlotWidget(title="QBER Timeline")
            self._plot_widget.setBackground("#0d0d0d")
            self._plot_widget.setYRange(0, 0.30, padding=0.05)
            self._plot_widget.setLabel("left",   "QBER")
            self._plot_widget.setLabel("bottom", "Window index")
            # Noise floor reference line
            self._plot_widget.addLine(y=0.04,  pen=pg.mkPen("#4caf50", style=Qt.PenStyle.DashLine))
            self._plot_widget.addLine(y=0.11,  pen=pg.mkPen("#ffca28", style=Qt.PenStyle.DashLine))
            self._qber_curve = self._plot_widget.plot(
                list(self._qber_history),
                pen=pg.mkPen("#29b6f6", width=2),
            )
            mid_splitter.addWidget(self._plot_widget)
            mid_splitter.setSizes([200, 900])
            root_layout.addWidget(mid_splitter)

            # ---- Model readout row --------------------------------------
            model_row = QHBoxLayout()
            self._rf_label  = QLabel("RF:  —")
            self._svm_label = QLabel("SVM: —")
            for lbl in (self._rf_label, self._svm_label):
                lbl.setFont(QFont("Consolas", 11))
                model_row.addWidget(lbl)
            root_layout.addLayout(model_row)

            # ---- Forensic report ----------------------------------------
            self._report_area = QTextEdit()
            self._report_area.setReadOnly(True)
            self._report_area.setFont(QFont("Consolas", 10))
            self._report_area.setFixedHeight(160)
            self._report_area.setPlaceholderText("Forensic report will appear here…")
            root_layout.addWidget(self._report_area)

            self.setStyleSheet("""
                QMainWindow { background-color: #121212; }
                QWidget { background-color: #121212; color: #e0e0e0; }
                QLabel { color: #e0e0e0; }
                QTextEdit { background-color: #1e1e1e; color: #b0bec5; border: 1px solid #333; }
                QFrame { border: 1px solid #333; border-radius: 4px; }
                QProgressBar { border: 1px solid #333; border-radius: 3px; }
                QProgressBar::chunk { background-color: #29b6f6; }
            """)

        @staticmethod
        def _make_vital_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setFont(QFont("Consolas", 11))
            lbl.setStyleSheet("padding: 4px;")
            return lbl

        def _set_status_style(self, level: str) -> None:
            bg, fg = self._COLORS.get(level, self._COLORS["warning"])
            self._status_label.setStyleSheet(
                f"background-color: {bg}; color: {fg}; border-radius: 4px; padding: 6px;"
            )

        # ----------------------------------------------------------------
        # Worker setup
        # ----------------------------------------------------------------

        def _start_worker(self, attack_mode: str) -> None:
            self._worker = IDSWorker(attack_mode=attack_mode)
            self._worker.result_ready.connect(self._on_result)
            self._worker.start()
            log.info(f"Dashboard: IDSWorker started (attack_mode={attack_mode})")

        # ----------------------------------------------------------------
        # Slot — called in GUI thread
        # ----------------------------------------------------------------

        def _on_result(self, result: dict) -> None:
            """Update all widgets from the inference result emitted by IDSWorker."""
            vitals      = result["vitals"]
            verdict     = result["verdict"]
            rf_pred     = result["rf_prediction"]
            rf_conf     = result["rf_confidence"]
            svm_anomaly = result["svm_anomaly"]
            flagged     = result["flagged"]
            report      = result["report"]

            # -- Status banner
            if verdict == "normal":
                self._status_label.setText("⬤  SYSTEM SECURE")
                self._set_status_style("normal")
            elif "ZERO-DAY" in verdict:
                self._status_label.setText(f"☢  {verdict}")
                self._set_status_style("critical")
            else:
                self._status_label.setText(f"⚠  ATTACK DETECTED — {rf_pred.upper()}")
                self._set_status_style("critical")

            # -- Live vitals
            self._voltage_lbl.setText(f"Voltage:  {vitals['voltage']:.2f} V")
            self._jitter_lbl.setText( f"Jitter:   {vitals['jitter']:.2f} ns")
            self._qber_lbl.setText(   f"QBER:     {vitals['qber']:.2%}")

            # -- QBER rolling plot
            self._qber_history.append(vitals["qber"])
            self._qber_curve.setData(list(self._qber_history))

            # -- Model readout
            self._rf_label.setText(
                f"RF: {rf_pred}  ({rf_conf:.1%})"
            )
            svm_text  = "SVM: ANOMALY ⚠" if svm_anomaly else "SVM: NORMAL ✓"
            svm_color = "#ef5350" if svm_anomaly else "#4caf50"
            self._svm_label.setText(svm_text)
            self._svm_label.setStyleSheet(f"color: {svm_color};")

            # -- Forensic report
            self._report_area.setPlainText(report)

        def closeEvent(self, event) -> None:
            log.info("Dashboard closing — stopping worker thread.")
            self._worker.stop()
            self._worker.wait(3000)   # wait up to 3 s for clean shutdown
            super().closeEvent(event)


    def main() -> None:
        parser = argparse.ArgumentParser(description="QKD Real-Time IDS Dashboard")
        parser.add_argument(
            "--attack",
            choices=["none", "timeshift", "blinding"],
            default="none",
            help="Inject an attack mode for demonstration.",
        )
        args = parser.parse_args()

        app = QApplication(sys.argv)
        app.setApplicationName("QKD IDS Dashboard")
        window = IDSDashboard(attack_mode=args.attack)
        window.show()
        sys.exit(app.exec())


    if __name__ == "__main__":
        main()

else:
    log.error("Cannot launch GUI — PyQt6 and/or pyqtgraph not installed.")
