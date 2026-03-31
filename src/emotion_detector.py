from typing import List, Optional
from .models import ScriptItem

try:
    from transformers import pipeline  # type: ignore
    _HAS_TRANSFORMERS = True
except Exception:
    _HAS_TRANSFORMERS = False

_EMOTION_PIPE = None


def _get_emotion_pipeline():
    global _EMOTION_PIPE
    if _EMOTION_PIPE is not None:
        return _EMOTION_PIPE

    if not _HAS_TRANSFORMERS:
        return None

    _EMOTION_PIPE = pipeline(
        task="text-classification",
        model="j-hartmann/emotion-english-distilroberta-base",
        top_k=1,
    )
    return _EMOTION_PIPE


def _heuristic_emotion(text: str) -> str:
    t = text.lower()
    if any(w in t for w in ["sorry", "sad", "cry", "miss", "lonely", "hurt"]):
        return "sadness"
    if any(w in t for w in ["angry", "hate", "stole", "mad", "shout", "furious"]):
        return "anger"
    if any(w in t for w in ["wow", "yay", "happy", "great", "love", "amazing", "relief", "great"]):
        return "joy"
    if any(w in t for w in ["scared", "afraid", "fear", "monster", "terrified", "panic", "nervous"]):
        return "fear"
    return "neutral"


def _extract_label(out) -> str:
    if isinstance(out, list) and out:
        first = out[0]
        if isinstance(first, list) and first:
            first = first[0]
        if isinstance(first, dict):
            return str(first.get("label", "neutral")).lower()
    return "neutral"


def detect_emotion(text: str) -> str:
    pipe = _get_emotion_pipeline()
    if pipe is None:
        return _heuristic_emotion(text)

    try:
        out = pipe(text)
        return _extract_label(out)
    except Exception:
        return _heuristic_emotion(text)


def _build_context(items: List[ScriptItem], i: int) -> str:

    parts: List[str] = []

    if i - 1 >= 0:
        prev = items[i - 1].text.strip()
        if prev:
            parts.append(prev)

    cur = items[i].text.strip()
    if cur:
        parts.append(cur)

    if i + 1 < len(items):
        nxt = items[i + 1].text.strip()
        #keep next short to avoid leaking too much future content
        if nxt:
            parts.append(nxt)

    return " ".join(parts)


def annotate_emotions(items: List[ScriptItem]) -> List[ScriptItem]:

    # Identify dialogue indices
    dlg_indices = [i for i, it in enumerate(items) if it.type == "dialogue"]

    if not dlg_indices:
        return items

    pipe = _get_emotion_pipeline()
    if pipe is None:
        for i in dlg_indices:
            items[i].emotion = _heuristic_emotion(_build_context(items, i))
        return items

    #batch inference
    texts = [_build_context(items, i) for i in dlg_indices]

    try:
        outs = pipe(texts)
        # outs should align with texts length
        for idx, out in zip(dlg_indices, outs):
            items[idx].emotion = _extract_label(out)
    except Exception:
        for i in dlg_indices:
            items[i].emotion = _heuristic_emotion(_build_context(items, i))

    return items