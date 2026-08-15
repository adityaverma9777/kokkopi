import { WidgetConfig, getSessionId } from './config';

export class KokkopiClient {
    private baseUrl: string;
    private config: WidgetConfig;
    private ws: WebSocket | null = null;
    private mediaRecorder: MediaRecorder | null = null;
    private audioContext: AudioContext | null = null;

    constructor(baseUrl: string, config: WidgetConfig) {
        this.baseUrl = baseUrl;
        this.config = config;
    }

    public async streamChat(message: string, onToken: (token: string) => void, onComplete: () => void, onError: (err: string) => void) {
        try {
            const res = await fetch(`${this.baseUrl}/api/public/agents/${this.config.agent_id}/chat/stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message, session_id: getSessionId() })
            });

            if (!res.ok) {
                onError("Failed to connect to agent.");
                return;
            }

            const reader = res.body?.getReader();
            const decoder = new TextDecoder("utf-8");

            if (!reader) return;

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            onComplete();
                            return;
                        }
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.error) {
                                onError(parsed.error);
                                return;
                            }
                            if (parsed.token) {
                                onToken(parsed.token);
                            }
                        } catch (e) {
                            // ignore parse errors for partial chunks
                        }
                    }
                }
            }
            onComplete();
        } catch (e) {
            onError("Connection error.");
        }
    }

    public async startVoiceSession(
        onTranscript: (t: string) => void, 
        onThinking: () => void, 
        onComplete: () => void,
        onError: (err: string) => void
    ) {
        // Stop any existing session
        this.stopVoiceSession();

        let stream: MediaStream;
        try {
            stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        } catch (err) {
            onError("Microphone access denied.");
            return;
        }

        const wsUrl = this.baseUrl.replace('http', 'ws') + `/api/public/agents/${this.config.agent_id}/voice`;
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            this.ws?.send(JSON.stringify({ type: 'start', session_id: getSessionId() }));
        };

        this.ws.onmessage = async (e) => {
            const data = JSON.parse(e.data);
            if (data.type === 'session_ready') {
                this.mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
                this.mediaRecorder.ondataavailable = (e) => {
                    if (e.data.size > 0 && this.ws?.readyState === WebSocket.OPEN) {
                        const reader = new FileReader();
                        reader.readAsDataURL(e.data);
                        reader.onloadend = () => {
                            const base64 = (reader.result as string).split(',')[1];
                            this.ws?.send(JSON.stringify({ type: 'audio_data', audio: base64 }));
                        };
                    }
                };
                this.mediaRecorder.start(500); // 500ms chunks
            } else if (data.type === 'transcript') {
                onTranscript(data.text);
            } else if (data.type === 'response_start') {
                onThinking();
                // Stop recording while answering for MVP, half-duplex
                if (this.mediaRecorder && this.mediaRecorder.state === 'recording') {
                    this.mediaRecorder.stop();
                }
            } else if (data.type === 'audio_response') {
                // Play audio bytes
                await this.playAudioBase64(data.audio);
            } else if (data.type === 'response_complete') {
                onComplete();
                this.stopVoiceSession();
            } else if (data.type === 'error') {
                onError(data.message);
                this.stopVoiceSession();
            }
        };

        this.ws.onclose = () => {
            this.stopVoiceSession();
        };
    }

    private async playAudioBase64(base64: string) {
        if (!this.audioContext) {
            this.audioContext = new AudioContext();
        }
        
        try {
            const binaryString = window.atob(base64);
            const len = binaryString.length;
            const bytes = new Uint8Array(len);
            for (let i = 0; i < len; i++) {
                bytes[i] = binaryString.charCodeAt(i);
            }
            
            const buffer = await this.audioContext.decodeAudioData(bytes.buffer);
            const source = this.audioContext.createBufferSource();
            source.buffer = buffer;
            source.connect(this.audioContext.destination);
            source.start(0);
        } catch (e) {
            console.error("Audio playback error", e);
        }
    }

    public stopVoiceSession() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
            this.mediaRecorder.stream.getTracks().forEach(t => t.stop());
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
