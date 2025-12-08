from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from piper import PiperVoice
import io
import wave
import os
from fastapi.responses import Response

# APIRouter to group related endpoints
router = APIRouter(
    prefix="/tts",  # All routes in this file will start with /tts
    tags=["Text-to-Speech"]  # This is for the API docs
)

# Path to Piper model
MODEL_PATH = os.environ.get(
    "PIPER_MODEL_PATH",
    os.path.join(os.path.dirname(__file__), "../../models/piper/en_US-amy-medium.onnx")
)

# Load Piper voice model once at startup
print(f"🔊 Loading Piper TTS model from: {MODEL_PATH}")
_voice = PiperVoice.load(MODEL_PATH)
print(f"✅ Piper TTS loaded! Sample rate: {_voice.config.sample_rate}")


# Request body schema
class TTSRequest(BaseModel):
    text: str


async def get_tts_audio_bytes(request: TTSRequest) -> bytes:
    """Generates TTS audio using Piper and returns WAV bytes."""
    try:
        # Synthesize speech
        chunks = list(_voice.synthesize(request.text))
        
        if not chunks:
            raise ValueError("No audio generated")
        
        # Get audio properties
        sample_rate = chunks[0].sample_rate
        sample_width = chunks[0].sample_width
        channels = chunks[0].sample_channels
        
        # Combine all audio bytes
        all_audio_bytes = b''.join(chunk.audio_int16_bytes for chunk in chunks)
        
        # Write to WAV format
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(all_audio_bytes)
        
        return wav_buffer.getvalue()
        
    except Exception as e:
        raise e


@router.post("/generate-audio")
async def generate_audio(request: TTSRequest):
    """API endpoint that returns TTS audio as WAV."""
    try:
        audio_bytes = await get_tts_audio_bytes(request)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
