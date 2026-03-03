import os
import asyncio
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
    DeepgramClientOptions,
)


def get_deepgram_client() -> DeepgramClient:
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY not set in environment")
    return DeepgramClient(api_key)


async def create_live_connection(on_transcript, on_error=None):
    """
    Create a Deepgram live transcription connection (SDK v6).
    on_transcript: async callable(transcript: str, is_final: bool)
    on_error: optional async callable(error: str)
    Returns the live connection object.
    """
    client = get_deepgram_client()
    connection = client.listen.asyncwebsocket.v("1")

    async def _on_message(self, result, **kwargs):
        try:
            sentence = result.channel.alternatives[0].transcript
            is_final = result.is_final
            if sentence:
                await on_transcript(sentence, is_final)
        except Exception:
            pass

    async def _on_error(self, error, **kwargs):
        if on_error:
            await on_error(str(error))

    connection.on(LiveTranscriptionEvents.Transcript, _on_message)
    connection.on(LiveTranscriptionEvents.Error, _on_error)

    options = LiveOptions(
        model="nova-3",
        language="en-US",
        smart_format=True,
        interim_results=True,
        endpointing=500,
    )

    await connection.start(options)
    return connection


async def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """
    One-shot transcription of raw audio bytes (SDK v6).
    Returns the combined final transcript string.
    """
    client = get_deepgram_client()
    result = await asyncio.to_thread(
        client.listen.rest.v("1").transcribe_file,
        {"buffer": audio_bytes, "mimetype": "audio/webm"},
        LiveOptions(
            model="nova-3",
            smart_format=True,
            language="en-US",
        ),
    )
    try:
        return result.results.channels[0].alternatives[0].transcript
    except Exception:
        return ""
