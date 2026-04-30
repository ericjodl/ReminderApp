"""Transportleiste: Wiedergabe, Aufnahme, Stop, Geraete-Auswahl, Zoom."""
from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QPushButton, QSpacerItem,
                             QSizePolicy, QToolButton, QWidget)

from .audio_engine import AudioEngine


class TransportBar(QWidget):
    play_pressed = pyqtSignal()
    stop_pressed = pyqtSignal()
    record_pressed = pyqtSignal()
    rewind_pressed = pyqtSignal()
    zoom_in_pressed = pyqtSignal()
    zoom_out_pressed = pyqtSignal()
    input_device_changed = pyqtSignal(object)
    output_device_changed = pyqtSignal(object)

    def __init__(self, engine: AudioEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        self.btn_rewind = self._mk_btn("|<", "Zum Anfang", self.rewind_pressed.emit)
        self.btn_play = self._mk_btn(">", "Wiedergabe (Leertaste)", self.play_pressed.emit)
        self.btn_stop = self._mk_btn("[]", "Stop", self.stop_pressed.emit)
        self.btn_record = self._mk_btn("REC", "Aufnahme", self.record_pressed.emit)
        self.btn_record.setStyleSheet("background:#7a2222;color:#fff;font-weight:bold;")
        for b in (self.btn_rewind, self.btn_play, self.btn_stop, self.btn_record):
            layout.addWidget(b)

        layout.addSpacing(12)
        self.time_label = QLabel("0:00.000")
        self.time_label.setStyleSheet("font-family: Consolas, monospace; color:#e9ecf1; font-size:14px;")
        layout.addWidget(self.time_label)

        layout.addSpacing(16)
        layout.addWidget(QLabel("Eingang:"))
        self.cmb_in = QComboBox()
        self.cmb_in.setMinimumWidth(180)
        self._populate_inputs()
        self.cmb_in.currentIndexChanged.connect(self._on_input_changed)
        layout.addWidget(self.cmb_in)

        layout.addWidget(QLabel("Ausgang:"))
        self.cmb_out = QComboBox()
        self.cmb_out.setMinimumWidth(180)
        self._populate_outputs()
        self.cmb_out.currentIndexChanged.connect(self._on_output_changed)
        layout.addWidget(self.cmb_out)

        layout.addItem(QSpacerItem(20, 1, QSizePolicy.Policy.Expanding,
                                   QSizePolicy.Policy.Minimum))

        self.btn_zoom_out = self._mk_btn("-", "Auszoomen (Strg+Mausrad)",
                                         self.zoom_out_pressed.emit)
        self.btn_zoom_in = self._mk_btn("+", "Hineinzoomen", self.zoom_in_pressed.emit)
        layout.addWidget(self.btn_zoom_out)
        layout.addWidget(self.btn_zoom_in)

        self.setStyleSheet("""
            QWidget { background:#191a1e; }
            QLabel { color:#bfc4cc; }
            QPushButton { background:#2a2c33; color:#e9ecf1; border:1px solid #3a3d47;
                          border-radius:3px; padding:6px 10px; }
            QPushButton:hover { background:#33363f; }
            QComboBox { background:#2a2c33; color:#e9ecf1; border:1px solid #3a3d47;
                        padding:4px; }
            QComboBox QAbstractItemView { background:#2a2c33; color:#e9ecf1; selection-background-color:#3a6dff; }
        """)

    def _mk_btn(self, text: str, tip: str, slot: Callable[[], None]) -> QPushButton:
        b = QPushButton(text)
        b.setToolTip(tip)
        b.setMinimumWidth(40)
        b.clicked.connect(slot)
        return b

    def _populate_inputs(self):
        self.cmb_in.blockSignals(True)
        self.cmb_in.clear()
        self.cmb_in.addItem("(kein)", None)
        for idx, name in AudioEngine.list_input_devices():
            self.cmb_in.addItem(f"{name}", idx)
        self.cmb_in.blockSignals(False)

    def _populate_outputs(self):
        self.cmb_out.blockSignals(True)
        self.cmb_out.clear()
        self.cmb_out.addItem("(Standard)", None)
        for idx, name in AudioEngine.list_output_devices():
            self.cmb_out.addItem(f"{name}", idx)
        self.cmb_out.blockSignals(False)

    def _on_input_changed(self, _: int):
        idx = self.cmb_in.currentData()
        self.input_device_changed.emit(idx)

    def _on_output_changed(self, _: int):
        idx = self.cmb_out.currentData()
        self.output_device_changed.emit(idx)

    def update_time(self, samples: int, sample_rate: int):
        secs = samples / sample_rate if sample_rate else 0.0
        m = int(secs // 60)
        s = secs - m * 60
        self.time_label.setText(f"{m}:{s:06.3f}")

    def set_state(self, playing: bool, recording: bool):
        # einfaches Highlighting
        self.btn_play.setStyleSheet("background:#3a6dff;color:#fff;" if playing
                                    else "")
        self.btn_record.setStyleSheet(
            "background:#ff2020;color:#fff;font-weight:bold;" if recording
            else "background:#7a2222;color:#fff;font-weight:bold;")
