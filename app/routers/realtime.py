"""
WebSocket router for real-time streaming responses.

This module provides WebSocket endpoints for:
- Streaming STT transcription segment by segment
- Streaming LLM responses token by token
- Full voice pipeline (STT → LLM → TTS)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import ollama
import json
import tempfile
import os
import base64
from faster_whisper import WhisperModel
from .tts import get_tts_audio_bytes, TTSRequest

router = APIRouter(
    prefix="/ws",
    tags=["WebSocket"]
)

# Load Whisper model (reuse from stt module or load here)
# Using a smaller model for faster streaming
stt_model = WhisperModel("small", device="auto", compute_type="auto")

# System prompt for concise responses
SYSTEM_PROMPT = """You are a helpful voice assistant. Keep your responses brief and conversational - 
aim for 1-2 sentences maximum. Be direct and avoid unnecessary details or filler words."""


async def stream_transcription(websocket: WebSocket, audio_bytes: bytes):
    """Stream transcription segments as they're generated."""
    tmp_path = None
    try:
        # Write audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        # Transcribe and stream segments
        segments, info = stt_model.transcribe(tmp_path, beam_size=1)
        
        full_transcript = ""
        for segment in segments:
            text = segment.text.strip()
            if text:
                full_transcript += text + " "
                # Send each segment as it's processed
                await websocket.send_json({
                    "type": "stt_segment",
                    "content": text,
                    "start": segment.start,
                    "end": segment.end
                })
        
        # Send completion
        await websocket.send_json({
            "type": "stt_done",
            "full_transcript": full_transcript.strip()
        })
        
        return full_transcript.strip()
        
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat responses.
    
    Client sends: {"type": "chat", "prompt": "user message", "model": "llama3.2:1b"}
    Server streams: {"type": "token", "content": "word"} for each token
    Server sends: {"type": "done", "full_response": "complete text"} when finished
    Server sends: {"type": "error", "message": "error details"} on error
    """
    await websocket.accept()
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "chat":
                prompt = message.get("prompt", "")
                model = message.get("model", "llama3.2:1b")
                
                if not prompt.strip():
                    await websocket.send_json({
                        "type": "error",
                        "message": "Empty prompt received"
                    })
                    continue
                
                # Stream the LLM response
                full_response = ""
                try:
                    # Signal that streaming is starting
                    await websocket.send_json({
                        "type": "start",
                        "prompt": prompt
                    })
                    
                    # Stream tokens from Ollama
                    for chunk in ollama.chat(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ],
                        stream=True
                    ):
                        token = chunk["message"]["content"]
                        full_response += token
                        
                        # Send each token to client
                        await websocket.send_json({
                            "type": "token",
                            "content": token
                        })
                    
                    # Send completion signal with full response
                    await websocket.send_json({
                        "type": "done",
                        "full_response": full_response
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"LLM error: {str(e)}"
                    })
            
            elif message.get("type") == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message.get('type')}"
                })
                
    except WebSocketDisconnect:
        print("WebSocket client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass


def is_sentence_end(text: str) -> bool:
    """Check if text ends with a sentence boundary."""
    text = text.rstrip()
    return text.endswith(('.', '!', '?', '。', '！', '？')) or text.endswith('.\n') or text.endswith('\n\n')


async def generate_tts_chunk(text: str, chunk_index: int) -> tuple[int, bytes]:
    """Generate TTS for a text chunk and return with index for ordering."""
    tts_request = TTSRequest(text=text)
    audio_bytes = await get_tts_audio_bytes(tts_request)
    return chunk_index, audio_bytes


@router.websocket("/voice")
async def websocket_voice_pipeline(websocket: WebSocket):
    """
    Full voice pipeline WebSocket endpoint with STREAMING TTS.
    
    Client sends: {"type": "audio", "data": "<base64 encoded audio>"}
    
    Server streams:
    1. STT segments: {"type": "stt_segment", "content": "text", "start": 0.0, "end": 1.5}
    2. STT complete: {"type": "stt_done", "full_transcript": "full text"}
    3. LLM start: {"type": "llm_start"}
    4. LLM tokens: {"type": "llm_token", "content": "word"}
    5. TTS chunks: {"type": "tts_chunk", "audio": "<base64>", "index": 0, "sentence": "text"}
    6. LLM complete: {"type": "llm_done", "full_response": "full text"}
    7. TTS complete: {"type": "tts_done", "total_chunks": N}
    8. Pipeline complete: {"type": "pipeline_done"}
    
    Audio starts playing as soon as first sentence is ready!
    """
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "audio":
                model = message.get("model", "llama3.2:1b")
                
                try:
                    # Decode base64 audio
                    audio_base64 = message.get("data", "")
                    if not audio_base64:
                        await websocket.send_json({
                            "type": "error",
                            "message": "No audio data received"
                        })
                        continue
                    
                    audio_bytes = base64.b64decode(audio_base64)
                    
                    # Step 1: Stream STT
                    await websocket.send_json({"type": "stt_start"})
                    transcript = await stream_transcription(websocket, audio_bytes)
                    
                    if not transcript:
                        await websocket.send_json({
                            "type": "error",
                            "message": "No speech detected"
                        })
                        continue
                    
                    # Step 2: Stream LLM response with sentence-level TTS
                    await websocket.send_json({"type": "llm_start"})
                    await websocket.send_json({"type": "tts_start"})
                    
                    full_response = ""
                    sentence_buffer = ""
                    chunk_index = 0
                    
                    for chunk in ollama.chat(
                        model=model,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": transcript}
                        ],
                        stream=True
                    ):
                        token = chunk["message"]["content"]
                        full_response += token
                        sentence_buffer += token
                        
                        # Send token to client for visual streaming
                        await websocket.send_json({
                            "type": "llm_token",
                            "content": token
                        })
                        
                        # Check if we have a complete sentence
                        if is_sentence_end(sentence_buffer) and len(sentence_buffer.strip()) > 5:
                            # Generate TTS for this sentence immediately
                            sentence_text = sentence_buffer.strip()
                            
                            try:
                                tts_request = TTSRequest(text=sentence_text)
                                audio_response = await get_tts_audio_bytes(tts_request)
                                audio_base64_chunk = base64.b64encode(audio_response).decode('utf-8')
                                
                                # Send audio chunk to client
                                await websocket.send_json({
                                    "type": "tts_chunk",
                                    "audio": audio_base64_chunk,
                                    "index": chunk_index,
                                    "sentence": sentence_text
                                })
                                
                                chunk_index += 1
                            except Exception as tts_error:
                                print(f"TTS chunk error: {tts_error}")
                            
                            # Reset buffer for next sentence
                            sentence_buffer = ""
                    
                    # Handle any remaining text in buffer
                    if sentence_buffer.strip():
                        try:
                            tts_request = TTSRequest(text=sentence_buffer.strip())
                            audio_response = await get_tts_audio_bytes(tts_request)
                            audio_base64_chunk = base64.b64encode(audio_response).decode('utf-8')
                            
                            await websocket.send_json({
                                "type": "tts_chunk",
                                "audio": audio_base64_chunk,
                                "index": chunk_index,
                                "sentence": sentence_buffer.strip()
                            })
                            chunk_index += 1
                        except Exception as tts_error:
                            print(f"TTS final chunk error: {tts_error}")
                    
                    # LLM complete
                    await websocket.send_json({
                        "type": "llm_done",
                        "full_response": full_response
                    })
                    
                    # TTS complete
                    await websocket.send_json({
                        "type": "tts_done",
                        "total_chunks": chunk_index
                    })
                    
                    # Pipeline complete
                    await websocket.send_json({"type": "pipeline_done"})
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Pipeline error: {str(e)}"
                    })
            
            elif message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            
            else:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown message type: {message.get('type')}"
                })
                
    except WebSocketDisconnect:
        print("Voice WebSocket client disconnected")
    except Exception as e:
        print(f"Voice WebSocket error: {e}")
