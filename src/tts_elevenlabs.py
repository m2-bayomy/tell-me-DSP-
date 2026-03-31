import os
import re
from pathlib import Path
from typing import List, Optional

from elevenlabs.client import ElevenLabs

from .models import ScriptItem

_CLIENT: Optional[ElevenLabs] = None

# Keep verb list aligned with dialogue_parser.py
_VERBS = r"said|asked|shouted|whispered|replied|cried|yelled|muttered"

# Conservative patterns to remove common dialogue tags from narration
# we do not modify ScriptItem.text; only the text sent to TTS is cleaned.
_TAG_PATTERNS = [
    re.compile(rf"\b[A-Z][a-z]+\s+(?i:{_VERBS})\s*,\s*$"),
    re.compile(rf"\b[A-Z][a-z]+\s+(?i:{_VERBS})\s*\.\s*$"),
    re.compile(rf"\b[A-Z][a-z]+\s+(?i:{_VERBS})\s*$"),
    re.compile(rf"\s*,\s*[A-Z][a-z]+\s+(?i:{_VERBS})\s*,\s*"),
    re.compile(rf"\s*,\s*[A-Z][a-z]+\s+(?i:{_VERBS})\s*\.\s*"),
]


def _get_client() -> ElevenLabs:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError(
            "ELEVENLABS_API_KEY not found. Set it as an environment variable and restart VS Code."
        )

    _CLIENT = ElevenLabs(api_key=api_key)
    return _CLIENT


def _emotion_to_voice_settings(emotion: Optional[str]) -> dict:
    e = (emotion or "").lower()

    stability = 0.45
    similarity_boost = 0.80
    style = 0.30
    use_speaker_boost = True

    if "anger" in e:
        stability = 0.35
        style = 0.55
    elif "sad" in e:
        stability = 0.60
        style = 0.20
    elif "joy" in e or "happy" in e:
        stability = 0.40
        style = 0.50
    elif "fear" in e:
        stability = 0.55
        style = 0.35

    return {
        "stability": stability,
        "similarity_boost": similarity_boost,
        "style": style,
        "use_speaker_boost": use_speaker_boost,
    }


def _clean_narration_for_tts(text: str) -> str:

    t = " ".join(text.split())  # normalize whitespace
    for pat in _TAG_PATTERNS:
        t = pat.sub(" ", t)
    t = " ".join(t.split()).strip(" ,.")
    return t


def synthesize_items_to_clips(
    items: List[ScriptItem],
    out_dir: str = "output/clips",
    model_id: str = "eleven_multilingual_v2",
    skip_empty_narration: bool = True,
) -> str:

    client = _get_client()

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for it in items:
        settings = (
            _emotion_to_voice_settings(it.emotion)
            if it.type == "dialogue"
            else _emotion_to_voice_settings(None)
        )

        voice_id = it.voice_id or "21m00Tcm4TlvDq8ikWAM"

        #TTS-time narration cleanup
        tts_text = it.text
        if it.type == "narration":
            tts_text = _clean_narration_for_tts(it.text)
            if skip_empty_narration and not tts_text:
                # If narration becomes empty after cleanup, skip generating this clip.
                # The stitcher will simply not include it.
                continue

        audio_stream = client.text_to_speech.convert(
            voice_id=voice_id,
            model_id=model_id,
            text=tts_text,
            voice_settings=settings,
        )

        audio_bytes = b"".join(audio_stream)

        fname = f"{it.idx:03d}_{it.type}.mp3"
        with open(out_path / fname, "wb") as f:
            f.write(audio_bytes)

    return str(out_path)