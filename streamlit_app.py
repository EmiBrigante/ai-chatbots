import streamlit as st
import requests
import io
import html
import json
from audiorecorder import audiorecorder

# Page configuration
st.set_page_config(
    page_title="AI Voice Chatbot",
    page_icon="🎙️",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    .stApp {
        font-family: 'Outfit', sans-serif;
        background: linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 50%, #16213e 100%);
        min-height: 100vh;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 0 1rem 0;
    }
    
    .main-header h1 {
        font-size: 2.8rem;
        font-weight: 700;
        background: linear-gradient(135deg, #00d4ff 0%, #7c3aed 50%, #f472b6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .main-header p {
        color: #94a3b8;
        font-size: 1.1rem;
        font-weight: 300;
    }
    
    .status-box {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        text-align: center;
    }
    
    .status-listening {
        background: rgba(16, 185, 129, 0.15);
        border-color: rgba(16, 185, 129, 0.4);
        color: #34d399;
    }
    
    .status-processing {
        background: rgba(99, 102, 241, 0.15);
        border-color: rgba(99, 102, 241, 0.4);
        color: #a5b4fc;
    }
    
    .transcript-box {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        border-radius: 16px;
        padding: 1.25rem;
        margin: 1.5rem 0;
        color: #a7f3d0;
        font-size: 1.05rem;
        line-height: 1.6;
    }
    
    .transcript-label {
        color: #10b981;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.5rem;
    }
    
    .response-section {
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 1.25rem;
        margin: 1.5rem 0;
    }
    
    .response-label {
        color: #818cf8;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.75rem;
    }
    
    .instructions {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1rem;
        margin: 1rem 0;
        color: #64748b;
        font-size: 0.9rem;
        text-align: center;
    }
    
    .footer {
        text-align: center;
        color: #475569;
        font-size: 0.8rem;
        padding: 2rem 0;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# API endpoints
BASE_URL = "http://127.0.0.1:8080"
CHATBOT_URL = f"{BASE_URL}/chatbot/audio-response"
STT_URL = f"{BASE_URL}/stt/transcribe"

# Header
st.markdown("""
<div class="main-header">
    <h1>🎙️ Voice AI</h1>
    <p>Click to record — I'll listen and respond</p>
</div>
""", unsafe_allow_html=True)

# Instructions
st.markdown("""
<div class="instructions">
    <strong>How it works:</strong> Click the microphone button to start recording, 
    click again to stop. I'll transcribe and respond.
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "last_audio_bytes" not in st.session_state:
    st.session_state.last_audio_bytes = None

# Audio recorder (simple click to record/stop)
audio = audiorecorder("🎤 Click to Record", "⏹️ Click to Stop")

# Process audio when recording is complete
if len(audio) > 0:
    # Get audio bytes
    audio_bytes = audio.export().read()
    
    # Only process if this is new audio (different from last processed)
    if audio_bytes != st.session_state.last_audio_bytes:
        st.session_state.last_audio_bytes = audio_bytes
        
        # Show that we received audio
        st.markdown('<div class="status-box status-processing">⚡ Processing your audio...</div>', unsafe_allow_html=True)
        
        # Transcribe
        with st.spinner("🎯 Transcribing..."):
            try:
                files = {"file": ("recording.wav", audio_bytes, "audio/wav")}
                stt_response = requests.post(STT_URL, files=files)
                stt_response.raise_for_status()
                transcript = stt_response.json()["transcription"]
                
                if transcript.strip():
                    # Show transcript (escape HTML to prevent XSS)
                    safe_transcript = html.escape(transcript)
                    st.markdown(f'''
                    <div class="transcript-box">
                        <div class="transcript-label">📝 You said</div>
                        {safe_transcript}
                    </div>
                    ''', unsafe_allow_html=True)
                    
                    # Get AI response
                    with st.spinner("🤖 Generating response..."):
                        payload = {"prompt": transcript}
                        response = requests.post(CHATBOT_URL, json=payload)
                        response.raise_for_status()
                        audio_response = response.content
                        
                        st.markdown('''
                        <div class="response-section">
                            <div class="response-label">🔊 AI Response</div>
                        </div>
                        ''', unsafe_allow_html=True)
                        
                        st.audio(audio_response, format="audio/wav", autoplay=True)
                else:
                    st.warning("🤔 Couldn't detect any speech. Please try again.")
                        
            except requests.exceptions.RequestException as e:
                st.error(f"❌ Network error: {e}")
            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid response from server: {e}")

# Footer
st.markdown('''
<div class="footer">
    Powered by Ollama • Whisper • Piper TTS
</div>
''', unsafe_allow_html=True)
