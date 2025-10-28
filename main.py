import uvicorn
import fastapi
from gtts import gTTS
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# TTS Test
# tts = gTTS("Hello, world!", lang="en")
# tts.save("hello.mp3")

# Initialize the FastAPI app
app = fastapi.FastAPI()

# request body schema
class TTSRequest(BaseModel):
    text: str
    lang: str = "en"

# API endpoint for TTS
@app.post("/text-to-speech/")
async def text_to_speech(request: TTSRequest):
    """
    Generates a TTS audio file from the provided text and saves it.
    Returns a URL to fetch the audio file.
    """
    try:
        tts = gTTS(text=request.text, lang=request.lang)
        file_path = "response.mp3"
        tts.save(file_path)
 
        return {"status": "success", "file_path": f"/speech-audio/{file_path}"}
    except Exception as e:
        raise fastapi.HTTPException(status_code=500, detail=str(e))

@app.get("/speech-audio/{file_name}")
async def get_speech_audio(file_name: str):
    """
    Returns the audio file.
    """
    return FileResponse(path=file_name, media_type="audio/mpeg", filename=file_name)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)