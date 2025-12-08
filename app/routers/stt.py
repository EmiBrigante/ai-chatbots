from fastapi import APIRouter, HTTPException, UploadFile, File
from faster_whisper import WhisperModel
import tempfile
import os

# APIRouter to group related endpoints
router = APIRouter(
    prefix="/stt",  # All routes in this file will start with /stt
    tags=["Speech-to-Text"]  # This is for the API docs
)

# Initialize the Whisper model (loaded once at startup)
model = WhisperModel("large-v3-turbo", device="auto", compute_type="auto")


async def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """Transcribes audio bytes using Whisper and returns the text."""
    try:
        # Write audio bytes to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name

        try:
            # Transcribe the audio
            segments, info = model.transcribe(tmp_path, beam_size=5)
            
            # Combine all segments into a single transcript
            transcript = " ".join([segment.text for segment in segments])
            return transcript.strip()
        finally:
            # Clean up the temporary file
            os.unlink(tmp_path)
            
    except Exception as e:
        raise e


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


