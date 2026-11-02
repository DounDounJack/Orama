"""Local speech-to-text needs faster-whisper and PyAV to agree.

PyAV 19 removed the ``metadata_errors`` argument that faster-whisper 1.2
passes to ``av.open``, so every local transcription failed with a TypeError
(requirements.txt now pins ``av<19``). Decoding a tiny clip exercises exactly
that call without downloading a Whisper model.
"""
import math
import struct
import wave

import pytest


def test_faster_whisper_can_decode_audio(tmp_path):
    audio = pytest.importorskip("faster_whisper.audio")
    clip = tmp_path / "beep.wav"
    with wave.open(str(clip), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"".join(struct.pack("<h", int(4000 * math.sin(i / 6))) for i in range(8000)))
    samples = audio.decode_audio(str(clip))
    assert len(samples) == pytest.approx(8000, abs=200)
