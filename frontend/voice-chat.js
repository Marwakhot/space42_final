/**
 * Voice Chat Module for Orion Chat Widget
 * Adds speech-to-text and text-to-speech capabilities
 */

class VoiceChat {
    constructor(options = {}) {
        this.inputElement = options.inputElement;
        this.messagesContainer = options.messagesContainer;
        this.onSend = options.onSend || (() => {});
        this.voiceflowApiKey = options.voiceflowApiKey || null;
        this.voiceflowProjectId = options.voiceflowProjectId || null;
        
        this.recognition = null;
        this.isListening = false;
        this.synthesis = window.speechSynthesis;
        
        this.init();
    }
    
    init() {
        // Check for speech recognition support
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.continuous = false;
            this.recognition.interimResults = true;
            this.recognition.lang = 'en-US';
            
            this.recognition.onresult = (event) => {
                let finalTranscript = '';
                let interimTranscript = '';
                
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        finalTranscript += transcript;
                    } else {
                        interimTranscript += transcript;
                    }
                }
                
                if (this.inputElement) {
                    this.inputElement.value = finalTranscript || interimTranscript;
                    this.inputElement.style.color = finalTranscript ? '#f3f4f6' : '#9ca3af';
                }
            };
            
            this.recognition.onend = () => {
                this.isListening = false;
                this.updateVoiceButton(false);
                
                // Auto-send if we have final text
                if (this.inputElement && this.inputElement.value.trim()) {
                    this.inputElement.style.color = '#f3f4f6';
                }
            };
            
            this.recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                this.isListening = false;
                this.updateVoiceButton(false);
            };
        }
    }
    
    createVoiceButton() {
        const button = document.createElement('button');
        button.id = 'voiceChatBtn';
        button.className = 'voice-chat-btn';
        button.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                <line x1="12" y1="19" x2="12" y2="23"/>
                <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
        `;
        button.title = this.recognition ? 'Click to speak' : 'Voice not supported';
        button.disabled = !this.recognition;
        
        button.onclick = () => this.toggleListening();
        
        return button;
    }
    
    toggleListening() {
        if (!this.recognition) {
            alert('Speech recognition is not supported in your browser. Please use Chrome.');
            return;
        }
        
        if (this.isListening) {
            this.recognition.stop();
            this.isListening = false;
        } else {
            this.inputElement.value = '';
            this.inputElement.placeholder = 'Listening...';
            this.recognition.start();
            this.isListening = true;
        }
        
        this.updateVoiceButton(this.isListening);
    }
    
    updateVoiceButton(isListening) {
        const btn = document.getElementById('voiceChatBtn');
        if (!btn) return;
        
        if (isListening) {
            btn.classList.add('listening');
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="currentColor" stroke="none" width="20" height="20">
                    <rect x="6" y="6" width="12" height="12" rx="2"/>
                </svg>
            `;
            btn.style.background = 'linear-gradient(135deg, #ef4444, #dc2626)';
            btn.style.animation = 'pulse-recording 1s ease-in-out infinite';
        } else {
            btn.classList.remove('listening');
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
                    <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
                    <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
                    <line x1="12" y1="19" x2="12" y2="23"/>
                    <line x1="8" y1="23" x2="16" y2="23"/>
                </svg>
            `;
            btn.style.background = 'linear-gradient(135deg, #8b5cf6, #6366f1)';
            btn.style.animation = 'none';
            
            if (this.inputElement) {
                this.inputElement.placeholder = 'Type or click mic to speak...';
            }
        }
    }
    
    speak(text) {
        if (!this.synthesis) return;
        
        // Cancel any ongoing speech
        this.synthesis.cancel();
        
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.95;
        utterance.pitch = 1;
        utterance.volume = 1;
        
        // Try to find the best voice - prioritize Arabic/Emirati accents
        const voices = this.synthesis.getVoices();
        
        // Priority order for voice selection
        let selectedVoice = null;
        
        // 1. Try Arabic UAE voice
        selectedVoice = voices.find(v => v.lang === 'ar-AE' || v.lang === 'ar-SA');
        
        // 2. Try any Arabic voice
        if (!selectedVoice) {
            selectedVoice = voices.find(v => v.lang.startsWith('ar'));
        }
        
        // 3. Try UK English (more neutral, less American)
        if (!selectedVoice) {
            selectedVoice = voices.find(v => 
                v.lang === 'en-GB' && 
                (v.name.includes('Google') || v.name.includes('Daniel') || v.name.includes('Male'))
            );
        }
        
        // 4. Try Google UK English
        if (!selectedVoice) {
            selectedVoice = voices.find(v => v.name.includes('Google UK English'));
        }
        
        // 5. Try any English voice that's not American
        if (!selectedVoice) {
            selectedVoice = voices.find(v => 
                v.lang === 'en-GB' || v.lang === 'en-AU' || v.lang === 'en-IN'
            );
        }
        
        // 6. Fallback to any available voice
        if (!selectedVoice && voices.length > 0) {
            selectedVoice = voices.find(v => v.lang.startsWith('en')) || voices[0];
        }
        
        if (selectedVoice) {
            utterance.voice = selectedVoice;
            console.log('Using voice:', selectedVoice.name, selectedVoice.lang);
        }
        
        this.synthesis.speak(utterance);
    }
    
    stopSpeaking() {
        if (this.synthesis) {
            this.synthesis.cancel();
        }
    }
}

// CSS styles for voice button
const voiceChatStyles = document.createElement('style');
voiceChatStyles.textContent = `
    .voice-chat-btn {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        border: none;
        background: linear-gradient(135deg, #8b5cf6, #6366f1);
        color: white;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all 0.3s;
        flex-shrink: 0;
    }
    
    .voice-chat-btn:hover:not(:disabled) {
        transform: scale(1.1);
        box-shadow: 0 0 20px rgba(139, 92, 246, 0.5);
    }
    
    .voice-chat-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
    }
    
    .voice-chat-btn.listening {
        background: linear-gradient(135deg, #ef4444, #dc2626);
    }
    
    @keyframes pulse-recording {
        0%, 100% { transform: scale(1); box-shadow: 0 0 20px rgba(239, 68, 68, 0.5); }
        50% { transform: scale(1.1); box-shadow: 0 0 30px rgba(239, 68, 68, 0.8); }
    }
    
    .orion-chat-input-area {
        display: flex;
        gap: 0.5rem;
        align-items: center;
        padding: 0.75rem;
    }
    
    .orion-chat-input {
        flex: 1;
    }
    
    /* Speaker button for bot messages */
    .speak-btn {
        background: none;
        border: none;
        color: #8b5cf6;
        cursor: pointer;
        padding: 0.25rem;
        opacity: 0.6;
        transition: opacity 0.2s;
    }
    
    .speak-btn:hover {
        opacity: 1;
    }
`;
document.head.appendChild(voiceChatStyles);

// Helper function to initialize voice chat on any page
function initVoiceChatWidget(inputId, messagesId, voiceflowConfig = {}) {
    const inputElement = document.getElementById(inputId);
    const messagesContainer = document.getElementById(messagesId);
    
    if (!inputElement) return null;
    
    const voiceChat = new VoiceChat({
        inputElement: inputElement,
        messagesContainer: messagesContainer,
        voiceflowApiKey: voiceflowConfig.apiKey,
        voiceflowProjectId: voiceflowConfig.projectId
    });
    
    // Add voice button to input area
    const inputArea = inputElement.parentElement;
    if (inputArea) {
        const voiceBtn = voiceChat.createVoiceButton();
        inputArea.appendChild(voiceBtn);
    }
    
    // Store reference for speaking bot responses
    window.voiceChatInstance = voiceChat;
    
    return voiceChat;
}

// Function to add speak button to bot messages
function addSpeakButton(messageElement, text) {
    if (!window.voiceChatInstance) return;
    
    const speakBtn = document.createElement('button');
    speakBtn.className = 'speak-btn';
    speakBtn.title = 'Listen to this message';
    speakBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>
        </svg>
    `;
    speakBtn.onclick = () => {
        window.voiceChatInstance.speak(text);
    };
    
    messageElement.appendChild(speakBtn);
}
