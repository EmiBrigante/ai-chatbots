from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel
from .llm import get_llm_response, LLMRequest
from .tts import get_tts_audio_bytes, TTSRequest

router = APIRouter(
    prefix="/chatbot",
    tags=["Chatbot"]
)

class ChatRequest(BaseModel):
    prompt: str
    model: str = "llama3.2:1b"
    lang: str = "en"

@router.post("/audio-response")
async def audio_response(request: ChatRequest):
    """
    Orchestrates the chatbot response by calling the LLM and TTS functions directly.
    """
    try:
        # 1. Call the LLM function
        llm_request_data = LLMRequest(prompt=request.prompt, model=request.model)
        llm_result = await get_llm_response(llm_request_data)
        text_response = llm_result["response"]

        # 2. Call the TTS function
        tts_request_data = TTSRequest(text=text_response, lang=request.lang)
        audio_bytes = await get_tts_audio_bytes(tts_request_data)

        # 3. Return the audio content
        return Response(content=audio_bytes, media_type="audio/mpeg")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")
