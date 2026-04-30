"""Audio-Engine: Aufnahme, Wiedergabe und Echtzeit-Mischen ueber sounddevice."""
from __future__ import annotations

import threading
from typing import Callable, List, Optional, Tuple

import numpy as np
import sounddevice as sd

from .project import Clip, Project, Track


class AudioEngine:
    BLOCK_SIZE = 1024

    def __init__(self, project: Project):
        self.project = project
        self._lock = threading.RLock()

        self._playhead = 0          # in Samples
        self._is_playing = False
        self._is_recording = False
        self._loop_enabled = False
        self._loop_start = 0
        self._loop_end = 0

        self._input_device: Optional[int] = None
        self._output_device: Optional[int] = None
        self._input_channels = 1

        self._stream: Optional[sd.Stream] = None

        # Aufnahme-State
        self._record_track: Optional[Track] = None
        self._record_buffer: List[np.ndarray] = []
        self._record_start_sample = 0

        # Callbacks fuer die UI
        self.on_position_changed: Optional[Callable[[int], None]] = None
        self.on_state_changed: Optional[Callable[[], None]] = None

    # ---- Geraete ----
    @staticmethod
    def list_input_devices() -> List[Tuple[int, str]]:
        try:
            devs = sd.query_devices()
        except Exception:
            return []
        return [(i, d["name"]) for i, d in enumerate(devs) if d["max_input_channels"] > 0]

    @staticmethod
    def list_output_devices() -> List[Tuple[int, str]]:
        try:
            devs = sd.query_devices()
        except Exception:
            return []
        return [(i, d["name"]) for i, d in enumerate(devs) if d["max_output_channels"] > 0]

    def set_input_device(self, index: Optional[int]):
        self._input_device = index
        if index is not None:
            try:
                info = sd.query_devices(index)
                self._input_channels = max(1, min(2, int(info["max_input_channels"])))
            except Exception:
                self._input_channels = 1

    def set_output_device(self, index: Optional[int]):
        self._output_device = index

    # ---- Status ----
    @property
    def playhead(self) -> int:
        return self._playhead

    @playhead.setter
    def playhead(self, value: int):
        self._playhead = max(0, int(value))
        if self.on_position_changed:
            self.on_position_changed(self._playhead)

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    # ---- Mixing ----
    def _mix_block(self, start: int, frames: int) -> np.ndarray:
        out = np.zeros((frames, self.project.channels), dtype=np.float32)
        has_solo = self.project.has_solo()
        for track in self.project.tracks:
            if track.mute:
                continue
            if has_solo and not track.solo:
                continue
            track_gain = float(track.gain)
            pan = float(track.pan)
            # Equal-power-Panning (vereinfacht)
            l_gain = track_gain * np.sqrt(0.5 * (1.0 - pan))
            r_gain = track_gain * np.sqrt(0.5 * (1.0 + pan))
            for clip in track.clips:
                cs = clip.start_sample
                ce = clip.end_sample
                if ce <= start or cs >= start + frames:
                    continue
                local_start = max(0, start - cs)
                local_end = min(clip.length, start + frames - cs)
                if local_end <= local_start:
                    continue
                out_start = max(0, cs - start)
                out_end = out_start + (local_end - local_start)
                view = clip.view()[local_start:local_end]
                if view.ndim == 1:
                    seg_l = view * (l_gain * clip.gain)
                    seg_r = view * (r_gain * clip.gain)
                else:
                    seg_l = view[:, 0] * (l_gain * clip.gain)
                    seg_r = view[:, -1] * (r_gain * clip.gain)
                out[out_start:out_end, 0] += seg_l
                if self.project.channels >= 2:
                    out[out_start:out_end, 1] += seg_r
        # Begrenze auf [-1, 1] um harte Clipping-Verzerrungen zu vermeiden
        np.clip(out, -1.0, 1.0, out=out)
        return out

    # ---- Stream-Callback ----
    def _stream_callback(self, indata, outdata, frames, time_info, status):
        # Wiedergabe
        with self._lock:
            start = self._playhead
            mix = self._mix_block(start, frames)
            outdata[:] = mix

            # Aufnahme
            if self._is_recording and self._record_track is not None and indata is not None:
                # indata: (frames, channels)
                buf = np.array(indata, dtype=np.float32, copy=True)
                if buf.shape[1] == 1:
                    buf = buf[:, 0]
                self._record_buffer.append(buf)

            self._playhead += frames
            if self._loop_enabled and self._loop_end > self._loop_start:
                if self._playhead >= self._loop_end:
                    self._playhead = self._loop_start

        if self.on_position_changed:
            # Achtung: Callback laeuft im Audio-Thread; Qt-Signal sollte threadsicher sein.
            self.on_position_changed(self._playhead)

    # ---- Transport ----
    def _open_stream(self, with_input: bool):
        sr = self.project.sample_rate
        if with_input:
            self._stream = sd.Stream(
                samplerate=sr,
                blocksize=self.BLOCK_SIZE,
                device=(self._input_device, self._output_device),
                channels=(self._input_channels, self.project.channels),
                dtype="float32",
                callback=self._stream_callback,
                latency="low",
            )
        else:
            self._stream = sd.OutputStream(
                samplerate=sr,
                blocksize=self.BLOCK_SIZE,
                device=self._output_device,
                channels=self.project.channels,
                dtype="float32",
                callback=self._output_only_callback,
                latency="low",
            )
        self._stream.start()

    def _output_only_callback(self, outdata, frames, time_info, status):
        with self._lock:
            mix = self._mix_block(self._playhead, frames)
            outdata[:] = mix
            self._playhead += frames
            if self._loop_enabled and self._loop_end > self._loop_start:
                if self._playhead >= self._loop_end:
                    self._playhead = self._loop_start
        if self.on_position_changed:
            self.on_position_changed(self._playhead)

    def play(self):
        if self._is_playing or self._is_recording:
            return
        self._is_playing = True
        try:
            self._open_stream(with_input=False)
        except Exception as e:
            self._is_playing = False
            raise
        if self.on_state_changed:
            self.on_state_changed()

    def record(self):
        """Startet Aufnahme auf der ersten 'armed' Spur und gleichzeitig Wiedergabe der anderen."""
        if self._is_playing or self._is_recording:
            return
        armed = next((t for t in self.project.tracks if t.armed), None)
        if armed is None:
            raise RuntimeError("Keine Spur ist scharfgeschaltet (Aufnahme-Knopf an der Spur).")
        if self._input_device is None:
            raise RuntimeError("Kein Eingabegeraet ausgewaehlt.")
        self._record_track = armed
        self._record_buffer = []
        self._record_start_sample = self._playhead
        self._is_recording = True
        try:
            self._open_stream(with_input=True)
        except Exception:
            self._is_recording = False
            self._record_track = None
            raise
        if self.on_state_changed:
            self.on_state_changed()

    def stop(self):
        was_recording = self._is_recording
        rec_track = self._record_track
        rec_buffer = self._record_buffer
        rec_start = self._record_start_sample

        self._is_playing = False
        self._is_recording = False
        self._record_track = None
        self._record_buffer = []

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if was_recording and rec_track is not None and rec_buffer:
            data = np.concatenate(rec_buffer, axis=0).astype(np.float32, copy=False)
            clip = Clip(data=data, start_sample=rec_start,
                        name=f"Take {len(rec_track.clips) + 1}")
            with self._lock:
                rec_track.add_clip(clip)

        if self.on_state_changed:
            self.on_state_changed()

    def shutdown(self):
        self.stop()
