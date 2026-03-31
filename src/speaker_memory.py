# src/speaker_memory.py

from typing import List, Optional
from .models import ScriptItem


def apply_speaker_memory(items: List[ScriptItem]) -> List[ScriptItem]:
    last_speaker: Optional[str] = None

    for it in items:
        if it.type == "dialogue":
            if it.speaker:
                last_speaker = it.speaker
            else:
                if last_speaker:
                    it.speaker = last_speaker

    return items