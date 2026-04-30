"""Track-Kopf links neben der Timeline (Name, Mute, Solo, Arm, Lautstaerke)."""
from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QPushButton, QSlider,
                             QSizePolicy, QVBoxLayout, QWidget)

from .project import Track


class TrackHeaderWidget(QWidget):
    HEIGHT = 80
    changed = pyqtSignal()

    def __init__(self, track: Track, on_remove, parent=None):
        super().__init__(parent)
        self.track = track
        self._on_remove = on_remove
        self.setFixedHeight(self.HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 6, 8, 6)
        outer.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(6)
        self.name_edit = QLineEdit(track.name)
        self.name_edit.setStyleSheet("background:#2a2c33;color:#e9ecf1;border:1px solid #3a3d47;")
        self.name_edit.editingFinished.connect(self._on_name_changed)
        top.addWidget(self.name_edit, 1)

        self.btn_remove = QPushButton("X")
        self.btn_remove.setFixedSize(22, 22)
        self.btn_remove.setToolTip("Spur loeschen")
        self.btn_remove.clicked.connect(self._remove)
        top.addWidget(self.btn_remove)

        outer.addLayout(top)

        mid = QHBoxLayout()
        mid.setSpacing(4)
        self.btn_mute = QPushButton("M")
        self.btn_solo = QPushButton("S")
        self.btn_arm = QPushButton("REC")
        for b in (self.btn_mute, self.btn_solo, self.btn_arm):
            b.setCheckable(True)
            b.setFixedHeight(22)
        self.btn_mute.setFixedWidth(28)
        self.btn_solo.setFixedWidth(28)
        self.btn_arm.setFixedWidth(40)
        self.btn_mute.toggled.connect(self._on_mute)
        self.btn_solo.toggled.connect(self._on_solo)
        self.btn_arm.toggled.connect(self._on_arm)
        mid.addWidget(self.btn_mute)
        mid.addWidget(self.btn_solo)
        mid.addWidget(self.btn_arm)

        self.vol = QSlider(Qt.Orientation.Horizontal)
        self.vol.setRange(0, 200)
        self.vol.setValue(int(track.gain * 100))
        self.vol.setToolTip("Lautstaerke")
        self.vol.valueChanged.connect(self._on_vol)
        mid.addWidget(self.vol, 1)
        outer.addLayout(mid)

        self.setStyleSheet("""
            QPushButton { background:#2a2c33; color:#e9ecf1; border:1px solid #3a3d47;
                          border-radius:3px; }
            QPushButton:hover { background:#33363f; }
            QPushButton:checked { background:#ff8040; color:#1c1d22; border:1px solid #ffa060; }
            #mute:checked { background:#ffa040; }
            #solo:checked { background:#ffd040; color:#1c1d22; }
            #arm:checked { background:#ff4040; color:#fff; }
            QLabel { color:#bfc4cc; }
            QSlider::groove:horizontal { background:#2a2c33; height:6px; border-radius:3px; }
            QSlider::handle:horizontal { background:#7099ff; width:12px; margin:-4px 0; border-radius:6px; }
        """)
        self.btn_mute.setObjectName("mute")
        self.btn_solo.setObjectName("solo")
        self.btn_arm.setObjectName("arm")
        self._refresh()

    def _refresh(self):
        self.btn_mute.setChecked(self.track.mute)
        self.btn_solo.setChecked(self.track.solo)
        self.btn_arm.setChecked(self.track.armed)

    def _on_name_changed(self):
        self.track.name = self.name_edit.text() or self.track.name
        self.changed.emit()

    def _on_mute(self, val: bool):
        self.track.mute = val
        self.changed.emit()

    def _on_solo(self, val: bool):
        self.track.solo = val
        self.changed.emit()

    def _on_arm(self, val: bool):
        self.track.armed = val
        self.changed.emit()

    def _on_vol(self, val: int):
        self.track.gain = val / 100.0
        self.changed.emit()

    def _remove(self):
        self._on_remove(self.track)
