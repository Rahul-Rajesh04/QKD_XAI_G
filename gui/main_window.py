import sys
import os
import argparse
import collections
import csv
import time
from datetime import datetime

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
        QFrame, QComboBox, QTabWidget, QPushButton, QMessageBox, QSlider
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont, QPixmap
    import pyqtgraph as pg        
    _GUI_AVAILABLE = True
except ImportError as exc:
    _GUI_AVAILABLE = False
    log.error(f"GUI dependencies not available. Run: pip install PyQt6 pyqtgraph")

if _GUI_AVAILABLE:
    from gui.worker_thread import IDSWorker

    class IDSDashboard(QMainWindow):

        _HISTORY_LEN: int = 200   

        _COLORS = {
            "normal":   ("#051a0f", "#00ff66"),   
            "warning":  ("#1a1500", "#fcee0a"),   
            "critical": ("#1a0505", "#ff003c"),   
        }

        def __init__(self, attack_mode: str = "none") -> None:
            super().__init__()
            self.setWindowTitle("QKD Real-Time IDS - Rahul Rajesh 2360445")
            self.resize(1200, 800)

            self._qber_history: collections.deque[float] = collections.deque(
                [0.0] * self._HISTORY_LEN, maxlen=self._HISTORY_LEN
            )
            
            self._last_abort_log_time = 0.0
            self._last_warn_log_time = 0.0

            self._init_environmental_logs()
            self._build_ui()
            self._set_initial_dropdown(attack_mode)
            self._start_worker(attack_mode)

        def _init_environmental_logs(self) -> None:
            self._degradation_log = os.path.join(_PROJECT_ROOT, "logs", "channel_degradation.csv")
            self._abort_log = os.path.join(_PROJECT_ROOT, "logs", "critical_aborts.csv")
            
            os.makedirs(os.path.dirname(self._degradation_log), exist_ok=True)
            
            if not os.path.exists(self._degradation_log):
                with open(self._degradation_log, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow(["Timestamp", "Warning_Type", "Live_QBER", "Noise_Threshold", "Voltage", "Jitter"])
                    
            if not os.path.exists(self._abort_log):
                with open(self._abort_log, 'w', newline='', encoding='utf-8') as f:
                    csv.writer(f).writerow(["Timestamp", "Event_Type", "Live_QBER", "Abort_Threshold", "Voltage", "Jitter"])

        def _create_panel(self) -> QFrame:
            frame = QFrame()
            frame.setObjectName("panel")
            return frame

        def _build_ui(self) -> None:
            self._tabs = QTabWidget()
            self.setCentralWidget(self._tabs)

            telemetry_tab = QWidget()
            root_layout = QVBoxLayout(telemetry_tab)
            root_layout.setContentsMargins(15, 15, 15, 15)
            root_layout.setSpacing(15)

            self._status_label = QLabel("[ INITIALISING... ]")
            self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._status_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
            self._status_label.setFixedHeight(55)
            self._set_status_style("warning")
            root_layout.addWidget(self._status_label)

            top_controls_layout = QHBoxLayout()
            
            control_panel = self._create_panel()
            control_layout = QHBoxLayout(control_panel)
            control_layout.setContentsMargins(15, 10, 15, 10)
            
            control_label = QLabel("Active Mode:")
            control_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            
            self._attack_selector = QComboBox()
            self._attack_selector.setFont(QFont("Consolas", 10))
            self._attack_selector.setMinimumWidth(200)
            self._attack_selector.addItems([
                "Safe Transmission (None)", 
                "Time-Shift Attack", 
                "Blinding Attack", 
                "Zero-Day Anomaly"
            ])
            self._attack_selector.currentIndexChanged.connect(self._on_attack_changed)
            
            self._clear_btn = QPushButton("Clear All Logs")
            self._clear_btn.setObjectName("dangerBtn")
            self._clear_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self._clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._clear_btn.clicked.connect(self._clear_logs)
            
            control_layout.addWidget(control_label)
            control_layout.addWidget(self._attack_selector)
            control_layout.addStretch()
            control_layout.addWidget(self._clear_btn)
            
            top_controls_layout.addWidget(control_panel)
            
            slider_panel = self._create_panel()
            slider_layout = QHBoxLayout(slider_panel)
            slider_layout.setContentsMargins(15, 10, 15, 10)
            
            self._noise_lbl = QLabel("Noise Floor: 4.0%")
            self._noise_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self._noise_slider = QSlider(Qt.Orientation.Horizontal)
            self._noise_slider.setRange(0, 300)
            self._noise_slider.setValue(40)
            self._noise_slider.setCursor(Qt.CursorShape.PointingHandCursor)
            self._noise_slider.valueChanged.connect(self._update_thresholds)
            
            self._abort_lbl = QLabel("Abort Threshold: 11.0%")
            self._abort_lbl.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
            self._abort_slider = QSlider(Qt.Orientation.Horizontal)
            self._abort_slider.setRange(0, 300)
            self._abort_slider.setValue(110)
            self._abort_slider.setCursor(Qt.CursorShape.PointingHandCursor)
            self._abort_slider.valueChanged.connect(self._update_thresholds)
            
            slider_layout.addWidget(self._noise_lbl)
            slider_layout.addWidget(self._noise_slider)
            slider_layout.addSpacing(30)
            slider_layout.addWidget(self._abort_lbl)
            slider_layout.addWidget(self._abort_slider)
            
            top_controls_layout.addWidget(slider_panel)
            root_layout.addLayout(top_controls_layout)

            mid_splitter = QSplitter(Qt.Orientation.Horizontal)
            mid_splitter.setHandleWidth(10)

            vitals_frame = self._create_panel()
            vitals_frame.setFixedWidth(220)
            vitals_layout = QVBoxLayout(vitals_frame)
            vitals_layout.setContentsMargins(15, 15, 15, 15)
            
            vitals_title = QLabel("LIVE VITALS")
            vitals_title.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
            vitals_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
            vitals_title.setStyleSheet("color: #777777; margin-bottom: 10px;")
            vitals_layout.addWidget(vitals_title)

            self._voltage_lbl = self._make_vital_label("Voltage:  — V")
            self._jitter_lbl  = self._make_vital_label("Jitter:   — ns")
            self._qber_lbl    = self._make_vital_label("QBER:     —")
            for lbl in (self._voltage_lbl, self._jitter_lbl, self._qber_lbl):
                vitals_layout.addWidget(lbl)

            vitals_layout.addStretch()

            fill_label = QLabel("Buffer Fill Status")
            fill_label.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
            fill_label.setStyleSheet("color: #777777;")
            self._fill_bar = QProgressBar()
            self._fill_bar.setMaximum(500)
            self._fill_bar.setTextVisible(False)
            self._fill_bar.setFixedHeight(6)
            vitals_layout.addWidget(fill_label)
            vitals_layout.addWidget(self._fill_bar)

            mid_splitter.addWidget(vitals_frame)

            graph_panel = self._create_panel()
            graph_layout = QVBoxLayout(graph_panel)
            graph_layout.setContentsMargins(5, 5, 5, 5)
            
            self._plot_widget = pg.PlotWidget()
            self._plot_widget.setBackground("#050505")
            self._plot_widget.setYRange(0, 0.30, padding=0.05)
            self._plot_widget.getAxis("left").enableAutoSIPrefix(False)
            self._plot_widget.getAxis("left").setPen(pg.mkPen(color="#333333"))
            self._plot_widget.getAxis("bottom").setPen(pg.mkPen(color="#333333"))
            self._plot_widget.setLabel("left",   "QBER")
            self._plot_widget.setLabel("bottom", "Window index")
            self._plot_widget.showGrid(x=True, y=True, alpha=0.2)
            self._plot_widget.setMouseEnabled(x=False, y=False)
            self._plot_widget.hideButtons()
            self._plot_widget.setLimits(yMin=0.0, yMax=1.0)
            
            self._noise_line = pg.InfiniteLine(angle=0, pen=pg.mkPen("#00ff66", style=Qt.PenStyle.DashLine, width=1.5))
            self._noise_line.setValue(0.04)
            self._plot_widget.addItem(self._noise_line)
            
            self._abort_line = pg.InfiniteLine(angle=0, pen=pg.mkPen("#fcee0a", style=Qt.PenStyle.DashLine, width=1.5))
            self._abort_line.setValue(0.11)
            self._plot_widget.addItem(self._abort_line)
            
            self._qber_curve = self._plot_widget.plot(
                list(self._qber_history),
                pen=pg.mkPen("#00f0ff", width=2.5),
                fillLevel=0.0,
                fillBrush=pg.mkBrush(0, 240, 255, 30)
            )
            graph_layout.addWidget(self._plot_widget)
            mid_splitter.addWidget(graph_panel)
            
            mid_splitter.setSizes([220, 980])
            root_layout.addWidget(mid_splitter)

            bottom_panel = self._create_panel()
            bottom_layout = QVBoxLayout(bottom_panel)
            bottom_layout.setContentsMargins(15, 10, 15, 15)
            
            model_row = QHBoxLayout()
            self._rf_label  = QLabel("RF Decision:  —")
            self._svm_label = QLabel("SVM Status: —")
            for lbl in (self._rf_label, self._svm_label):
                lbl.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
                model_row.addWidget(lbl)
            bottom_layout.addLayout(model_row)

            self._report_area = QTextEdit()
            self._report_area.setReadOnly(True)
            self._report_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._report_area.setFont(QFont("Consolas", 10))
            self._report_area.setFixedHeight(140)
            self._report_area.setPlaceholderText("Forensic ML narrative will stream here...")
            bottom_layout.addWidget(self._report_area)
            
            root_layout.addWidget(bottom_panel)

            self._tabs.addTab(telemetry_tab, "Live Telemetry")

            xai_tab = QWidget()
            xai_layout = QVBoxLayout(xai_tab)
            xai_layout.setContentsMargins(15, 15, 15, 15)
            self._xai_image_label = QLabel("Awaiting anomaly detection to populate visual evidence...")
            self._xai_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._xai_image_label.setFont(QFont("Consolas", 12))
            self._xai_image_label.setStyleSheet("color: #777777;")
            xai_layout.addWidget(self._xai_image_label)
            self._tabs.addTab(xai_tab, "Visual Forensics (XAI)")

            self.setStyleSheet("""
                QMainWindow { background-color: #050505; }
                QWidget { color: #e0e0e0; font-family: 'Consolas', monospace; }
                
                QFrame#panel { 
                    background-color: #0a0a0a; 
                    border: 1px solid #1f1f1f; 
                    border-radius: 4px; 
                }
                
                QComboBox { 
                    background-color: #0f0f0f; 
                    color: #ff003c; 
                    border: 1px solid #333333; 
                    padding: 6px 12px; 
                    border-radius: 2px; 
                }
                QComboBox::drop-down { border: none; }
                QComboBox QAbstractItemView { 
                    background-color: #0f0f0f; 
                    color: #e0e0e0; 
                    selection-background-color: #ff003c; 
                    selection-color: #000000;
                    border: 1px solid #333333;
                }
                
                QPushButton#dangerBtn { 
                    background-color: #1a0505; 
                    color: #ff003c; 
                    border: 1px solid #ff003c; 
                    padding: 6px 16px; 
                    border-radius: 2px; 
                }
                QPushButton#dangerBtn:hover { 
                    background-color: #ff003c; 
                    color: #000000;
                }
                
                QTextEdit { 
                    background-color: #0a0a0a; 
                    color: #00ff66; 
                    border: 1px solid #1f1f1f; 
                    border-radius: 2px;
                    padding: 8px;
                }
                
                QProgressBar { 
                    border: 1px solid #1f1f1f; 
                    background-color: #050505; 
                    border-radius: 2px; 
                }
                QProgressBar::chunk { 
                    background-color: #00f0ff; 
                    width: 4px;
                    margin: 0.5px;
                }
                
                QTabWidget::pane { border: 1px solid #1f1f1f; border-radius: 4px; top: -1px; }
                QTabBar::tab { 
                    background: #0a0a0a; 
                    color: #777777; 
                    padding: 10px 20px; 
                    border: 1px solid #1f1f1f;
                    border-bottom: none;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                    margin-right: 2px;
                    font-weight: bold;
                }
                QTabBar::tab:selected { 
                    background: #ff003c; 
                    color: #000000; 
                    border: 1px solid #ff003c;
                }
                
                QSlider { min-height: 24px; }
                QSlider::groove:horizontal { 
                    border: none; 
                    height: 4px; 
                    background: #1f1f1f; 
                    border-radius: 2px; 
                }
                QSlider::handle:horizontal { 
                    background: #ff003c; 
                    border: none; 
                    width: 16px; 
                    height: 16px; 
                    margin: -6px 0; 
                    border-radius: 8px; 
                }
                QSlider::sub-page:horizontal {
                    background: #ff003c;
                    border-radius: 2px;
                }
            """)

        def _update_thresholds(self) -> None:
            noise_val = self._noise_slider.value() / 1000.0
            abort_val = self._abort_slider.value() / 1000.0
            
            self._noise_lbl.setText(f"Noise Floor: {noise_val*100:.1f}%")
            self._abort_lbl.setText(f"Abort Threshold: {abort_val*100:.1f}%")
            
            self._noise_line.setValue(noise_val)
            self._abort_line.setValue(abort_val)

        @staticmethod
        def _make_vital_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setFont(QFont("Consolas", 12))
            lbl.setStyleSheet("background-color: #0f0f0f; border: 1px solid #1f1f1f; border-radius: 2px; padding: 8px; color: #e0e0e0;")
            return lbl

        def _set_status_style(self, level: str) -> None:
            bg, fg = self._COLORS.get(level, self._COLORS["warning"])
            self._status_label.setStyleSheet(
                f"background-color: {bg}; color: {fg}; border: 1px solid {fg}; border-radius: 2px; padding: 6px; letter-spacing: 1px;"
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
            
            self._status_label.setText("[ SWITCHING MODES... ]")
            self._set_status_style("warning")
            self._qber_history.clear()
            self._qber_history.extend([0.0] * self._HISTORY_LEN)
            self._qber_curve.setData(list(self._qber_history))
            self._report_area.clear()
            self._xai_image_label.clear()
            self._xai_image_label.setText("Awaiting anomaly detection to populate visual evidence...")
            self._fill_bar.setValue(0)
            
            self._start_worker(selected_mode)

        def _clear_logs(self) -> None:
            log_dir = os.path.join(_PROJECT_ROOT, "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            with open(os.path.join(log_dir, "threat_telemetry.csv"), 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(["Timestamp", "System_Verdict", "Detected_Signature", "Confidence", "SVM_Triggered", "Voltage", "Jitter", "QBER"])
            
            with open(self._degradation_log, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(["Timestamp", "Warning_Type", "Live_QBER", "Noise_Threshold", "Voltage", "Jitter"])
                
            with open(self._abort_log, 'w', newline='', encoding='utf-8') as f:
                csv.writer(f).writerow(["Timestamp", "Event_Type", "Live_QBER", "Abort_Threshold", "Voltage", "Jitter"])
                
            QMessageBox.information(self, "Logs Cleared", "All telemetry, degradation, and abort logs have been successfully wiped and reset.")

        def _start_worker(self, attack_mode: str) -> None:
            intensity = "blinding" if attack_mode == "blinding" else "single_photon"
            
            self._worker = IDSWorker(attack_mode=attack_mode, intensity_mode=intensity)
            self._worker.result_ready.connect(self._on_result)
            self._worker.start()

        def _on_result(self, result: dict) -> None:
            vitals      = result["vitals"]
            verdict     = result["verdict"]
            rf_pred     = result["rf_prediction"]
            rf_conf     = result["rf_confidence"]
            svm_anomaly = result["svm_anomaly"]
            flagged     = result["flagged"]
            report      = result["report"]

            self._fill_bar.setValue(500)

            noise_threshold = self._noise_slider.value() / 1000.0
            abort_threshold = self._abort_slider.value() / 1000.0
            current_qber = vitals["qber"]
            
            is_qber_abort = current_qber >= abort_threshold
            is_noise_warning = current_qber > noise_threshold and not is_qber_abort

            if is_qber_abort:
                self._status_label.setText(f"[ CRITICAL ABORT: QBER EXCEEDS {abort_threshold:.1%} ]")
                self._set_status_style("critical")
                self._xai_image_label.clear()
                self._xai_image_label.setText("Connection Aborted: High QBER threshold breached.")
                report = f"CRITICAL SYSTEM ABORT\nLive QBER ({current_qber:.2%}) exceeds the dynamic abort threshold ({abort_threshold:.1%}).\nKey generation suspended to prevent eavesdropping."
                
                if time.time() - self._last_abort_log_time > 5.0:
                    with open(self._abort_log, 'a', newline='', encoding='utf-8') as f:
                        csv.writer(f).writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "THRESHOLD_BREACH_ABORT",
                            f"{current_qber*100:.2f}%",
                            f"{abort_threshold*100:.1f}%",
                            f"{vitals['voltage']:.2f} V",
                            f"{vitals['jitter']:.3f} ns"
                        ])
                    self._last_abort_log_time = time.time()

            elif "ZERO-DAY" in verdict:
                self._status_label.setText(f"[ {verdict} ]")
                self._set_status_style("critical")
                self._xai_image_label.clear()
                self._xai_image_label.setText("Zero-Day Anomaly Detected.\nNo pre-computed SHAP evidence available for unclassified threats.")
            elif verdict != "normal":
                self._status_label.setText(f"[ ATTACK DETECTED: {rf_pred.upper()} ]")
                self._set_status_style("critical")

            elif is_noise_warning:
                self._status_label.setText("[ WARNING: ELEVATED CHANNEL NOISE ]")
                self._set_status_style("warning")
                self._xai_image_label.clear()
                self._xai_image_label.setText(f"No attack detected, but channel noise ({current_qber:.2%}) exceeds baseline ({noise_threshold:.1%}).")
                report = f"ELEVATED NOISE WARNING\nLive QBER is above the expected baseline.\nThis indicates fiber degradation, temperature fluctuation, or misalignment.\nSecure key rate is degraded."
                
                if time.time() - self._last_warn_log_time > 5.0:
                    with open(self._degradation_log, 'a', newline='', encoding='utf-8') as f:
                        csv.writer(f).writerow([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "ELEVATED_NOISE_WARNING",
                            f"{current_qber*100:.2f}%",
                            f"{noise_threshold*100:.1f}%",
                            f"{vitals['voltage']:.2f} V",
                            f"{vitals['jitter']:.3f} ns"
                        ])
                    self._last_warn_log_time = time.time()
                    
            else:
                self._status_label.setText("[ SYSTEM SECURE ]")
                self._set_status_style("normal")
                self._xai_image_label.clear()
                self._xai_image_label.setText("System Secure. No active anomalies.")

            self._voltage_lbl.setText(f"Voltage:  {vitals['voltage']:>5.2f} V")
            self._jitter_lbl.setText( f"Jitter:   {vitals['jitter']:>5.2f} ns")
            self._qber_lbl.setText(   f"QBER:     {vitals['qber']:>5.2%}")

            self._qber_history.append(vitals["qber"])
            self._qber_curve.setData(list(self._qber_history))

            self._rf_label.setText(f"RF: {rf_pred}  ({rf_conf:.1%})")
            
            svm_text  = "SVM: ANOMALY ALERT" if svm_anomaly else "SVM: NORMAL"
            svm_color = "#ff003c" if svm_anomaly else "#00ff66" 
            self._svm_label.setText(svm_text)
            self._svm_label.setStyleSheet(f"color: {svm_color};")

            self._report_area.setPlainText(report)

            if not is_qber_abort and not is_noise_warning:
                if rf_pred == "attack_blinding" and flagged:
                    img_path = os.path.join(_PROJECT_ROOT, "Results", "Forensic_Evidence", "Evidence_Blinding_Attack_Summary.png")
                    if os.path.exists(img_path):
                        pixmap = QPixmap(img_path)
                        self._xai_image_label.setPixmap(pixmap.scaled(1000, 600, Qt.AspectRatioMode.KeepAspectRatio))
                elif rf_pred == "attack_timeshift" and flagged:
                    img_path = os.path.join(_PROJECT_ROOT, "Results", "Forensic_Evidence", "Evidence_TimeShift_Attack_Summary.png")
                    if os.path.exists(img_path):
                        pixmap = QPixmap(img_path)
                        self._xai_image_label.setPixmap(pixmap.scaled(1000, 600, Qt.AspectRatioMode.KeepAspectRatio))

        def closeEvent(self, event) -> None:
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
        app.setStyle("Fusion") 
        app.setApplicationName("QKD IDS Dashboard")
        window = IDSDashboard(attack_mode=args.attack)
        window.show()
        sys.exit(app.exec())

    if __name__ == "__main__":
        main()

else:
    log.error("Cannot launch GUI. PyQt6 and/or pyqtgraph not installed.")