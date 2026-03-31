import json
import hashlib
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional

from .models import ScriptItem


def load_free_voices(path: str) -> List[Dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    voices = data.get("voices", [])
    if not isinstance(voices, list) or not voices:
        raise ValueError(f"No voices found in {path}")
    # normalize fields
    out = []
    for v in voices:
        if not isinstance(v, dict) or "id" not in v:
            continue
        out.append(
            {
                "id": str(v["id"]),
                "name": str(v.get("name", "")),
                "gender": str(v.get("gender", "neutral")).lower(),
            }
        )
    if not out:
        raise ValueError(f"No valid voice entries found in {path}")
    return out


def load_free_voice_ids(path: str) -> List[str]:
    voices = load_free_voices(path)
    return [v["id"] for v in voices]


def load_registry(path: str) -> Dict:
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"characters": {}}, indent=2), encoding="utf-8")
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("characters", {})
    return data


def save_registry(path: str, registry: Dict) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")


def load_name_gender_overrides(path: str) -> Dict[str, str]:
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    # normalize to lower tokens
    out: Dict[str, str] = {}
    for k, v in data.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        vv = v.strip().lower()
        if vv in {"male", "female", "neutral"}:
            out[k.strip()] = vv
    return out


def canonicalize_speaker_name(name: str) -> str:
    """
    Keep it simple and stable. Your parser produces capitalized names already.
    This avoids 'ALI' and 'Ali' becoming different registry keys.
    """
    n = " ".join(name.strip().split())
    return " ".join(part[:1].upper() + part[1:].lower() for part in n.split(" ") if part)


def _stable_candidate_index(key: str, pool_size: int) -> int:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % pool_size


def _build_gender_pools(
    free_voices: List[Dict],
    reserved_voice_ids: Set[str],
) -> Tuple[List[str], List[str], List[str]]:
    male = []
    female = []
    neutral = []
    for v in free_voices:
        vid = v["id"]
        if vid in reserved_voice_ids:
            continue
        g = v.get("gender", "neutral")
        if g == "female":
            female.append(vid)
        elif g == "male":
            male.append(vid)
        else:
            neutral.append(vid)
    return male, female, neutral


def _infer_gender(name: str, overrides: Dict[str, str]) -> str:

    if name in overrides:
        return overrides[name]

    lower = name.lower()
    if lower.endswith(("a", "ah", "ia", "ina", "aya", "ette")):
        return "female"
    return "neutral"


def ensure_voices_for_speakers(
    items: List[ScriptItem],
    registry: Dict,
    free_voice_ids: Optional[List[str]] = None,  # backward compatibility
    reserved_voice_ids: Optional[Set[str]] = None,
    free_voices: Optional[List[Dict]] = None,
    name_gender_overrides: Optional[Dict[str, str]] = None,
) -> Dict:

    reserved_voice_ids = reserved_voice_ids or set()
    name_gender_overrides = name_gender_overrides or {}

    if free_voices is None:
        # If caller still passes free_voice_ids, treat as neutral pool
        if free_voice_ids is None:
            raise ValueError("Must provide free_voices or free_voice_ids")
        free_voices = [{"id": vid, "name": "", "gender": "neutral"} for vid in free_voice_ids]

    char_map: Dict[str, str] = registry.setdefault("characters", {})

    #Build pools
    male_pool, female_pool, neutral_pool = _build_gender_pools(free_voices, reserved_voice_ids)

    # get speakers from script
    speakers = sorted(
        {canonicalize_speaker_name(it.speaker) for it in items if it.type == "dialogue" and it.speaker}
    )

    used = set(char_map.values())

    for speaker in speakers:
        if speaker in char_map:
            continue

        gender = _infer_gender(speaker, name_gender_overrides)

        #choose pool based on gender fallback to neutral then to any available
        if gender == "female" and female_pool:
            pool = female_pool
        elif gender == "male" and male_pool:
            pool = male_pool
        elif neutral_pool:
            pool = neutral_pool
        else:
            pool = [*female_pool, *male_pool, *neutral_pool]

        if not pool:
            raise ValueError("No available free voices after applying reserved voice constraints.")

        start = _stable_candidate_index(speaker.strip().lower(), len(pool))

        chosen = None
        for offset in range(len(pool)):
            candidate = pool[(start + offset) % len(pool)]
            if candidate not in used:
                chosen = candidate
                break

        if chosen is None:
            # all used, deterministically reuse
            chosen = pool[start]

        char_map[speaker] = chosen
        used.add(chosen)

    registry["characters"] = char_map
    return registry