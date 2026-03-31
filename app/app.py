# app/app.py

import sys
import os
import json
from pathlib import Path
from datetime import datetime

import streamlit as st

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.dialogue_parser import parse_script  # noqa: E402
from src.emotion_detector import annotate_emotions  # noqa: E402
from src.voice_assigner import (  # noqa: E402
    load_voice_mapping,
    assign_voices,
    merge_character_mapping,
)
from src.voice_registry import (  # noqa: E402
    load_free_voices,
    load_registry,
    save_registry,
    ensure_voices_for_speakers,
    load_name_gender_overrides,
)
from src.tts_elevenlabs import synthesize_items_to_clips  # noqa: E402
from src.audio_stitcher import stitch_audio  # noqa: E402
from src.speaker_memory import apply_speaker_memory  # noqa: E402



def make_run_dir() -> Path:
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = Path("output") / "runs" / ts
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "clips").mkdir(parents=True, exist_ok=True)
    return run_dir


# aage setup
st.set_page_config(page_title="Tell Me (Ehkeely)", layout="centered")
st.title("Tell Me (Ehkeely) – Prototype")
st.write(
    "Paste a story below. This prototype generates a structured script (narration + dialogue), "
    "annotates emotions, assigns voices, then generates an audiobook using ElevenLabs."
)

# session state
st.session_state.setdefault("items", None)
st.session_state.setdefault("script_json", None)
st.session_state.setdefault("final_audio_path", None)
st.session_state.setdefault("run_dir", None)
st.session_state.setdefault("voice_mapping_used", None)

# Input example
default_example = (
    'Ali looked at Sara and shouted, "You stole my toy!"\n'
    '"I\'m sorry, Ali," Sara said sadly.\n'
    "The room fell silent."
)

story_text = st.text_area(
    "Story text",
    height=240,
    placeholder=default_example,
)

# Actions
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    parse_clicked = st.button("Generate Script (Parse)")

with col2:
    audio_clicked = st.button("Generate Audio (ElevenLabs)")

with col3:
    clear_clicked = st.button("Clear")

if clear_clicked:
    st.session_state["items"] = None
    st.session_state["script_json"] = None
    st.session_state["final_audio_path"] = None
    st.session_state["run_dir"] = None
    st.session_state["voice_mapping_used"] = None
    st.experimental_rerun()

#parse + annotate + voice assign
if parse_clicked:
    if not story_text.strip():
        st.warning("Please paste some story text first.")
    else:
        try:
            # parse narration/dialogue
            items = parse_script(story_text)

            # fill missing speakers using speaker memory heuristic
            items = apply_speaker_memory(items)

            # annotate emotions
            items = annotate_emotions(items)

            #load base mapping
            base_mapping = load_voice_mapping("data/voice_mapping.json")

            #load free voice
            free_voices = load_free_voices("data/free_voices.json")

            #load persistent registry + gender overrides and allocate missing speaker voices
            registry = load_registry("data/voice_registry.json")
            overrides = load_name_gender_overrides("data/name_gender_overrides.json")

            reserved = {base_mapping.get("default_narrator"), base_mapping.get("fallback_voice")}
            registry = ensure_voices_for_speakers(
                items=items,
                registry=registry,
                free_voices=free_voices,
                reserved_voice_ids=reserved,
                name_gender_overrides=overrides,
            )

            # persist registry globally 
            save_registry("data/voice_registry.json", registry)

            #Merge registry characters into mapping used for this run
            mapping = merge_character_mapping(base_mapping, registry)

            #assign voices to each ScriptItem
            items = assign_voices(items, mapping)

            # Serialize structured script
            data = [item.to_dict() for item in items]
            script_json = json.dumps(data, indent=4, ensure_ascii=False)

            # Create a new run folder
            run_dir = make_run_dir()
            (run_dir / "script.json").write_text(script_json, encoding="utf-8")

            (run_dir / "voice_mapping_used.json").write_text(
                json.dumps(mapping, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            (run_dir / "voice_registry_snapshot.json").write_text(
                json.dumps(registry, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            st.session_state["items"] = items
            st.session_state["script_json"] = script_json
            st.session_state["final_audio_path"] = None
            st.session_state["run_dir"] = str(run_dir)
            st.session_state["voice_mapping_used"] = mapping

            st.success(f"Script generated. Saved to: {run_dir}")

        except Exception as e:
            st.error(f"Failed to generate script: {e}")

#show script output
if st.session_state["script_json"]:
    st.subheader("Structured Output (Script)")
    st.json(json.loads(st.session_state["script_json"]))

    st.download_button(
        label="Download script.json",
        data=st.session_state["script_json"],
        file_name="script.json",
        mime="application/json",
    )

    if st.session_state.get("voice_mapping_used"):
        st.subheader("Voice Mapping Used (Auto)")
        st.json(st.session_state["voice_mapping_used"])

# audio generation (ElevenLabs)
if audio_clicked:
    if st.session_state["items"] is None or st.session_state["run_dir"] is None:
        st.warning("Please click 'Generate Script (Parse)' first.")
    else:
        if not os.getenv("ELEVENLABS_API_KEY"):
            st.error("ELEVENLABS_API_KEY is not set. Set it as an environment variable and restart VS Code.")
        else:
            try:
                run_dir = Path(st.session_state["run_dir"])
                clips_dir = run_dir / "clips"
                final_mp3 = run_dir / "audiobook.mp3"

                with st.spinner("Generating speech clips with ElevenLabs..."):
                    synthesize_items_to_clips(
                        st.session_state["items"],
                        out_dir=str(clips_dir),
                        model_id="eleven_multilingual_v2",
                    )

                with st.spinner("Stitching clips into one audiobook with pauses..."):
                    final_audio = stitch_audio(
                        clips_dir=str(clips_dir),
                        output_file=str(final_mp3),
                        pause_ms=550,
                        pause_switch_ms=1000,
                    )

                st.session_state["final_audio_path"] = final_audio
                st.success(f"Audiobook generated. Saved to: {final_mp3}")

            except Exception as e:
                st.error(f"Audio generation failed: {e}")

# Show audio
if st.session_state["final_audio_path"]:
    st.subheader("Audio Output (Audiobook)")
    st.write(f"Run folder: `{st.session_state['run_dir']}`")
    st.write(f"Final audiobook: `{st.session_state['final_audio_path']}`")

    try:
        with open(st.session_state["final_audio_path"], "rb") as f:
            audio_bytes = f.read()

        st.audio(audio_bytes, format="audio/mp3")

        st.download_button(
            label="Download audiobook.mp3",
            data=audio_bytes,
            file_name="audiobook.mp3",
            mime="audio/mpeg",
        )
    except Exception as e:
        st.error(f"Could not load audio file: {e}")