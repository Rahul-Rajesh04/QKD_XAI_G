__author__ = "Rahul Rajesh 2360445"

import sys
import os
import argparse
import collections

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
        QFrame, QComboBox
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont, QColor
    import pyqtgraph as pg        
    _GUI_AVAILABLE = True
except ImportError as exc:
    _GUI_AVAILABLE = False
    log.error(f"GUI dependencies not available: {exc}. Run: pip install PyQt6 pyqtgraph")

if _GUI_AVAILABLE:
    from gui.worker_thread import IDSWorker

    class IDSDashboard(QMainWindow):

        _HISTORY_LEN: int = 200   

        _COLORS = {
            "normal":   ("#1e3a1e", "#4caf50"),   
            "warning":  ("#3a2e00", "#ffca28"),   
            "critical": ("#3a0d0d", "#ef5350"),   
        }

        def __init__(self, attack_mode: str = "none") -> None:
            super().__init__()
            self.setWindowTitle("QKD Real-Time IDS — Rahul Rajesh 2360445")
            self.resize(1100, 750)

            self._qber_history: collections.deque[float] = collections.deque(
                [0.0] * self._HISTORY_LEN, maxlen=self._HISTORY_LEN
            )

            self._build_ui()
            self._set_initial_dropdown(attack_mode)
            self._start_worker(attack_mode)

        def _build_ui(self) -> None:
            central = QWidget()
            self.setCentralWidget(central)
            root_layout = QVBoxLayout(central)
            root_layout.setSpacing(8)

            self._status_label = QLabel("⬤  INITIALISING…")
            self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._status_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
            self._status_label.setFixedHeight(48)
            self._set_status_style("warning")
            root_layout.addWidget(self._status_label)

            control_layout = QHBoxLayout()
            control_label = QLabel("Active Simulation Mode:")
            control_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
            
            self._attack_selector = QComboBox()
            self._attack_selector.setFont(QFont("Consolas", 11))
            self._attack_selector.addItems([
                "Safe Transmission (None)", 
                "Time-Shift Attack", 
                "Blinding Attack", 
                "Zero-Day Anomaly"
            ])
            self._attack_selector.currentIndexChanged.connect(self._on_attack_changed)
            
            control_layout.addWidget(control_label)
            control_layout.addWidget(self._attack_selector)
            control_layout.addStretch()
            root_layout.addLayout(control_layout)

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

            fill_label = QLabel("Buffer fill:")
            self._fill_bar = QProgressBar()
            self._fill_bar.setMaximum(500)
            self._fill_bar.setTextVisible(True)
            vitals_layout.addWidget(fill_label)
            vitals_layout.addWidget(self._fill_bar)

            mid_splitter.addWidget(vitals_frame)

            self._plot_widget = pg.PlotWidget(title="QBER Timeline")
            self._plot_widget.setBackground("#0d0d0d")
            self._plot_widget.setYRange(0, 0.30, padding=0.05)
            self._plot_widget.setLabel("left",   "QBER")
            self._plot_widget.setLabel("bottom", "Window index")
            self._plot_widget.addLine(y=0.04,  pen=pg.mkPen("#4caf50", style=Qt.PenStyle.DashLine))
            self._plot_widget.addLine(y=0.11,  pen=pg.mkPen("#ffca28", style=Qt.PenStyle.DashLine))
            self._qber_curve = self._plot_widget.plot(
                list(self._qber_history),
                pen=pg.mkPen("#29b6f6", width=2),
            )
            mid_splitter.addWidget(self._plot_widget)
            mid_splitter.setSizes([200, 900])
            root_layout.addWidget(mid_splitter)

            model_row = QHBoxLayout()
            self._rf_label  = QLabel("RF:  —")
            self._svm_label = QLabel("SVM: —")
            for lbl in (self._rf_label, self._svm_label):
                lbl.setFont(QFont("Consolas", 11))
                model_row.addWidget(lbl)
            root_layout.addLayout(model_row)

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
                QComboBox { background-color: #1e1e1e; color: #e0e0e0; border: 1px solid #333; padding: 4px; }
                QComboBox QAbstractItemView { background-color: #1e1e1e; color: #e0e0e0; selection-background-color: #29b6f6; }
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

        def _set_initial_dropdown(self, attack_mode: str) -> None:
            mode_map = {"none": 0, "timeshift": 1, "blinding": 2, "zeroday": 3}
            if attack_mode in mode_map:
                self._attack_selector.setCurrentIndex(mode_map[attack_mode])

        def _on_attack_changed(self, index: int) -> None:
            mode_map = {0: "none", 1: "timeshift", 2: "blinding", 3: "zeroday"}
            selected_mode = mode_map.get(index, "none")
            
            self._worker.stop()
            self._worker.wait()
            
            self._status_label.setText("⬤  SWITCHING MODES...")
            self._set_status_style("warning")
            self._qber_history.clear()
            self._qber_history.extend([0.0] * self._HISTORY_LEN)
            self._qber_curve.setData(list(self._qber_history))
            self._report_area.clear()
            
            self._start_worker(selected_mode)

        def _start_worker(self, attack_mode: str) -> None:
            intensity = "blinding" if attack_mode == "blinding" else "single_photon"
            
            self._worker = IDSWorker(attack_mode=attack_mode, intensity_mode=intensity)
            self._worker.result_ready.connect(self._on_result)
            self._worker.start()
            log.info(f"Dashboard: IDSWorker started (attack={attack_mode}, intensity={intensity})")

        def _on_result(self, result: dict) -> None:
            vitals      = result["vitals"]
            verdict     = result["verdict"]
            rf_pred     = result["rf_prediction"]
            rf_conf     = result["rf_confidence"]
            svm_anomaly = result["svm_anomaly"]
            flagged     = result["flagged"]
            report      = result["report"]

            if verdict == "normal":
                self._status_label.setText("⬤  SYSTEM SECURE")
                self._set_status_style("normal")
            elif "ZERO-DAY" in verdict:
                self._status_label.setText(f"☢  {verdict}")
                self._set_status_style("critical")
            else:
                self._status_label.setText(f"⚠  ATTACK DETECTED — {rf_pred.upper()}")
                self._set_status_style("critical")

            self._voltage_lbl.setText(f"Voltage:  {vitals['voltage']:.2f} V")
            self._jitter_lbl.setText( f"Jitter:   {vitals['jitter']:.2f} ns")
            self._qber_lbl.setText(   f"QBER:     {vitals['qber']:.2%}")

            self._qber_history.append(vitals["qber"])
            self._qber_curve.setData(list(self._qber_history))

            self._rf_label.setText(f"RF: {rf_pred}  ({rf_conf:.1%})")
            
            svm_text  = "SVM: ANOMALY ⚠" if svm_anomaly else "SVM: NORMAL ✓"
            svm_color = "#ef5350" if svm_anomaly else "#4caf50"
            self._svm_label.setText(svm_text)
            self._svm_label.setStyleSheet(f"color: {svm_color};")

            self._report_area.setPlainText(report)

        def closeEvent(self, event) -> None:
            log.info("Dashboard closing — stopping worker thread.")
            self._worker.stop()
            self._worker.wait(3000)   
            super().closeEvent(event)


    def main() -> None:
        parser = argparse.ArgumentParser(description="QKD Real-Time IDS Dashboard")
        parser.add_argument(
            "--attack",
            choices=["none", "timeshift", "blinding", "zeroday"],
            default="none",
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