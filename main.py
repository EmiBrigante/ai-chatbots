from app.routers import tts  # Import the TTS router
from fastapi import FastAPI
import uvicorn

app = FastAPI()

app.include_router(tts.router)

@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080,)