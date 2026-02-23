import sys
import os
import argparse
import collections
import functools

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
        QFrame, QPushButton, QTabWidget, QSlider
    )
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont
    import pyqtgraph as pg        
    _GUI_AVAILABLE = True
except ImportError as exc:
    _GUI_AVAILABLE = False
    log.error(f"GUI dependencies not available. Run: pip install PyQt6 pyqtgraph")

if _GUI_AVAILABLE:
    from gui.worker_thread import IDSWorker

    class SandboxDashboard(QMainWindow):

        _HISTORY_LEN: int = 200   

        _COLORS = {
            "normal":   ("#051a0f", "#00ff66"),   
            "warning":  ("#1a1500", "#fcee0a"),   
            "critical": ("#1a0505", "#ff003c"),   
        }

        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle("QKD Live-Fire Sandbox - Rahul Rajesh 2360445")
            self.resize(1200, 800)

            self._qber_history: collections.deque[float] = collections.deque(
                [0.0] * self._HISTORY_LEN, maxlen=self._HISTORY_LEN
            )
            
            self._injection_timer = QTimer()
            self._injection_timer.setSingleShot(True)
            self._injection_timer.timeout.connect(self._reset_button_styles)

            self._build_ui()
            self._start_worker()

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

            self._status_label = QLabel("[ SYSTEM SECURE ]")
            self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._status_label.setFont(QFont("Consolas", 16, QFont.Weight.Bold))
            self._status_label.setFixedHeight(55)
            self._set_status_style("normal")
            root_layout.addWidget(self._status_label)

            top_controls_layout = QHBoxLayout()

            control_frame = self._create_panel()
            control_layout = QHBoxLayout(control_frame)
            control_layout.setContentsMargins(15, 10, 15, 10)
            
            control_label = QLabel("Live Attack Injection (25000 Events):")
            control_label.setFont(QFont("Consolas", 11, QFont.Weight.Bold))
            control_label.setStyleSheet("border: none; padding-right: 15px;")
            control_layout.addWidget(control_label)
            
            self._btn_timeshift = self._create_injection_button("Inject Time-Shift", "timeshift")
            self._btn_blinding = self._create_injection_button("Inject Blinding", "blinding")
            self._btn_zeroday = self._create_injection_button("Inject Zero-Day", "zeroday")
            
            control_layout.addWidget(self._btn_timeshift)
            control_layout.addWidget(self._btn_blinding)
            control_layout.addWidget(self._btn_zeroday)
            control_layout.addStretch()
            
            top_controls_layout.addWidget(control_frame)

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
            self._fill_bar.setFixedHeight(8)
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

            self.setStyleSheet("""
                QMainWindow { background-color: #050505; }
                QWidget { color: #e0e0e0; font-family: 'Consolas', monospace; }
                
                QFrame#panel { 
                    background-color: #0a0a0a; 
                    border: 1px solid #1f1f1f; 
                    border-radius: 4px; 
                }
                
                QPushButton { 
                    background-color: #1a0505; 
                    color: #ff003c; 
                    border: 1px solid #ff003c; 
                    padding: 8px 16px; 
                    border-radius: 2px;
                    font-weight: bold;
                }
                QPushButton:hover { 
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

        def _create_injection_button(self, text: str, attack_mode: str) -> QPushButton:
            btn = QPushButton(text)
            btn.clicked.connect(functools.partial(self._trigger_injection, attack_mode, btn))
            return btn

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

        def _trigger_injection(self, attack_mode: str, button: QPushButton) -> None:
            self._worker.inject_attack(attack_mode, 25000)
            button.setStyleSheet("background-color: #ff003c; color: #000000; font-weight: bold;")
            self._injection_timer.start(4000) 

        def _reset_button_styles(self) -> None:
            style = "background-color: #1a0505; color: #ff003c; border: 1px solid #ff003c; padding: 8px 16px; border-radius: 2px; font-weight: bold;"
            self._btn_timeshift.setStyleSheet(style)
            self._btn_blinding.setStyleSheet(style)
            self._btn_zeroday.setStyleSheet(style)

        def _start_worker(self) -> None:
            self._worker = IDSWorker(attack_mode="none", intensity_mode="single_photon")
            self._worker.result_ready.connect(self._on_result)
            self._worker.start()

        def _on_result(self, result: dict) -> None:
            vitals      = result["vitals"]
            verdict     = result["verdict"]
            rf_pred     = result["rf_prediction"]
            rf_conf     = result["rf_confidence"]
            svm_anomaly = result["svm_anomaly"]
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
                report = f"CRITICAL SYSTEM ABORT\nLive QBER ({current_qber:.2%}) exceeds the dynamic abort threshold ({abort_threshold:.1%}).\nKey generation suspended to prevent eavesdropping."
            elif "ZERO-DAY" in verdict:
                self._status_label.setText(f"[ {verdict} ]")
                self._set_status_style("critical")
            elif verdict != "normal":
                self._status_label.setText(f"[ ATTACK DETECTED: {rf_pred.upper()} ]")
                self._set_status_style("critical")
            elif is_noise_warning:
                self._status_label.setText("[ WARNING: ELEVATED CHANNEL NOISE ]")
                self._set_status_style("warning")
                report = f"ELEVATED NOISE WARNING\nLive QBER is above the expected baseline.\nThis indicates fiber degradation, temperature fluctuation, or misalignment.\nSecure key rate is degraded."
            else:
                self._status_label.setText("[ SYSTEM SECURE ]")
                self._set_status_style("normal")

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

        def closeEvent(self, event) -> None:
            self._worker.stop()
            self._worker.wait(3000)   
            super().closeEvent(event)

    def main() -> None:
        app = QApplication(sys.argv)
        app.setStyle("Fusion") 
        app.setApplicationName("QKD Live-Fire Sandbox")
        window = SandboxDashboard()
        window.show()
        sys.exit(app.exec())

    if __name__ == "__main__":
        main()

else:
    log.error("Cannot launch GUI. PyQt6 and/or pyqtgraph not installed.")