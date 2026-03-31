# src/dialogue_parser.py

import re
from typing import List, Optional
from .models import ScriptItem

#verbs can be case-insensitive but names must be capitalized.
VERBS = r"said|asked|shouted|whispered|replied|cried|yelled|muttered"

#After-quote pattern
AFTER_QUOTE = re.compile(
    rf'^\s*,?\s*(?P<name>[A-Z][a-z]+)\s+(?P<verb>(?i:{VERBS}))\b'
)

#before-quote pattern
BEFORE_QUOTE = re.compile(
    rf'(?P<name>[A-Z][a-z]+)\s+(?P<verb>(?i:{VERBS}))\s*,?\s*$'
)

SENTENCE_START_NAME = re.compile(r'^\s*(?P<name>[A-Z][a-z]+)\b')


def _infer_speaker(text: str, quote_start: int, quote_end: int) -> Optional[str]:

    #After-quote
    after_window = text[quote_end: quote_end + 120]
    m_after = AFTER_QUOTE.search(after_window)
    if m_after:
        return m_after.group("name")

    #Before-quote
    before_window = text[max(0, quote_start - 120): quote_start]

    before_trim = before_window.strip()

    last_boundary = max(
        before_trim.rfind("."),
        before_trim.rfind("!"),
        before_trim.rfind("?"),
        before_trim.rfind("\n"),
    )
    clause = before_trim[last_boundary + 1:].strip()

    m_before = BEFORE_QUOTE.search(clause)
    if m_before:
        return m_before.group("name")

    #sentence-start fallback
    # if clause starts with a capitalized name, use it.
    m_start = SENTENCE_START_NAME.search(clause)
    if m_start:
        return m_start.group("name")

    return None


def parse_script(text: str) -> List[ScriptItem]:

    items: List[ScriptItem] = []
    idx = 0
    cursor = 0

    # Find dialogue in quotes using positions
    for m in re.finditer(r'"(.*?)"', text, flags=re.DOTALL):
        q_start, q_end = m.span()
        spoken = m.group(1).strip()

        #Narration before this quote
        narration = text[cursor:q_start].strip()
        if narration:
            narration = re.sub(r"\s+", " ", narration)
            items.append(ScriptItem(idx=idx, type="narration", text=narration))
            idx += 1

        #Dialogue item
        if spoken:
            speaker = _infer_speaker(text, q_start, q_end)
            items.append(ScriptItem(idx=idx, type="dialogue", text=spoken, speaker=speaker))
            idx += 1

        cursor = q_end

    # Trailing narration after last quote
    tail = text[cursor:].strip()
    if tail:
        tail = re.sub(r"\s+", " ", tail)
        items.append(ScriptItem(idx=idx, type="narration", text=tail))
        idx += 1

    return items
