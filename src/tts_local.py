# src/tts_local.py

from pathlib import Path
from typing import List
import wave
import math
import struct

from .models import ScriptItem

def _tone_for(item: ScriptItem) -> int:
    """Map emotion/type to a tone frequency (simple placeholder)."""
    if item.type == "narration":
        return 440
    e = (item.emotion or "").lower()
    if "anger" in e:
        return 660
    if "sad" in e:
        return 330
    if "joy" in e or "happy" in e:
        return 550
    if "fear" in e:
        return 220
    return 440

def generate_placeholder_wav(path: Path, seconds: float, freq: int, sample_rate: int = 22050):
    """Generate a simple sine-wave wav file."""
    n_samples = int(sample_rate * seconds)
    amp = 0.2 

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2) 
        wf.setframerate(sample_rate)

        for i in range(n_samples):
            t = i / sample_rate
            val = amp * math.sin(2 * math.pi * freq * t)
            wf.writeframes(struct.pack("<h", int(val * 32767)))

def synthesize_items_to_clips(items: List[ScriptItem], out_dir: str = "output/clips") -> str:
    """
    Creates one WAV file per script item as a placeholder for real TTS.
    Returns the output folder.
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for it in items:
        freq = _tone_for(it)
        dur = min(2.0, max(0.6, len(it.text) / 40.0))
        fname = f"{it.idx:03d}_{it.type}.wav"
        generate_placeholder_wav(out_path / fname, seconds=dur, freq=freq)

    return str(out_path)
