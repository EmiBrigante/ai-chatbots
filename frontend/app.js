/**
 * Voice AI Chat - Main Application
 * 
 * Modules:
 * 1. Configuration
 * 2. State Management
 * 3. DOM Elements
 * 4. Utilities (logging, status)
 * 5. Audio Queue (streaming TTS playback)
 * 6. VAD (Voice Activity Detection)
 * 7. WebSocket (server communication)
 * 8. Recording (manual mode)
 * 9. Event Handlers
 * 10. Initialization
 */

// ============================================
// 1. CONFIGURATION
// ============================================

const CONFIG = {
    API_BASE: 'http://127.0.0.1:8080',
    WS_BASE: 'ws://127.0.0.1:8080',
    
    get WS_VOICE_URL() {
        return `${this.WS_BASE}/ws/voice`;
    },
    
    VAD: {
        volumeThreshold: 15,      // Volume level to detect speech (0-100)
        silenceTimeout: 1000,     // ms of silence before triggering
        minSpeechDuration: 300,   // Minimum speech duration in ms
        minAudioSize: 1000,       // Minimum audio blob size in bytes
    }
};

const STATUS = {
    READY: 'ready',
    RECORDING: 'recording',
    PROCESSING: 'processing'
};

// ============================================
// 2. STATE MANAGEMENT
// ============================================

const state = {
    // WebSocket
    websocket: null,
    pipelineResolve: null,
    processingStartTime: null,
    
    // Manual Recording
    recording: {
        mediaRecorder: null,
        chunks: [],
        isActive: false,
        startTime: null,
        timer: null
    },
    
    // Audio Queue (TTS playback)
    audio: {
        queue: [],
        isPlaying: false,
        currentIndex: 0
    },
    
    // VAD (Hands-free mode)
    vad: {
        isEnabled: false,
        isProcessing: false,
        isSpeaking: false,
        silenceStart: null,
        speechStart: null,
        stream: null,
        mediaRecorder: null,
        audioChunks: [],
        audioContext: null,
        analyser: null,
        animationFrame: null
    }
};

// ============================================
// 3. DOM ELEMENTS
// ============================================

const elements = {
    // Main UI
    recordBtn: document.getElementById('recordBtn'),
    clearBtn: document.getElementById('clearBtn'),
    transcript: document.getElementById('transcript'),
    response: document.getElementById('response'),
    audioPlayer: document.getElementById('audioPlayer'),
    modelSelect: document.getElementById('modelSelect'),
    
    // Status
    statusIndicator: document.getElementById('statusIndicator'),
    statusText: document.getElementById('statusText'),
    recordingDuration: document.getElementById('recordingDuration'),
    processingTime: document.getElementById('processingTime'),
    logsContainer: document.getElementById('logs'),
    
    // Badges
    sttBadge: document.getElementById('sttBadge'),
    llmBadge: document.getElementById('llmBadge'),
    speakingBadge: document.getElementById('speakingBadge'),
    
    // Hands-free mode
    handsFreeToggle: document.getElementById('handsFreeToggle'),
    volumeMeterContainer: document.getElementById('volumeMeterContainer'),
    volumeBar: document.getElementById('volumeBar'),
    volumeStatus: document.getElementById('volumeStatus')
};

// ============================================
// 4. UTILITIES
// ============================================

function log(message, type = 'info') {
    const timeStr = new Date().toTimeString().split(' ')[0];
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <span class="log-time">[${timeStr}]</span>
        <span class="log-${type}">${message}</span>
    `;
    elements.logsContainer.appendChild(entry);
    elements.logsContainer.scrollTop = elements.logsContainer.scrollHeight;
}

function setStatus(status, text) {
    elements.statusIndicator.className = `status-indicator status-${status}`;
    if (status === STATUS.RECORDING) {
        elements.statusIndicator.classList.add('recording');
    }
    elements.statusText.textContent = text;
}

function startStreamingEffect(element, badge) {
    element.classList.add('streaming');
    badge.classList.remove('hidden');
}

function stopStreamingEffect(element, badge) {
    element.classList.remove('streaming');
    badge.classList.add('hidden');
}

function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Failed to read blob'));
        reader.onloadend = () => resolve(reader.result.split(',')[1]);
        reader.readAsDataURL(blob);
    });
}

function base64ToBlob(base64, mimeType = 'audio/wav') {
    const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    return new Blob([bytes], { type: mimeType });
}

// ============================================
// 5. AUDIO QUEUE (Streaming TTS Playback)
// ============================================

const AudioQueue = {
    add(audioBase64, index, sentence) {
        const blob = base64ToBlob(audioBase64);
        const url = URL.createObjectURL(blob);
        state.audio.queue.push({ url, index, sentence });
        
        if (!state.audio.isPlaying) {
            this.playNext();
        }
    },
    
    playNext() {
        if (state.audio.queue.length === 0) {
            state.audio.isPlaying = false;
            elements.speakingBadge.classList.add('hidden');
            
            // Resume hands-free listening
            if (state.vad.isEnabled && !state.vad.isProcessing) {
                elements.volumeStatus.textContent = 'Listening...';
                elements.volumeStatus.className = 'volume-status';
                setStatus(STATUS.READY, 'Ready - speak anytime');
            }
            return;
        }
        
        state.audio.isPlaying = true;
        elements.speakingBadge.classList.remove('hidden');
        
        const next = state.audio.queue.shift();
        elements.audioPlayer.src = next.url;
        elements.audioPlayer.classList.remove('hidden');
        
        elements.audioPlayer.play().catch(err => {
            log(`Audio play error: ${err.message}`, 'error');
            this.playNext();
        });
    },
    
    reset() {
        state.audio.queue = [];
        state.audio.isPlaying = false;
        state.audio.currentIndex = 0;
        elements.speakingBadge.classList.add('hidden');
    }
};

// Audio player event listeners
elements.audioPlayer.addEventListener('ended', () => AudioQueue.playNext());
elements.audioPlayer.addEventListener('pause', () => {
    if (state.audio.queue.length === 0) {
        elements.speakingBadge.classList.add('hidden');
    }
});

// ============================================
// 6. VAD (Voice Activity Detection)
// ============================================

const VAD = {
    async start() {
        try {
            state.vad.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Set up audio analysis
            state.vad.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            state.vad.analyser = state.vad.audioContext.createAnalyser();
            state.vad.analyser.fftSize = 256;
            state.vad.analyser.smoothingTimeConstant = 0.8;
            
            const source = state.vad.audioContext.createMediaStreamSource(state.vad.stream);
            source.connect(state.vad.analyser);
            
            // Set up recorder
            state.vad.mediaRecorder = new MediaRecorder(state.vad.stream);
            state.vad.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) state.vad.audioChunks.push(e.data);
            };
            state.vad.mediaRecorder.onstop = () => this.onRecordingStop();
            
            // Start monitoring
            this.monitorVolume();
            
            elements.volumeMeterContainer.classList.remove('hidden');
            elements.recordBtn.disabled = true;
            elements.recordBtn.textContent = '🎤 Hands-free Active';
            log('Hands-free mode enabled', 'success');
            
        } catch (error) {
            log(`Microphone error: ${error.message}`, 'error');
            elements.handsFreeToggle.checked = false;
            state.vad.isEnabled = false;
        }
    },
    
    stop() {
        if (state.vad.animationFrame) {
            cancelAnimationFrame(state.vad.animationFrame);
            state.vad.animationFrame = null;
        }
        
        if (state.vad.mediaRecorder?.state === 'recording') {
            state.vad.mediaRecorder.stop();
        }
        
        state.vad.audioContext?.close();
        state.vad.stream?.getTracks().forEach(track => track.stop());
        
        // Reset state
        Object.assign(state.vad, {
            isSpeaking: false,
            silenceStart: null,
            speechStart: null,
            audioChunks: [],
            audioContext: null,
            analyser: null,
            stream: null
        });
        
        elements.volumeMeterContainer.classList.add('hidden');
        elements.recordBtn.disabled = false;
        elements.recordBtn.textContent = '🎤 Start Recording';
    },
    
    monitorVolume() {
        if (!state.vad.analyser || !state.vad.isEnabled) return;
        
        const dataArray = new Uint8Array(state.vad.analyser.frequencyBinCount);
        state.vad.analyser.getByteFrequencyData(dataArray);
        
        const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
        const volumePercent = Math.min(100, (average / 128) * 100);
        
        elements.volumeBar.style.width = `${volumePercent}%`;
        
        // Skip if processing or playing
        if (state.vad.isProcessing || state.audio.isPlaying) {
            elements.volumeStatus.textContent = state.audio.isPlaying ? 'AI Speaking...' : 'Processing...';
            elements.volumeStatus.className = 'volume-status processing';
            state.vad.animationFrame = requestAnimationFrame(() => this.monitorVolume());
            return;
        }
        
        const now = Date.now();
        
        if (volumePercent > CONFIG.VAD.volumeThreshold) {
            this.onSpeechDetected(now);
        } else {
            this.onSilenceDetected(now);
        }
        
        state.vad.animationFrame = requestAnimationFrame(() => this.monitorVolume());
    },
    
    onSpeechDetected(now) {
        if (!state.vad.isSpeaking) {
            state.vad.isSpeaking = true;
            state.vad.speechStart = now;
            state.vad.silenceStart = null;
            state.vad.audioChunks = [];
            
            if (state.vad.mediaRecorder?.state === 'inactive') {
                state.vad.mediaRecorder.start();
                state.recording.startTime = now;
                setStatus(STATUS.RECORDING, 'Listening...');
            }
        }
        
        elements.volumeStatus.textContent = 'Speaking...';
        elements.volumeStatus.className = 'volume-status speaking';
        state.vad.silenceStart = null;
    },
    
    onSilenceDetected(now) {
        if (state.vad.isSpeaking) {
            if (!state.vad.silenceStart) {
                state.vad.silenceStart = now;
            }
            
            const silenceDuration = now - state.vad.silenceStart;
            const remaining = ((CONFIG.VAD.silenceTimeout - silenceDuration) / 1000).toFixed(1);
            elements.volumeStatus.textContent = `Silence... ${remaining}s`;
            
            if (silenceDuration >= CONFIG.VAD.silenceTimeout) {
                state.vad.isSpeaking = false;
                
                if (state.vad.mediaRecorder?.state === 'recording') {
                    const duration = ((now - state.recording.startTime) / 1000).toFixed(2);
                    elements.recordingDuration.textContent = duration;
                    state.vad.mediaRecorder.stop();
                }
                
                state.vad.silenceStart = null;
                state.vad.speechStart = null;
            }
        } else {
            elements.volumeStatus.textContent = 'Listening...';
            elements.volumeStatus.className = 'volume-status';
        }
    },
    
    async onRecordingStop() {
        if (state.vad.audioChunks.length === 0 || state.vad.isProcessing) {
            state.vad.audioChunks = [];
            return;
        }
        
        const audioBlob = new Blob(state.vad.audioChunks, { type: 'audio/wav' });
        state.vad.audioChunks = [];
        
        state.vad.isProcessing = true;
        elements.volumeStatus.textContent = 'Processing...';
        elements.volumeStatus.className = 'volume-status processing';
        
        try {
            if (audioBlob.size < CONFIG.VAD.minAudioSize) {
                log('Audio too short, skipping...', 'info');
                return;
            }
            
            await Pipeline.run(audioBlob);
            
            if (state.vad.isEnabled) {
                elements.volumeStatus.textContent = 'Listening...';
                elements.volumeStatus.className = 'volume-status';
                setStatus(STATUS.READY, 'Ready');
            }
        } catch (error) {
            log(`Pipeline error: ${error.message}`, 'error');
            elements.response.textContent = `Error: ${error.message}`;
            setStatus(STATUS.READY, 'Ready');
            
            if (state.vad.isEnabled) {
                elements.volumeStatus.textContent = 'Listening...';
                elements.volumeStatus.className = 'volume-status';
            }
        } finally {
            state.vad.isProcessing = false;
        }
    },
    
    reset() {
        state.vad.isSpeaking = false;
        state.vad.silenceStart = null;
        state.vad.speechStart = null;
        state.vad.audioChunks = [];
        state.vad.isProcessing = false;
        elements.volumeStatus.textContent = 'Listening...';
        elements.volumeStatus.className = 'volume-status';
    }
};

// ============================================
// 7. WEBSOCKET
// ============================================

const WebSocketManager = {
    connect() {
        return new Promise((resolve, reject) => {
            if (state.websocket?.readyState === WebSocket.OPEN) {
                return resolve(state.websocket);
            }
            
            state.websocket = new WebSocket(CONFIG.WS_VOICE_URL);
            
            state.websocket.onopen = () => resolve(state.websocket);
            
            state.websocket.onerror = () => {
                log('Connection error', 'error');
                reject(new Error('WebSocket connection failed'));
            };
            
            state.websocket.onclose = () => {
                state.websocket = null;
            };
            
            state.websocket.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
        });
    },
    
    handleMessage(data) {
        switch (data.type) {
            // STT
            case 'stt_start':
                elements.transcript.textContent = '';
                startStreamingEffect(elements.transcript, elements.sttBadge);
                setStatus(STATUS.PROCESSING, 'Transcribing...');
                break;
                
            case 'stt_segment':
                elements.transcript.textContent += data.content + ' ';
                break;
                
            case 'stt_done':
                stopStreamingEffect(elements.transcript, elements.sttBadge);
                elements.transcript.textContent = data.full_transcript;
                log(`✓ Transcribed: "${data.full_transcript.substring(0, 40)}..."`, 'success');
                break;
            
            // LLM
            case 'llm_start':
                elements.response.textContent = '';
                startStreamingEffect(elements.response, elements.llmBadge);
                setStatus(STATUS.PROCESSING, 'Generating...');
                break;
                
            case 'llm_token':
                elements.response.textContent += data.content;
                break;
                
            case 'llm_done':
                stopStreamingEffect(elements.response, elements.llmBadge);
                break;
            
            // TTS
            case 'tts_start':
                AudioQueue.reset();
                setStatus(STATUS.PROCESSING, 'Speaking...');
                break;
                
            case 'tts_chunk':
                AudioQueue.add(data.audio, data.index, data.sentence);
                break;
                
            case 'tts_done':
                break;
            
            // Pipeline
            case 'pipeline_done':
                stopStreamingEffect(elements.transcript, elements.sttBadge);
                stopStreamingEffect(elements.response, elements.llmBadge);
                
                const elapsed = ((Date.now() - state.processingStartTime) / 1000).toFixed(2);
                elements.processingTime.textContent = elapsed;
                log(`✓ Complete (${elapsed}s)`, 'success');
                setStatus(STATUS.READY, 'Ready');
                
                if (!state.vad.isEnabled) {
                    elements.recordBtn.disabled = false;
                }
                
                if (state.pipelineResolve) {
                    state.pipelineResolve(true);
                    state.pipelineResolve = null;
                }
                break;
            
            // Error
            case 'error':
                stopStreamingEffect(elements.transcript, elements.sttBadge);
                stopStreamingEffect(elements.response, elements.llmBadge);
                
                log(`Server error: ${data.message}`, 'error');
                setStatus(STATUS.READY, 'Ready');
                
                if (!state.vad.isEnabled) {
                    elements.recordBtn.disabled = false;
                }
                
                if (state.pipelineResolve) {
                    state.pipelineResolve(false);
                    state.pipelineResolve = null;
                }
                break;
        }
    }
};

// ============================================
// 8. PIPELINE
// ============================================

const Pipeline = {
    async run(audioBlob) {
        return new Promise(async (resolve, reject) => {
            try {
                await WebSocketManager.connect();
                
                state.pipelineResolve = resolve;
                state.processingStartTime = Date.now();
                
                const base64Audio = await blobToBase64(audioBlob);
                log(`Sending audio (${(audioBlob.size / 1024).toFixed(1)} KB)...`, 'info');
                
                state.websocket.send(JSON.stringify({
                    type: 'audio',
                    data: base64Audio,
                    model: elements.modelSelect.value
                }));
                
            } catch (error) {
                log(`Pipeline error: ${error.message}`, 'error');
                reject(error);
            }
        });
    }
};

// ============================================
// 9. RECORDING (Manual Mode)
// ============================================

const Recording = {
    async init() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            state.recording.mediaRecorder = new MediaRecorder(stream);
            
            state.recording.mediaRecorder.ondataavailable = (e) => {
                if (e.data.size > 0) state.recording.chunks.push(e.data);
            };
            
            state.recording.mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(state.recording.chunks, { type: 'audio/wav' });
                state.recording.chunks = [];
                await this.process(audioBlob);
            };
            
            return true;
        } catch (error) {
            log(`Microphone error: ${error.message}`, 'error');
            return false;
        }
    },
    
    async start() {
        if (!state.recording.mediaRecorder) {
            if (!await this.init()) return;
        }
        
        state.recording.chunks = [];
        state.recording.mediaRecorder.start();
        state.recording.isActive = true;
        state.recording.startTime = Date.now();
        
        elements.recordBtn.textContent = '⏹️ Stop Recording';
        elements.recordBtn.classList.add('btn-recording');
        setStatus(STATUS.RECORDING, 'Recording...');
        
        state.recording.timer = setInterval(() => {
            const duration = (Date.now() - state.recording.startTime) / 1000;
            elements.recordingDuration.textContent = duration.toFixed(2);
        }, 100);
    },
    
    stop() {
        if (!state.recording.mediaRecorder || !state.recording.isActive) return;
        
        clearInterval(state.recording.timer);
        state.recording.mediaRecorder.stop();
        state.recording.isActive = false;
        
        elements.recordBtn.textContent = '🎤 Start Recording';
        elements.recordBtn.classList.remove('btn-recording');
        elements.recordBtn.disabled = true;
        setStatus(STATUS.PROCESSING, 'Processing...');
    },
    
    async process(audioBlob) {
        try {
            await Pipeline.run(audioBlob);
        } catch (error) {
            log(`Error: ${error.message}`, 'error');
            elements.response.textContent = `Error: ${error.message}`;
            setStatus(STATUS.READY, 'Ready');
            elements.recordBtn.disabled = false;
        }
    },
    
    toggle() {
        if (state.recording.isActive) {
            this.stop();
        } else {
            this.start();
        }
    }
};

// ============================================
// 10. CLEAR & RESET
// ============================================

function clearAll() {
    stopStreamingEffect(elements.transcript, elements.sttBadge);
    stopStreamingEffect(elements.response, elements.llmBadge);
    
    AudioQueue.reset();
    elements.audioPlayer.pause();
    
    if (state.vad.isEnabled) {
        VAD.reset();
    }
    
    elements.transcript.textContent = 'Your transcribed speech will appear here...';
    elements.response.textContent = 'The AI response will appear here...';
    elements.audioPlayer.classList.add('hidden');
    elements.audioPlayer.src = '';
    elements.recordingDuration.textContent = '0.00';
    elements.processingTime.textContent = '0.00';
    
    elements.logsContainer.innerHTML = `
        <div class="log-entry">
            <span class="log-time">[--:--:--]</span>
            <span class="log-info">Ready</span>
        </div>
    `;
}

// ============================================
// 11. EVENT HANDLERS
// ============================================

elements.recordBtn.addEventListener('click', () => Recording.toggle());
elements.clearBtn.addEventListener('click', clearAll);

elements.handsFreeToggle.addEventListener('change', (e) => {
    state.vad.isEnabled = e.target.checked;
    if (state.vad.isEnabled) {
        VAD.start();
    } else {
        VAD.stop();
    }
});

// ============================================
// 12. INITIALIZATION
// ============================================

function init() {
    log('Voice AI Chat ready', 'success');
    
    // Pre-connect WebSocket
    WebSocketManager.connect().catch(() => {});
}

// Start the app
init();

