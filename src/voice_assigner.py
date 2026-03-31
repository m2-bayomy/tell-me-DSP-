import json
from typing import Dict, List
from pathlib import Path

from .models import ScriptItem


def load_voice_mapping(path: str) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_voice_mapping(path: str, mapping: Dict) -> None:
    Path(path).write_text(json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8")


def merge_character_mapping(base_mapping: Dict, registry: Dict) -> Dict:

    base_mapping = dict(base_mapping)
    base_chars = dict(base_mapping.get("characters", {}))
    reg_chars = dict(registry.get("characters", {}))

    # Only fill missing
    for name, vid in reg_chars.items():
        base_chars.setdefault(name, vid)

    base_mapping["characters"] = base_chars
    return base_mapping


def assign_voices(items: List[ScriptItem], mapping: Dict) -> List[ScriptItem]:
    default_narrator = mapping.get("default_narrator")
    fallback_voice = mapping.get("fallback_voice")
    char_map = mapping.get("characters", {})

    if not default_narrator or not fallback_voice:
        raise ValueError("voice_mapping.json must define default_narrator and fallback_voice")

    for it in items:
        if it.type == "narration":
            it.voice_id = default_narrator
        else:
            if it.speaker and it.speaker in char_map:
                it.voice_id = char_map[it.speaker]
            else:
                it.voice_id = fallback_voice

    return items