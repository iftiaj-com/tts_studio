"""
core/audio_io.py
─────────────────
MP3 and other non-WAV audio I/O through soundfile's bundled libsndfile.

pydub shells out to ffmpeg for anything but WAV. ffmpeg is not shipped with
the installer, and a PC without it on PATH lost MP3 export and custom
ambiance import silently. libsndfile (already bundled for soundfile) reads
and writes MP3, FLAC and OGG itself, so pydub is only used for WAV here.
"""

import numpy as np
import soundfile as sf
from pydub import AudioSegment

# Sample rates an MPEG layer III stream can carry.
_MP3_RATES = (8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000)


def load_segment(path: str) -> AudioSegment:
    """Decode any audio file libsndfile understands into a 16-bit AudioSegment."""
    if str(path).lower().endswith(".wav"):
        try:
            return AudioSegment.from_wav(path)
        except Exception:
            pass   # e.g. float WAV pydub can't parse; libsndfile can
    data, sr = sf.read(path, dtype="int16", always_2d=True)
    return AudioSegment(data=np.ascontiguousarray(data).tobytes(), sample_width=2,
                        frame_rate=sr, channels=data.shape[1])


def export_mp3(seg: AudioSegment, path: str) -> None:
    """Encode *seg* as constant-bitrate MP3 (about 192 kbps, or 160 below 32 kHz)."""
    if seg.frame_rate not in _MP3_RATES:
        seg = seg.set_frame_rate(44100)
    seg = seg.set_sample_width(2)
    samples = np.array(seg.get_array_of_samples(), dtype=np.int16)
    if seg.channels > 1:
        samples = samples.reshape(-1, seg.channels)
    # libsndfile maps the level linearly onto the stream's bitrate range:
    # 32-320 kbps for MPEG-1 rates, 8-160 kbps below 32 kHz.
    level = 0.45 if seg.frame_rate >= 32000 else 0.0
    sf.write(path, samples, seg.frame_rate, format="MP3", subtype="MPEG_LAYER_III",
             compression_level=level, bitrate_mode="CONSTANT")
