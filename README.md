# AI Voice Chatbot

This project demonstrates a **fully local** AI Voice Chatbot that uses **Ollama** for text generation, **Whisper** for speech-to-text, and **Piper TTS** for fast neural voice output. It consists of a FastAPI backend and a Streamlit frontend.

## Features

- **Local LLM**: Uses Ollama (running `llama3.2:1b` by default) for privacy and offline capability.
- **Speech-to-Text**: Uses faster-whisper (`large-v3-turbo` model) for accurate speech recognition.
- **Text-to-Speech**: Fast neural TTS using Piper (runs locally, no internet required).
- **Voice Input**: Record your voice directly in the browser and get audio responses.
- **Interactive UI**: Modern web interface built with Streamlit with voice activity detection.

## Prerequisites

1.  **Python 3.10+**
2.  **Ollama**: [Download and install Ollama](https://ollama.com/download).
3.  **Pull the LLM Model**: Run the following command in your terminal:
    ```bash
    ollama pull llama3.2:1b
    ```

## Installation

1.  Clone the repository.
2.  Create a virtual environment (recommended):
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Download the Piper TTS voice model:
    ```bash
    mkdir -p models/piper
    curl -L -o models/piper/en_US-amy-medium.onnx \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx"
    curl -L -o models/piper/en_US-amy-medium.onnx.json \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
    ```

## Usage

To run the application, you need to start both the backend server and the frontend interface.

### 1. Start the Backend (FastAPI)

Open a terminal and run:
```bash
python main.py
```
The API will start at `http://127.0.0.1:8080`.

### 2. Start the Frontend (Streamlit)

Open a new terminal and run:
```bash
python -m streamlit run streamlit_app.py
```
This will open the web app in your browser.

## Project Structure

- `app/routers/`: Contains API routes for the Chatbot, LLM, and TTS services.
- `main.py`: Entry point for the FastAPI backend.
- `streamlit_app.py`: Frontend code using Streamlit.
