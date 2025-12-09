from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ollama

from ..config import SYSTEM_PROMPT, DEFAULT_MODEL

router = APIRouter(
    prefix="/llm",  # All routes in this file will start with /llm
    tags=["Language Model"]  # This is for the API docs
)


# Request body schema
class LLMRequest(BaseModel):
    prompt: str
    model: str = DEFAULT_MODEL


async def get_llm_response(request: LLMRequest):
    """Generates a response from the Ollama model."""
    response = ollama.chat(
        model=request.model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.prompt}
        ],
    )
    return {"response": response["message"]["content"]}


@router.post("/generate-response-ollama")
async def generate_response(request: LLMRequest):
    """API endpoint wrapper for the LLM logic."""
    try:
        return await get_llm_response(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
