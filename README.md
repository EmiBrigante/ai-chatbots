# AI Voice Chatbot

A local voice chatbot that runs entirely on your machine. Talk to it, and it talks back. No cloud, no API keys, no data leaving your computer.

## What it does

- You speak into your mic
- Whisper transcribes your speech
- Ollama generates a response using a local LLM
- Piper TTS reads the response back to you

Everything runs locally. Works offline once you have the models downloaded.

## Features

- **Fully local** - No internet required after setup
- **Real-time streaming** - See the response as it's being generated
- **Hands-free mode** - Voice activity detection, no need to click buttons
- **Fast TTS** - Audio starts playing before the full response is ready
- **Multiple models** - Choose between different Ollama models

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/download) installed and running

Pull the default model:

```bash
ollama pull llama3.2:1b
```

## Installation

```bash
# Clone and enter the project
git clone 
cd ai-chatbots

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download the Piper TTS voice model
mkdir -p models/piper
curl -L -o models/piper/en_US-amy-medium.onnx \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx"
curl -L -o models/piper/en_US-amy-medium.onnx.json \
    "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
```

## Usage

Start the server:

```bash
python main.py
```

Open your browser at `http://127.0.0.1:8080`

There's also a Streamlit frontend if you prefer:

```bash
streamlit run streamlit_app.py
```

## Project Structure

```
ai-chatbots/
├── main.py              # FastAPI server entry point
├── app/
│   ├── config.py        # Shared configuration
│   └── routers/
│       ├── chatbot.py   # Orchestrates LLM + TTS
│       ├── llm.py       # Ollama integration
│       ├── stt.py       # Whisper speech-to-text
│       ├── tts.py       # Piper text-to-speech
│       └── realtime.py  # WebSocket streaming
├── frontend/            # Vanilla JS frontend
├── streamlit_app.py     # Alternative Streamlit frontend
└── models/piper/        # TTS voice models
```

## Configuration

Edit `app/config.py` to change:

- Default LLM model
- System prompt
- Whisper model size

## TODO

- [ ] Add conversation history/memory
- [ ] Support multiple TTS voices
- [ ] Custom system prompts from the UI
- [ ] Docker support
- [ ] Better mobile support

## Tech Stack

- **Backend**: FastAPI + WebSockets
- **STT**: faster-whisper
- **LLM**: Ollama
- **TTS**: Piper TTS
- **Frontend**: Vanilla JS / Streamlit

## License

MIT - see [LICENSE](LICENSE)
