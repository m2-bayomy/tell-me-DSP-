# src/models.py


from dataclasses import dataclass, asdict
from typing import Optional, Literal, Dict, Any

ItemType = Literal["dialogue", "narration"]

@dataclass
class ScriptItem:
    idx: int
    type: ItemType
    text: str
    speaker: Optional[str] = None
    emotion: Optional[str] = None
    voice_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
