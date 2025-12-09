from fastapi import APIRouter, HTTPException, UploadFile, File
from faster_whisper import WhisperModel
import tempfile
import os

from ..config import STT_MODEL_NAME, STT_DEVICE, STT_COMPUTE_TYPE

# APIRouter to group related endpoints
router = APIRouter(
    prefix="/stt",  # All routes in this file will start with /stt
    tags=["Speech-to-Text"]  # This is for the API docs
)

# Initialize the Whisper model (loaded once at startup)
# This model is shared with realtime.py to avoid loading duplicate models
print(f"🎤 Loading Whisper STT model: {STT_MODEL_NAME}")
whisper_model = WhisperModel(STT_MODEL_NAME, device=STT_DEVICE, compute_type=STT_COMPUTE_TYPE)
print(f"✅ Whisper STT model loaded!")


async def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """Transcribes audio bytes using Whisper and returns the text."""
    # Write audio bytes to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_bytes)
        tmp_path = tmp_file.name

    try:
        # Transcribe the audio
        segments, info = whisper_model.transcribe(tmp_path, beam_size=5)
        
        # Combine all segments into a single transcript
        transcript = " ".join([segment.text for segment in segments])
        return transcript.strip()
    finally:
        # Clean up the temporary file
        os.unlink(tmp_path)


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """API endpoint that accepts an audio file and returns the transcription."""
    try:
        # Read the uploaded file
        audio_bytes = await file.read()
        
        # Transcribe the audio
        transcript = await transcribe_audio_bytes(audio_bytes)
        
        return {"transcription": transcript}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
