"""Timeline-Widget mit Lineal, Spuren-Lanes, Wellenform und Schneiden."""
from __future__ import annotations

from typing import List, Optional, Tuple

import numpy as np
from PyQt6.QtCore import QPoint, QRect, Qt, pyqtSignal
from PyQt6.QtGui import (QAction, QBrush, QColor, QFont, QKeySequence, QMouseEvent,
                         QPainter, QPen, QWheelEvent)
from PyQt6.QtWidgets import QMenu, QWidget

from .audio_engine import AudioEngine
from .project import Clip, Project, Track


def compute_peaks(data: np.ndarray, num_buckets: int) -> Tuple[np.ndarray, np.ndarray]:
    if data.ndim > 1:
        data = data.mean(axis=1)
    n = data.shape[0]
    if num_buckets <= 0 or n == 0:
        empty = np.zeros(0, dtype=np.float32)
        return empty, empty
    if num_buckets >= n:
        return data.astype(np.float32, copy=False), data.astype(np.float32, copy=False)
    bucket_size = n // num_buckets
    truncated = data[: bucket_size * num_buckets].reshape(num_buckets, bucket_size)
    mins = truncated.min(axis=1).astype(np.float32, copy=False)
    maxs = truncated.max(axis=1).astype(np.float32, copy=False)
    return mins, maxs


class TimelineCanvas(QWidget):
    RULER_HEIGHT = 28
    TRACK_HEIGHT = 80
    EDGE_GRAB = 6
    MIN_PPS = 5.0
    MAX_PPS = 2000.0

    playheadChanged = pyqtSignal(int)
    selectionChanged = pyqtSignal()
    projectChanged = pyqtSignal()

    def __init__(self, project: Project, engine: AudioEngine, parent=None):
        super().__init__(parent)
        self.project = project
        self.engine = engine
        self.pps = 100.0  # Pixel pro Sekunde
        self._drag_mode: Optional[str] = None  # 'move' | 'trim_left' | 'trim_right' | 'playhead'
        self._drag_clip: Optional[Clip] = None
        self._drag_track: Optional[Track] = None
        self._drag_offset_samples = 0
        self._drag_origin_start = 0
        self._drag_origin_offset = 0
        self._drag_origin_length = 0

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self._update_size()

    # ---- Konvertierung ----
    def sample_to_x(self, sample: int) -> int:
        return int(sample / self.project.sample_rate * self.pps)

    def x_to_sample(self, x: int) -> int:
        if self.pps <= 0:
            return 0
        return int(x * self.project.sample_rate / self.pps)

    def track_index_at_y(self, y: int) -> int:
        if y < self.RULER_HEIGHT:
            return -1
        idx = (y - self.RULER_HEIGHT) // self.TRACK_HEIGHT
        if 0 <= idx < len(self.project.tracks):
            return int(idx)
        return -1

    def track_y(self, idx: int) -> int:
        return self.RULER_HEIGHT + idx * self.TRACK_HEIGHT

    # ---- Groesse ----
    def _update_size(self):
        length_s = max(self.project.length_seconds(), 60.0)  # mindestens 60 s anzeigen
        w = int(length_s * self.pps) + 400
        h = self.RULER_HEIGHT + max(1, len(self.project.tracks)) * self.TRACK_HEIGHT + 4
        self.setMinimumSize(w, h)
        self.resize(w, h)

    def refresh(self):
        self._update_size()
        self.update()
        self.projectChanged.emit()

    def set_zoom(self, pps: float, anchor_x: Optional[int] = None):
        old_pps = self.pps
        new_pps = max(self.MIN_PPS, min(self.MAX_PPS, pps))
        if new_pps == old_pps:
            return
        self.pps = new_pps
        self._update_size()
        self.update()

    # ---- Painting ----
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        rect = event.rect()

        # Hintergrund
        painter.fillRect(rect, QColor("#1e1f24"))

        # Lineal
        self._paint_ruler(painter, rect)

        # Spuren-Lanes
        for i, track in enumerate(self.project.tracks):
            y = self.track_y(i)
            lane_rect = QRect(0, y, self.width(), self.TRACK_HEIGHT)
            if not lane_rect.intersects(rect):
                continue
            # Abwechselnde Hintergrundfarben
            painter.fillRect(lane_rect,
                             QColor("#23252b") if i % 2 == 0 else QColor("#26282f"))
            # Mittellinie
            mid = y + self.TRACK_HEIGHT // 2
            painter.setPen(QPen(QColor("#2c2f37"), 1, Qt.PenStyle.SolidLine))
            painter.drawLine(0, mid, self.width(), mid)
            # Untere Trennlinie
            painter.setPen(QPen(QColor("#15161a"), 1))
            painter.drawLine(0, y + self.TRACK_HEIGHT - 1,
                             self.width(), y + self.TRACK_HEIGHT - 1)

            # Clips
            for clip in track.clips:
                self._paint_clip(painter, track, clip, y)

        # Playhead
        ph_x = self.sample_to_x(self.engine.playhead)
        painter.setPen(QPen(QColor("#ff5050"), 2))
        painter.drawLine(ph_x, 0, ph_x, self.height())

        painter.end()

    def _paint_ruler(self, painter: QPainter, rect: QRect):
        ruler_rect = QRect(0, 0, self.width(), self.RULER_HEIGHT)
        painter.fillRect(ruler_rect, QColor("#191a1e"))
        painter.setPen(QPen(QColor("#2c2f37"), 1))
        painter.drawLine(0, self.RULER_HEIGHT - 1, self.width(), self.RULER_HEIGHT - 1)

        # Rasterabstand abhaengig vom Zoom
        if self.pps >= 200:
            major_step = 1.0
        elif self.pps >= 80:
            major_step = 2.0
        elif self.pps >= 30:
            major_step = 5.0
        elif self.pps >= 12:
            major_step = 10.0
        else:
            major_step = 30.0

        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.setPen(QColor("#9aa0aa"))
        end_s = self.x_to_sample(rect.right()) / self.project.sample_rate + 1
        start_s = max(0.0, self.x_to_sample(rect.left()) / self.project.sample_rate - major_step)
        t = (int(start_s / major_step)) * major_step
        while t < end_s:
            x = int(t * self.pps)
            painter.setPen(QPen(QColor("#3a3d47"), 1))
            painter.drawLine(x, 0, x, self.height())
            painter.setPen(QColor("#bfc4cc"))
            mins = int(t // 60)
            secs = int(t - mins * 60)
            painter.drawText(x + 4, 16, f"{mins}:{secs:02d}")
            t += major_step

    def _paint_clip(self, painter: QPainter, track: Track, clip: Clip, lane_y: int):
        x1 = self.sample_to_x(clip.start_sample)
        x2 = self.sample_to_x(clip.end_sample)
        if x2 <= 0 or x1 > self.width():
            return
        clip_rect = QRect(x1, lane_y + 4, max(2, x2 - x1), self.TRACK_HEIGHT - 8)

        # Korpus
        body = QColor("#3a6dff") if not clip.selected else QColor("#ffa040")
        body.setAlpha(80)
        painter.fillRect(clip_rect, body)

        # Rand
        border = QColor("#7099ff") if not clip.selected else QColor("#ffb060")
        painter.setPen(QPen(border, 1 if not clip.selected else 2))
        painter.drawRect(clip_rect)

        # Wellenform
        self._paint_waveform(painter, clip, clip_rect)

        # Name
        painter.setPen(QColor("#e9ecf1"))
        font = QFont()
        font.setPointSize(8)
        painter.setFont(font)
        painter.drawText(clip_rect.adjusted(6, 2, -4, 0),
                         Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
                         clip.name)

    def _paint_waveform(self, painter: QPainter, clip: Clip, rect: QRect):
        if rect.width() < 2:
            return
        view = clip.view()
        if view.size == 0:
            return
        # Sichtbaren Bereich beschneiden
        widget_w = self.width()
        vx1 = max(0, rect.x())
        vx2 = min(widget_w, rect.right())
        if vx2 <= vx1:
            return
        # Welcher Sample-Bereich entspricht dem sichtbaren Pixelbereich?
        sample_per_px = self.project.sample_rate / self.pps
        offset_in_view_start = int((vx1 - rect.x()) * sample_per_px)
        offset_in_view_end = int((vx2 - rect.x()) * sample_per_px)
        offset_in_view_start = max(0, min(view.shape[0], offset_in_view_start))
        offset_in_view_end = max(0, min(view.shape[0], offset_in_view_end))
        if offset_in_view_end <= offset_in_view_start:
            return
        slice_data = view[offset_in_view_start:offset_in_view_end]
        num_buckets = max(1, vx2 - vx1)
        mins, maxs = compute_peaks(slice_data, num_buckets)
        center_y = rect.y() + rect.height() / 2.0
        amp = rect.height() / 2.0 - 2
        painter.setPen(QPen(QColor("#cfe2ff"), 1))
        for i in range(len(mins)):
            x = vx1 + i
            top = int(center_y - max(-1.0, min(1.0, float(maxs[i]))) * amp)
            bot = int(center_y - max(-1.0, min(1.0, float(mins[i]))) * amp)
            if top == bot:
                bot = top + 1
            painter.drawLine(x, top, x, bot)

    # ---- Maus / Tastatur ----
    def _hit_clip(self, x: int, y: int) -> Tuple[Optional[Track], Optional[Clip], str]:
        idx = self.track_index_at_y(y)
        if idx < 0:
            return None, None, "none"
        track = self.project.tracks[idx]
        for clip in reversed(track.clips):
            x1 = self.sample_to_x(clip.start_sample)
            x2 = self.sample_to_x(clip.end_sample)
            if x1 - 2 <= x <= x2 + 2:
                if abs(x - x1) <= self.EDGE_GRAB:
                    return track, clip, "edge_left"
                if abs(x - x2) <= self.EDGE_GRAB:
                    return track, clip, "edge_right"
                return track, clip, "body"
        return track, None, "lane"

    def _clear_selection(self):
        for t in self.project.tracks:
            for c in t.clips:
                c.selected = False

    def mousePressEvent(self, event: QMouseEvent):
        x = int(event.position().x())
        y = int(event.position().y())

        # Klick im Lineal -> Playhead
        if y < self.RULER_HEIGHT:
            sample = max(0, self.x_to_sample(x))
            self.engine.playhead = sample
            self._drag_mode = "playhead"
            self.playheadChanged.emit(sample)
            self.update()
            return

        track, clip, where = self._hit_clip(x, y)
        if event.button() == Qt.MouseButton.LeftButton:
            if clip is None:
                # Leere Stelle: Playhead setzen + Auswahl loeschen
                self._clear_selection()
                self.engine.playhead = max(0, self.x_to_sample(x))
                self._drag_mode = "playhead"
                self.playheadChanged.emit(self.engine.playhead)
                self.selectionChanged.emit()
                self.update()
                return
            # Clip getroffen
            if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                self._clear_selection()
            clip.selected = True
            self._drag_clip = clip
            self._drag_track = track
            self._drag_origin_start = clip.start_sample
            self._drag_origin_offset = clip.offset
            self._drag_origin_length = clip.length
            self._drag_offset_samples = self.x_to_sample(x) - clip.start_sample
            if where == "edge_left":
                self._drag_mode = "trim_left"
            elif where == "edge_right":
                self._drag_mode = "trim_right"
            else:
                self._drag_mode = "move"
            self.selectionChanged.emit()
            self.update()
            return

        if event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint(), x, y, track, clip)

    def mouseMoveEvent(self, event: QMouseEvent):
        x = int(event.position().x())
        y = int(event.position().y())

        if self._drag_mode == "playhead":
            self.engine.playhead = max(0, self.x_to_sample(x))
            self.playheadChanged.emit(self.engine.playhead)
            self.update()
            return

        if self._drag_mode == "move" and self._drag_clip is not None:
            new_start = self.x_to_sample(x) - self._drag_offset_samples
            new_start = max(0, new_start)
            self._drag_clip.start_sample = new_start
            # Optional: Track wechseln je nach y
            new_idx = self.track_index_at_y(y)
            if new_idx >= 0 and self._drag_track is not None:
                new_track = self.project.tracks[new_idx]
                if new_track is not self._drag_track:
                    self._drag_track.remove_clip(self._drag_clip)
                    new_track.add_clip(self._drag_clip)
                    self._drag_track = new_track
            self.refresh()
            return

        if self._drag_mode in ("trim_left", "trim_right") and self._drag_clip is not None:
            sample = self.x_to_sample(x)
            clip = self._drag_clip
            if self._drag_mode == "trim_left":
                # neue linke Kante in Timeline-Samples
                delta = sample - self._drag_origin_start
                # Begrenzen: nicht negativ, nicht groesser als urspruengliche Laenge - 1
                delta = max(-self._drag_origin_offset,
                            min(self._drag_origin_length - 1, delta))
                clip.start_sample = self._drag_origin_start + delta
                clip.offset = self._drag_origin_offset + delta
                clip.length = self._drag_origin_length - delta
            else:  # trim_right
                new_end = max(clip.start_sample + 1, sample)
                max_end = clip.start_sample + (len(clip.data) - clip.offset)
                new_end = min(new_end, max_end)
                clip.length = new_end - clip.start_sample
            clip.invalidate_peaks()
            self.refresh()
            return

        # Cursorform anpassen
        track, clip, where = self._hit_clip(x, y)
        if clip is not None and where in ("edge_left", "edge_right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif clip is not None:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_mode = None
        self._drag_clip = None
        self._drag_track = None

    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.2 if delta > 0 else 1.0 / 1.2
            self.set_zoom(self.pps * factor, anchor_x=int(event.position().x()))
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_selected_clips()
            event.accept()
            return
        if event.key() == Qt.Key.Key_S:
            self.split_selected_at_playhead()
            event.accept()
            return
        super().keyPressEvent(event)

    # ---- Aktionen ----
    def delete_selected_clips(self):
        changed = False
        for t in self.project.tracks:
            to_delete = [c for c in t.clips if c.selected]
            for c in to_delete:
                t.remove_clip(c)
                changed = True
        if changed:
            self.refresh()
            self.selectionChanged.emit()

    def split_selected_at_playhead(self):
        ph = self.engine.playhead
        new_clips: List[Tuple[Track, Clip]] = []
        for t in self.project.tracks:
            for c in list(t.clips):
                if c.selected and c.start_sample < ph < c.end_sample:
                    right = c.split_at(ph)
                    if right is not None:
                        new_clips.append((t, right))
        for t, c in new_clips:
            t.add_clip(c)
        if new_clips:
            self.refresh()

    def split_clip_at(self, track: Track, clip: Clip, sample: int):
        right = clip.split_at(sample)
        if right is not None:
            track.add_clip(right)
            self.refresh()

    def _show_context_menu(self, global_pos, x: int, y: int,
                           track: Optional[Track], clip: Optional[Clip]):
        menu = QMenu(self)
        if clip is not None and track is not None:
            sample_at_cursor = max(clip.start_sample + 1,
                                   min(clip.end_sample - 1, self.x_to_sample(x)))
            act_split = QAction("An Cursor schneiden", self)
            act_split.triggered.connect(lambda: self.split_clip_at(track, clip, sample_at_cursor))
            menu.addAction(act_split)

            act_split_ph = QAction("Am Playhead schneiden", self)
            act_split_ph.triggered.connect(
                lambda: self.split_clip_at(track, clip, self.engine.playhead))
            menu.addAction(act_split_ph)

            act_delete = QAction("Loeschen", self)
            act_delete.setShortcut(QKeySequence("Del"))
            act_delete.triggered.connect(lambda: (track.remove_clip(clip), self.refresh()))
            menu.addAction(act_delete)
        else:
            act_paste = QAction("Playhead hierhin", self)
            act_paste.triggered.connect(lambda: setattr(self.engine, "playhead",
                                                       self.x_to_sample(x)))
            menu.addAction(act_paste)
        menu.exec(global_pos)
