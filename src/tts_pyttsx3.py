# src/tts_pyttsx3.py

from pathlib import Path
from typing import List
import pyttsx3

from .models import ScriptItem


def _pick_voice(engine, voice_id: str | None):
    """
    Best-effort voice selection.
    On Windows, available voices are limited; we map different voice_ids
    to different available system voices (if multiple exist).
    """
    voices = engine.getProperty("voices") or []
    if not voices:
        return

    # Create a stable index from voice_id
    if voice_id:
        idx = sum(ord(c) for c in voice_id) % len(voices)
    else:
        idx = 0

    engine.setProperty("voice", voices[idx].id)


def _apply_style(engine, item: ScriptItem):

    base_rate = 175
    engine.setProperty("volume", 1.0)

    if item.type == "narration":
        engine.setProperty("rate", base_rate)
        return

    e = (item.emotion or "").lower()
    if "anger" in e:
        engine.setProperty("rate", base_rate + 25)
    elif "sad" in e:
        engine.setProperty("rate", base_rate - 25)
    elif "joy" in e or "happy" in e:
        engine.setProperty("rate", base_rate + 10)
    elif "fear" in e:
        engine.setProperty("rate", base_rate - 10)
    else:
        engine.setProperty("rate", base_rate)


def synthesize_items_to_clips(items: List[ScriptItem], out_dir: str = "output/clips") -> str:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    engine = pyttsx3.init()

    for it in items:
        _pick_voice(engine, it.voice_id)
        _apply_style(engine, it)
        fname = f"{it.idx:03d}_{it.type}.wav"
        wav_path = out_path / fname
        engine.save_to_file(it.text, str(wav_path))

    engine.runAndWait()
    engine.stop()
    return str(out_path)
