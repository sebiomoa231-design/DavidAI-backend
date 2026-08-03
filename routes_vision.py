"""Vision endpoints (Section 18, 23) -- placeholders until v1.1+."""
from fastapi import APIRouter, File, Form, UploadFile

from david.vision import vision_engine

router = APIRouter(prefix="/api/vision", tags=["vision"])


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), prompt: str = Form("")):
    image_bytes = await file.read()
    return await vision_engine.analyze_image(image_bytes, content_type=file.content_type, prompt=prompt)
