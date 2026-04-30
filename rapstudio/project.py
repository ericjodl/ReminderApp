"""Datenmodell: Projekt -> Tracks -> Clips."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class Clip:
    """Ein Audio-Schnipsel auf einer Spur. Daten sind float32 mono oder stereo."""
    data: np.ndarray              # shape (n_samples,) oder (n_samples, channels)
    start_sample: int             # Position auf der Timeline in Samples
    name: str = "Clip"
    gain: float = 1.0             # linearer Multiplikator
    offset: int = 0               # Anzahl Samples die vom Anfang abgeschnitten sind
    length: int = 0               # Effektive Lange (kann <= len(data) - offset sein)
    selected: bool = False
    _peaks_cache: Optional[tuple] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self.length == 0:
            self.length = len(self.data) - self.offset

    @property
    def end_sample(self) -> int:
        return self.start_sample + self.length

    @property
    def channels(self) -> int:
        return 1 if self.data.ndim == 1 else self.data.shape[1]

    def view(self) -> np.ndarray:
        """Gibt den effektiv hoerbaren Bereich des Clips zurueck."""
        return self.data[self.offset: self.offset + self.length]

    def split_at(self, timeline_sample: int) -> Optional["Clip"]:
        """Schneidet diesen Clip an der Timeline-Position. Gibt den rechten Teil zurueck."""
        local = timeline_sample - self.start_sample
        if local <= 0 or local >= self.length:
            return None
        right = Clip(
            data=self.data,
            start_sample=self.start_sample + local,
            name=self.name,
            gain=self.gain,
            offset=self.offset + local,
            length=self.length - local,
        )
        self.length = local
        self._peaks_cache = None
        return right

    def invalidate_peaks(self):
        self._peaks_cache = None


@dataclass
class Track:
    name: str
    clips: List[Clip] = field(default_factory=list)
    gain: float = 1.0     # 0..2 (entspricht ca. -inf..+6 dB grob)
    pan: float = 0.0      # -1..1
    mute: bool = False
    solo: bool = False
    armed: bool = False   # fuer Aufnahme scharf

    def add_clip(self, clip: Clip):
        self.clips.append(clip)

    def remove_clip(self, clip: Clip):
        if clip in self.clips:
            self.clips.remove(clip)

    def length_samples(self) -> int:
        return max((c.end_sample for c in self.clips), default=0)


@dataclass
class Project:
    sample_rate: int = 48000
    channels: int = 2
    tracks: List[Track] = field(default_factory=list)
    bpm: float = 90.0

    def add_track(self, name: Optional[str] = None) -> Track:
        if name is None:
            name = f"Track {len(self.tracks) + 1}"
        track = Track(name=name)
        self.tracks.append(track)
        return track

    def remove_track(self, track: Track):
        if track in self.tracks:
            self.tracks.remove(track)

    def length_samples(self) -> int:
        return max((t.length_samples() for t in self.tracks), default=0)

    def length_seconds(self) -> float:
        return self.length_samples() / self.sample_rate if self.sample_rate else 0.0

    def has_solo(self) -> bool:
        return any(t.solo for t in self.tracks)
