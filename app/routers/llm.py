from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import ollama

# APIRouter to group related endpoints
router = APIRouter(
    prefix="/llm",  # All routes in this file will start with /llm
    tags=["Language Model"] # This is for the API docs
)

# request body schema
class LLMRequest(BaseModel):
    prompt: str
    model: str = "llama3:8b" # default model

@router.post("/generate-response-ollama")
async def generate_response(request: LLMRequest):
    """
    Generates a response from the Ollama model.
    """
    try:
        response = ollama.chat(
            model=request.model,
            messages=[
                {
                    "role": "user",
                    "content": request.prompt,
                },
            ],
        )
        return {"response": response["message"]["content"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
