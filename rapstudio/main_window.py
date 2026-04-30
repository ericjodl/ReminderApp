"""Hauptfenster der Anwendung."""
from __future__ import annotations

import os
import sys
import traceback
from typing import Dict, List, Optional

import numpy as np
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (QApplication, QFileDialog, QHBoxLayout, QLabel, QMainWindow,
                             QMenuBar, QMessageBox, QScrollArea, QVBoxLayout, QWidget)

from . import APP_NAME, __version__
from .audio_engine import AudioEngine
from .io_utils import export_mp3, export_wav, load_audio
from .project import Clip, Project, Track
from .timeline import TimelineCanvas
from .track_header import TrackHeaderWidget
from .transport import TransportBar


DARK_STYLE = """
QMainWindow, QWidget { background:#1e1f24; color:#e9ecf1; }
QMenuBar { background:#191a1e; color:#e9ecf1; }
QMenuBar::item:selected { background:#3a6dff; }
QMenu { background:#23252b; color:#e9ecf1; border:1px solid #3a3d47; }
QMenu::item:selected { background:#3a6dff; }
QScrollBar:horizontal, QScrollBar:vertical {
    background:#191a1e; border:none; width:12px; height:12px;
}
QScrollBar::handle { background:#3a3d47; border-radius:4px; min-width:20px; min-height:20px; }
QScrollBar::handle:hover { background:#4a4d57; }
QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
"""


class HeaderColumn(QWidget):
    """Container fuer Track-Header links."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # Spacer fuer Lineal-Hoehe
        self.top_spacer = QWidget()
        self.top_spacer.setFixedHeight(TimelineCanvas.RULER_HEIGHT)
        self.top_spacer.setStyleSheet("background:#191a1e;")
        layout.addWidget(self.top_spacer)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        layout.addWidget(self.list_container)
        layout.addStretch(1)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        self.resize(1400, 800)

        self.project = Project(sample_rate=48000, channels=2)
        # Standard: 2 Spuren (Beat + Vocals)
        beat = self.project.add_track("Beat")
        vocals = self.project.add_track("Vocals")
        vocals.armed = True

        self.engine = AudioEngine(self.project)

        self._build_ui()
        self._build_menu()
        self._wire_signals()

        # Periodische Aktualisierung von Zeitanzeige + Timeline-Repaint
        self._tick = QTimer(self)
        self._tick.setInterval(33)
        self._tick.timeout.connect(self._on_tick)
        self._tick.start()

        # Threadsicherheit: Engine-Callbacks nicht direkt nutzen,
        # Timer pollt stattdessen.
        self.engine.on_position_changed = None
        self.engine.on_state_changed = None

        self._refresh_track_headers()
        self.setStyleSheet(DARK_STYLE)

    # ---- UI-Aufbau ----
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.transport = TransportBar(self.engine)
        outer.addWidget(self.transport)

        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)
        outer.addWidget(body, 1)

        # Linke Header-Spalte in eigenem Scrollbereich (nur vertikal)
        self.header_scroll = QScrollArea()
        self.header_scroll.setWidgetResizable(True)
        self.header_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.header_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.header_scroll.setFixedWidth(240)
        self.header_column = HeaderColumn()
        self.header_scroll.setWidget(self.header_column)
        body_layout.addWidget(self.header_scroll)

        # Trennlinie
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background:#15161a;")
        body_layout.addWidget(sep)

        # Timeline in einem Scrollbereich (horizontal + vertikal)
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setWidgetResizable(False)
        self.timeline = TimelineCanvas(self.project, self.engine)
        self.timeline_scroll.setWidget(self.timeline)
        body_layout.addWidget(self.timeline_scroll, 1)

        # Vertikale Scroll-Synchronisation
        self.timeline_scroll.verticalScrollBar().valueChanged.connect(
            self._sync_header_scroll_from_timeline)

        # Statusleiste
        self.statusBar().showMessage("Bereit. Druecke Leertaste fuer Wiedergabe.")

        # Header-Map: Track -> Widget
        self._header_widgets: Dict[int, TrackHeaderWidget] = {}

    def _sync_header_scroll_from_timeline(self, value: int):
        self.header_scroll.verticalScrollBar().setValue(value)

    def _build_menu(self):
        bar: QMenuBar = self.menuBar()
        m_file = bar.addMenu("Datei")
        m_edit = bar.addMenu("Bearbeiten")
        m_track = bar.addMenu("Spur")
        m_help = bar.addMenu("Hilfe")

        act_import = QAction("Audio importieren ...", self)
        act_import.setShortcut(QKeySequence("Ctrl+I"))
        act_import.triggered.connect(self._on_import)
        m_file.addAction(act_import)

        act_export_wav = QAction("Als WAV exportieren ...", self)
        act_export_wav.setShortcut(QKeySequence("Ctrl+E"))
        act_export_wav.triggered.connect(lambda: self._on_export("wav"))
        m_file.addAction(act_export_wav)

        act_export_mp3 = QAction("Als MP3 exportieren ...", self)
        act_export_mp3.triggered.connect(lambda: self._on_export("mp3"))
        m_file.addAction(act_export_mp3)

        m_file.addSeparator()
        act_quit = QAction("Beenden", self)
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        m_file.addAction(act_quit)

        act_split = QAction("Am Playhead schneiden", self)
        act_split.setShortcut(QKeySequence("S"))
        act_split.triggered.connect(self.timeline.split_selected_at_playhead)
        m_edit.addAction(act_split)

        act_delete = QAction("Auswahl loeschen", self)
        act_delete.setShortcut(QKeySequence("Del"))
        act_delete.triggered.connect(self.timeline.delete_selected_clips)
        m_edit.addAction(act_delete)

        act_zoom_in = QAction("Hineinzoomen", self)
        act_zoom_in.setShortcut(QKeySequence("Ctrl+="))
        act_zoom_in.triggered.connect(lambda: self.timeline.set_zoom(self.timeline.pps * 1.25))
        m_edit.addAction(act_zoom_in)

        act_zoom_out = QAction("Auszoomen", self)
        act_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        act_zoom_out.triggered.connect(lambda: self.timeline.set_zoom(self.timeline.pps / 1.25))
        m_edit.addAction(act_zoom_out)

        act_add_track = QAction("Neue Spur", self)
        act_add_track.setShortcut(QKeySequence("Ctrl+T"))
        act_add_track.triggered.connect(self._on_add_track)
        m_track.addAction(act_add_track)

        act_about = QAction("Ueber RapStudio", self)
        act_about.triggered.connect(self._on_about)
        m_help.addAction(act_about)

        # Globaler Shortcut fuer Leertaste -> Play/Stop
        act_play = QAction("Play/Stop", self)
        act_play.setShortcut(QKeySequence(Qt.Key.Key_Space))
        act_play.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        act_play.triggered.connect(self._toggle_play)
        self.addAction(act_play)

        act_record = QAction("Aufnahme", self)
        act_record.setShortcut(QKeySequence("R"))
        act_record.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
        act_record.triggered.connect(self._toggle_record)
        self.addAction(act_record)

    def _wire_signals(self):
        self.transport.play_pressed.connect(self._toggle_play)
        self.transport.stop_pressed.connect(self._on_stop)
        self.transport.record_pressed.connect(self._toggle_record)
        self.transport.rewind_pressed.connect(self._on_rewind)
        self.transport.zoom_in_pressed.connect(
            lambda: self.timeline.set_zoom(self.timeline.pps * 1.25))
        self.transport.zoom_out_pressed.connect(
            lambda: self.timeline.set_zoom(self.timeline.pps / 1.25))
        self.transport.input_device_changed.connect(self.engine.set_input_device)
        self.transport.output_device_changed.connect(self.engine.set_output_device)

    # ---- Tick ----
    def _on_tick(self):
        self.timeline.update()
        self.transport.update_time(self.engine.playhead, self.project.sample_rate)
        self.transport.set_state(self.engine.is_playing, self.engine.is_recording)

    # ---- Track-Header ----
    def _refresh_track_headers(self):
        # Vorhandene Widgets abraeumen
        layout = self.header_column.list_layout
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        self._header_widgets.clear()

        for t in self.project.tracks:
            w = TrackHeaderWidget(t, on_remove=self._on_remove_track)
            w.changed.connect(self.timeline.update)
            layout.addWidget(w)
            self._header_widgets[id(t)] = w
        self.header_column.list_container.adjustSize()
        self.timeline.refresh()

    def _on_remove_track(self, track: Track):
        if QMessageBox.question(self, "Spur loeschen",
                                f"Spur '{track.name}' wirklich loeschen?") != QMessageBox.StandardButton.Yes:
            return
        self.project.remove_track(track)
        self._refresh_track_headers()

    def _on_add_track(self):
        self.project.add_track()
        self._refresh_track_headers()

    # ---- Transport-Aktionen ----
    def _toggle_play(self):
        if self.engine.is_playing or self.engine.is_recording:
            self.engine.stop()
        else:
            try:
                self.engine.play()
            except Exception as e:
                QMessageBox.critical(self, "Wiedergabe", str(e))

    def _toggle_record(self):
        if self.engine.is_recording:
            self.engine.stop()
            return
        if self.engine.is_playing:
            self.engine.stop()
        try:
            self.engine.record()
        except Exception as e:
            QMessageBox.critical(self, "Aufnahme", str(e))

    def _on_stop(self):
        self.engine.stop()

    def _on_rewind(self):
        self.engine.playhead = 0
        self.timeline.update()

    # ---- Import / Export ----
    def _on_import(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Audio importieren", "",
            "Audio (*.wav *.mp3 *.flac *.ogg *.m4a *.aac);;Alle Dateien (*.*)")
        if not path:
            return
        try:
            data, sr = load_audio(path, self.project.sample_rate)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Import fehlgeschlagen",
                                 f"Konnte Datei nicht laden:\n{e}")
            return
        # Zielspur: erste nicht-armed Spur, sonst neue Spur
        target = next((t for t in self.project.tracks if not t.armed), None)
        if target is None:
            target = self.project.add_track(os.path.basename(path))
            self._refresh_track_headers()
        clip = Clip(data=data, start_sample=self.engine.playhead,
                    name=os.path.basename(path))
        target.add_clip(clip)
        self.timeline.refresh()
        self.statusBar().showMessage(f"Importiert: {path} ({sr} Hz)")

    def _on_export(self, fmt: str):
        if self.project.length_samples() == 0:
            QMessageBox.information(self, "Export", "Nichts zum Exportieren.")
            return
        if fmt == "wav":
            path, _ = QFileDialog.getSaveFileName(self, "Als WAV exportieren",
                                                  "mix.wav", "WAV (*.wav)")
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Als MP3 exportieren",
                                                  "mix.mp3", "MP3 (*.mp3)")
        if not path:
            return
        try:
            mix = self._render_mixdown()
            if fmt == "wav":
                export_wav(path, mix, self.project.sample_rate)
            else:
                export_mp3(path, mix, self.project.sample_rate)
            self.statusBar().showMessage(f"Exportiert: {path}")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Export fehlgeschlagen", str(e))

    def _render_mixdown(self) -> np.ndarray:
        sr = self.project.sample_rate
        ch = self.project.channels
        total = self.project.length_samples()
        if total <= 0:
            return np.zeros((0, ch), dtype=np.float32)
        out = np.zeros((total, ch), dtype=np.float32)
        # Block-weise mischen via engine._mix_block ist nicht moeglich (Playhead!),
        # darum direkte Berechnung:
        has_solo = self.project.has_solo()
        for track in self.project.tracks:
            if track.mute:
                continue
            if has_solo and not track.solo:
                continue
            l_gain = float(track.gain) * np.sqrt(0.5 * (1.0 - track.pan))
            r_gain = float(track.gain) * np.sqrt(0.5 * (1.0 + track.pan))
            for clip in track.clips:
                cs = clip.start_sample
                ce = clip.end_sample
                if ce <= 0 or cs >= total:
                    continue
                view = clip.view()
                a = max(0, cs)
                b = min(total, ce)
                local_start = a - cs
                local_end = local_start + (b - a)
                seg = view[local_start:local_end]
                if seg.ndim == 1:
                    out[a:b, 0] += seg * (l_gain * clip.gain)
                    if ch >= 2:
                        out[a:b, 1] += seg * (r_gain * clip.gain)
                else:
                    out[a:b, 0] += seg[:, 0] * (l_gain * clip.gain)
                    if ch >= 2:
                        right = seg[:, -1] if seg.shape[1] > 1 else seg[:, 0]
                        out[a:b, 1] += right * (r_gain * clip.gain)
        np.clip(out, -1.0, 1.0, out=out)
        return out

    def _on_about(self):
        QMessageBox.about(
            self, "Ueber RapStudio",
            f"<h2>{APP_NAME} {__version__}</h2>"
            "<p>Einfacher Mehrspur-Recorder fuer Rap & Vocals.</p>"
            "<p><b>Tasten:</b><br>"
            "Leertaste = Play/Stop<br>"
            "R = Aufnahme starten/beenden<br>"
            "S = Am Playhead schneiden<br>"
            "Entf = Auswahl loeschen<br>"
            "Strg+I = Audio importieren<br>"
            "Strg+E = Als WAV exportieren<br>"
            "Strg+T = Neue Spur<br>"
            "Strg+Mausrad = Zoom</p>")

    # ---- Lifecycle ----
    def closeEvent(self, event):
        try:
            self.engine.shutdown()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
