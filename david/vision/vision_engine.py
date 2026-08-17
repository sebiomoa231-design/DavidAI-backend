"""
Vision engine placeholders (Section 18, v1.1+).

Image analysis / OCR are not implemented yet. Stubbed with a stable
interface so uploads can be routed here once a vision-capable provider
(e.g. Gemini vision, or a dedicated OCR service) is wired in.
"""
from david.utils.logger import get_logger

logger = get_logger("david.vision")


async def analyze_image(image_bytes: bytes, content_type: str = "image/png", prompt: str = "") -> dict:
    logger.info("analyze_image called (not yet implemented)")
    return {
        "success": False,
        "description": "",
        "error": "Vision analysis is not implemented yet (planned for v1.1+). "
                 "Wire this up to a vision-capable provider (e.g. Gemini) when ready.",
    }
