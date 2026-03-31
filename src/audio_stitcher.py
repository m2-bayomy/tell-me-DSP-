# src/audio_stitcher.py

from pathlib import Path
from pydub import AudioSegment

def _kind_from_filename(path: Path) -> str:

    name = path.stem.lower()
    if "_dialogue" in name:
        return "dialogue"
    if "_narration" in name:
        return "narration"
    return "unknown"

def stitch_audio(
    clips_dir: str,
    output_file: str,
    pause_ms: int = 300,
    pause_switch_ms: int = 700,
) -> str:

    clips_path = Path(clips_dir)
    out_path = Path(output_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    files = sorted(list(clips_path.glob("*.mp3")))
    if not files:
        raise FileNotFoundError(f"No .mp3 clips found in {clips_dir}")

    combined = AudioSegment.empty()
    prev_kind = None

    for f in files:
        kind = _kind_from_filename(f)

        #add pause BEFORE this segment
        if prev_kind is not None:
            if kind != prev_kind:
                combined += AudioSegment.silent(duration=pause_switch_ms)
            else:
                combined += AudioSegment.silent(duration=pause_ms)

        seg = AudioSegment.from_file(f)
        combined += seg
        prev_kind = kind

    #Export as mp3
    combined.export(out_path, format="mp3")
    return str(out_path)
