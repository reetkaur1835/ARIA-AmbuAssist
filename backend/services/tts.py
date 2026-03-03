import os
import base64
import httpx


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel
MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")

ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"


async def text_to_speech(text: str) -> bytes:
    """
    Convert text to speech using ElevenLabs.
    Returns raw MP3 bytes.
    """
    url = f"{ELEVENLABS_BASE_URL}/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.content


async def text_to_speech_base64(text: str) -> str:
    """
    Convert text to speech and return base64-encoded MP3 string.
    Safe to embed directly in JSON API response.
    """
    mp3_bytes = await text_to_speech(text)
    return base64.b64encode(mp3_bytes).decode("utf-8")
