"""Voice endpoints (Section 17, 23) -- placeholders until v1.0."""
from fastapi import APIRouter, File, UploadFile

from david.voice import voice_engine

router = APIRouter(prefix="/api/voice", tags=["voice"])


@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    return await voice_engine.speech_to_text(audio_bytes, content_type=file.content_type)


@router.post("/tts")
async def text_to_speech(payload: dict):
    return await voice_engine.text_to_speech(text=payload.get("text", ""), voice=payload.get("voice", "default"))
