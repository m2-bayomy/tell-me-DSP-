import os
from elevenlabs.client import ElevenLabs

api_key = os.getenv("ELEVENLABS_API_KEY")

if not api_key:
    raise ValueError("ELEVENLABS_API_KEY not found. Restart VS Code.")

client = ElevenLabs(api_key=api_key)

# Generate speech (returns a generator/stream)
audio_stream = client.text_to_speech.convert(
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel public voice
    model_id="eleven_multilingual_v2",
    text="Hello, this is a test from Tell Me project."
)

# Collect chunks into bytes
audio_bytes = b"".join(audio_stream)

# Save file
with open("test_output.wav", "wb") as f:
    f.write(audio_bytes)

print("Audio saved as test_output.wav")
