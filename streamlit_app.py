import streamlit as st
import requests
import numpy as np
import queue
import time
import io
import wave
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase
import av
import torch

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
    
    .status-speaking {
        background: rgba(239, 68, 68, 0.15);
        border-color: rgba(239, 68, 68, 0.4);
        color: #f87171;
        animation: pulse 1.5s ease-in-out infinite;
    }
    
    .status-processing {
        background: rgba(99, 102, 241, 0.15);
        border-color: rgba(99, 102, 241, 0.4);
        color: #a5b4fc;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.6; }
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

# Initialize Silero VAD
@st.cache_resource
def load_vad_model():
    model, utils = torch.hub.load(
        repo_or_dir='snakers4/silero-vad',
        model='silero_vad',
        force_reload=False,
        onnx=False
    )
    return model, utils

# Load VAD model
vad_model, vad_utils = load_vad_model()
(get_speech_timestamps, _, read_audio, _, _) = vad_utils

# Audio processor with VAD
class VADAudioProcessor(AudioProcessorBase):
    def __init__(self):
        self.audio_buffer = []
        self.sample_rate = 16000
        self.silence_threshold = 0.5  # seconds of silence to trigger end
        self.min_speech_duration = 0.3  # minimum speech duration
        self.last_speech_time = None
        self.is_speaking = False
        self.speech_started = False
        self.audio_queue = queue.Queue()
        self.result_queue = queue.Queue()
        
    def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
        # Convert to numpy array
        audio = frame.to_ndarray()
        
        # Convert to mono if stereo
        if len(audio.shape) > 1:
            audio = audio.mean(axis=0)
        
        # Resample to 16kHz if needed
        if frame.sample_rate != self.sample_rate:
            # Simple resampling
            ratio = self.sample_rate / frame.sample_rate
            new_length = int(len(audio) * ratio)
            audio = np.interp(
                np.linspace(0, len(audio), new_length),
                np.arange(len(audio)),
                audio
            )
        
        # Normalize audio
        audio = audio.astype(np.float32)
        if np.abs(audio).max() > 0:
            audio = audio / np.abs(audio).max()
        
        # VAD check
        audio_tensor = torch.from_numpy(audio)
        speech_prob = vad_model(audio_tensor, self.sample_rate).item()
        
        current_time = time.time()
        
        if speech_prob > 0.5:  # Speech detected
            self.is_speaking = True
            self.speech_started = True
            self.last_speech_time = current_time
            self.audio_buffer.extend(audio.tolist())
        else:
            if self.speech_started and self.last_speech_time:
                silence_duration = current_time - self.last_speech_time
                
                if silence_duration < self.silence_threshold:
                    # Still within silence threshold, keep buffering
                    self.audio_buffer.extend(audio.tolist())
                else:
                    # Silence exceeded threshold, speech ended
                    if len(self.audio_buffer) > self.sample_rate * self.min_speech_duration:
                        # Put audio in queue for processing
                        audio_data = np.array(self.audio_buffer, dtype=np.float32)
                        self.audio_queue.put(audio_data)
                    
                    # Reset
                    self.audio_buffer = []
                    self.speech_started = False
                    self.is_speaking = False
                    self.last_speech_time = None
        
        return frame


# Header
st.markdown("""
<div class="main-header">
    <h1>🎙️ Voice AI</h1>
    <p>Just speak — I'll listen and respond automatically</p>
</div>
""", unsafe_allow_html=True)

# Instructions
st.markdown("""
<div class="instructions">
    <strong>How it works:</strong> Click START below, then speak naturally. 
    When you pause, I'll automatically transcribe and respond.
</div>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processing" not in st.session_state:
    st.session_state.processing = False

# WebRTC streamer
ctx = webrtc_streamer(
    key="voice-chat",
    mode=WebRtcMode.SENDONLY,
    audio_processor_factory=VADAudioProcessor,
    media_stream_constraints={"audio": True, "video": False},
    rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
    async_processing=True,
)

# Process audio when available
if ctx.audio_processor:
    processor = ctx.audio_processor
    
    # Check for audio in queue
    try:
        audio_data = processor.audio_queue.get_nowait()
        
        if audio_data is not None and len(audio_data) > 0:
            st.session_state.processing = True
            
            # Convert to WAV bytes
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(16000)
                # Convert float32 to int16
                audio_int16 = (audio_data * 32767).astype(np.int16)
                wav_file.writeframes(audio_int16.tobytes())
            
            wav_bytes = wav_buffer.getvalue()
            
            # Transcribe
            with st.spinner("🎯 Transcribing..."):
                try:
                    files = {"file": ("recording.wav", wav_bytes, "audio/wav")}
                    stt_response = requests.post(STT_URL, files=files)
                    stt_response.raise_for_status()
                    transcript = stt_response.json()["transcription"]
                    
                    if transcript.strip():
                        # Show transcript
                        st.markdown(f'''
                        <div class="transcript-box">
                            <div class="transcript-label">📝 You said</div>
                            {transcript}
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
                            
                            st.audio(audio_response, format="audio/mpeg", autoplay=True)
                            
                except requests.exceptions.RequestException as e:
                    st.error(f"❌ Error: {e}")
            
            st.session_state.processing = False
            
    except queue.Empty:
        pass

# Status indicator
if ctx.state.playing:
    if st.session_state.processing:
        st.markdown('<div class="status-box status-processing">⚡ Processing...</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="status-box status-listening">👂 Listening... (speak now)</div>', unsafe_allow_html=True)

# Footer
st.markdown('''
<div class="footer">
    Powered by Ollama • Whisper • Silero VAD • gTTS
</div>
''', unsafe_allow_html=True)
