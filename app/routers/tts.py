from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from gtts import gTTS
import io
from fastapi.responses import Response

# APIRouter to group related endpoints
router = APIRouter(
    prefix="/tts",  # All routes in this file will start with /tts
    tags=["Text-to-Speech"] # This is for the API docs
)

# request body schema
class TTSRequest(BaseModel):
    text: str
    lang: str = "en"

async def get_tts_audio_bytes(request: TTSRequest) -> bytes:
    """Generates TTS audio and returns the raw bytes."""
    try:
        tts = gTTS(text=request.text, lang=request.lang)
        mp3_fp = io.BytesIO()
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        return mp3_fp.read()
    except Exception as e:
        raise e

@router.post("/generate-audio")
async def generate_audio(request: TTSRequest):
    """API endpoint that returns TTS audio as a streaming response."""
    try:
        audio_bytes = await get_tts_audio_bytes(request)
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
