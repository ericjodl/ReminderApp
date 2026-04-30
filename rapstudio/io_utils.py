"""Audio-Datei-Import und -Export."""
from __future__ import annotations

import io
import os
import sys
from typing import Tuple

import numpy as np
import soundfile as sf


def _configure_pydub_ffmpeg():
    """Wenn als PyInstaller-EXE laufend, pydub auf das mitgelieferte ffmpeg.exe zeigen."""
    try:
        from pydub import AudioSegment
    except ImportError:
        return
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(sys.argv[0]))
    candidate = os.path.join(base, "ffmpeg.exe")
    if os.path.isfile(candidate):
        AudioSegment.converter = candidate
        AudioSegment.ffmpeg = candidate
        # ffprobe kann fehlen; pydub faellt dann auf ffmpeg-only zurueck
        probe = os.path.join(base, "ffprobe.exe")
        if os.path.isfile(probe):
            AudioSegment.ffprobe = probe


_configure_pydub_ffmpeg()


def load_audio(path: str, target_sr: int) -> Tuple[np.ndarray, int]:
    """Laedt eine Audiodatei und gibt (data float32, sample_rate) zurueck.

    Versucht zuerst libsndfile (WAV/FLAC/OGG/neuere MP3-Builds), faellt sonst
    auf pydub zurueck (MP3/AAC/M4A, benoetigt ffmpeg im PATH).
    """
    ext = os.path.splitext(path)[1].lower()
    data: np.ndarray
    sr: int
    try:
        data, sr = sf.read(path, dtype="float32", always_2d=False)
    except Exception:
        if ext in (".mp3", ".m4a", ".aac", ".wma", ".ogg", ".opus"):
            data, sr = _load_with_pydub(path)
        else:
            raise

    # Resampling falls noetig (einfach, qualitativ ausreichend fuer DAW-Zwecke)
    if sr != target_sr:
        data = _resample_linear(data, sr, target_sr)
        sr = target_sr
    return data.astype(np.float32, copy=False), sr


def _load_with_pydub(path: str) -> Tuple[np.ndarray, int]:
    try:
        from pydub import AudioSegment
    except ImportError as e:
        raise RuntimeError(
            "Zum Import von MP3/AAC wird pydub (und ffmpeg im PATH) benoetigt."
        ) from e
    seg = AudioSegment.from_file(path)
    sr = seg.frame_rate
    samples = np.array(seg.get_array_of_samples())
    if seg.channels > 1:
        samples = samples.reshape((-1, seg.channels))
    # Normalisieren in float32 [-1, 1]
    max_val = float(1 << (8 * seg.sample_width - 1))
    data = samples.astype(np.float32) / max_val
    return data, sr


def _resample_linear(data: np.ndarray, sr_in: int, sr_out: int) -> np.ndarray:
    if sr_in == sr_out:
        return data
    ratio = sr_out / sr_in
    if data.ndim == 1:
        n_out = int(round(len(data) * ratio))
        x_in = np.arange(len(data), dtype=np.float64)
        x_out = np.linspace(0, len(data) - 1, n_out, dtype=np.float64)
        return np.interp(x_out, x_in, data).astype(np.float32)
    else:
        n_out = int(round(data.shape[0] * ratio))
        x_in = np.arange(data.shape[0], dtype=np.float64)
        x_out = np.linspace(0, data.shape[0] - 1, n_out, dtype=np.float64)
        out = np.empty((n_out, data.shape[1]), dtype=np.float32)
        for ch in range(data.shape[1]):
            out[:, ch] = np.interp(x_out, x_in, data[:, ch]).astype(np.float32)
        return out


def export_wav(path: str, data: np.ndarray, sr: int):
    sf.write(path, data, sr, subtype="PCM_16")


def export_mp3(path: str, data: np.ndarray, sr: int, bitrate: str = "192k"):
    """Exportiert MP3 via pydub/ffmpeg. ffmpeg muss installiert sein."""
    try:
        from pydub import AudioSegment
    except ImportError as e:
        raise RuntimeError(
            "Zum MP3-Export wird pydub (und ffmpeg im PATH) benoetigt."
        ) from e

    if data.ndim == 1:
        channels = 1
        interleaved = data
    else:
        channels = data.shape[1]
        interleaved = data.reshape(-1)

    int16 = np.clip(interleaved, -1.0, 1.0)
    int16 = (int16 * 32767.0).astype(np.int16)
    seg = AudioSegment(
        int16.tobytes(),
        frame_rate=sr,
        sample_width=2,
        channels=channels,
    )
    seg.export(path, format="mp3", bitrate=bitrate)
