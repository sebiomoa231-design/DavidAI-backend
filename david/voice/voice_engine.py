"""
Voice engine placeholders (Section 17, v1.0).

Speech-to-text and text-to-speech are not implemented yet -- these stubs
define the stable interface so the API layer and dashboard can be built
against it now, and wired to a real STT/TTS provider later (e.g. Whisper,
ElevenLabs, or a browser-side Web Speech API) without changing callers.
"""
from david.utils.logger import get_logger

logger = get_logger("david.voice")


async def speech_to_text(audio_bytes: bytes, content_type: str = "audio/wav") -> dict:
    logger.info("speech_to_text called (not yet implemented)")
    return {"success": False, "text": "", "error": "Speech-to-text is not implemented yet (planned for v1.0)."}


async def text_to_speech(text: str, voice: str = "default") -> dict:
    logger.info("text_to_speech called (not yet implemented)")
    return {"success": False, "audio_url": None, "error": "Text-to-speech is not implemented yet (planned for v1.0)."}
