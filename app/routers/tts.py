from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.responses import FileResponse
from gtts import gTTS
# APIRouter to group related endpoints
router = APIRouter(
    prefix="/tts",  # All routes in this file will start with /tts
    tags=["Text-to-Speech"] # This is for the API docs
)

# request body schema
class TTSRequest(BaseModel):
    text: str
    lang: str = "en"

@router.post("/generate-audio")
async def generate_audio(request: TTSRequest):
    """
    Generates a TTS audio file from the provided text and saves it.
    """
    try:
        tts = gTTS(text=request.text, lang=request.lang)
        file_path = "response.mp3"
        tts.save(file_path)
        return {"status": "success", "file_path": f"/tts/get-audio/{file_path}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/get-audio/{file_path}")
async def get_audio(file_path: str):
    """
    Returns the audio file.
    """
    return FileResponse(path=file_path, media_type="audio/mpeg", filename=file_path)

