import { WidgetConfig } from './config';
import { KokkopiClient } from './client';

export class KokkopiUI {
    private config: WidgetConfig;
    private client: KokkopiClient;
    private root: HTMLElement;
    private shadow: ShadowRoot;

    private isOpen = false;

    constructor(config: WidgetConfig, client: KokkopiClient) {
        this.config = config;
        this.client = client;
        
        this.root = document.createElement('div');
        this.root.id = 'kokkopi-widget-root';
        document.body.appendChild(this.root);
        
        // Shadow DOM for complete CSS isolation
        this.shadow = this.root.attachShadow({ mode: 'closed' });
    }

    public render() {
        this.shadow.innerHTML = `
            <style>
                :host {
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    z-index: 999999;
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                }
                
                #launcher {
                    width: 60px;
                    height: 60px;
                    border-radius: 50%;
                    background: ${this.config.primary_color || '#000'};
                    color: white;
                    border: none;
                    cursor: pointer;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 24px;
                    transition: transform 0.2s;
                }
                
                #launcher:hover {
                    transform: scale(1.05);
                }

                #chat-window {
                    display: none;
                    position: absolute;
                    bottom: 80px;
                    right: 0;
                    width: 350px;
                    height: 500px;
                    max-height: calc(100vh - 100px);
                    background: white;
                    border-radius: 12px;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
                    flex-direction: column;
                    overflow: hidden;
                    border: 1px solid #eee;
                }

                #chat-header {
                    background: ${this.config.primary_color || '#000'};
                    color: white;
                    padding: 16px;
                    font-weight: 600;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }

                #close-btn {
                    background: transparent;
                    border: none;
                    color: white;
                    cursor: pointer;
                    font-size: 20px;
                }

                #messages {
                    flex: 1;
                    padding: 16px;
                    overflow-y: auto;
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    background: #f9f9f9;
                }

                .msg {
                    padding: 10px 14px;
                    border-radius: 12px;
                    max-width: 85%;
                    line-height: 1.4;
                    font-size: 14px;
                }

                .msg-assistant {
                    background: white;
                    border: 1px solid #eee;
                    align-self: flex-start;
                    border-bottom-left-radius: 4px;
                }

                .msg-user {
                    background: ${this.config.primary_color || '#000'};
                    color: white;
                    align-self: flex-end;
                    border-bottom-right-radius: 4px;
                }

                #input-area {
                    padding: 12px;
                    background: white;
                    border-top: 1px solid #eee;
                    display: flex;
                    gap: 8px;
                }

                #chat-input {
                    flex: 1;
                    padding: 10px;
                    border: 1px solid #ddd;
                    border-radius: 20px;
                    outline: none;
                }

                #chat-input:focus {
                    border-color: ${this.config.primary_color || '#000'};
                }

                .action-btn {
                    background: ${this.config.primary_color || '#000'};
                    color: white;
                    border: none;
                    border-radius: 50%;
                    width: 38px;
                    height: 38px;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .action-btn:disabled {
                    background: #ccc;
                    cursor: not-allowed;
                }
            </style>
            
            <button id="launcher">💬</button>
            
            <div id="chat-window">
                <div id="chat-header">
                    <span>${this.config.name || 'Assistant'}</span>
                    <button id="close-btn">×</button>
                </div>
                <div id="messages">
                    <div class="msg msg-assistant">${this.config.greeting}</div>
                </div>
                <div id="input-area">
                    <input type="text" id="chat-input" placeholder="Type a message..." />
                    <button id="send-btn" class="action-btn">➔</button>
                    ${this.config.voice_enabled ? '<button id="voice-btn" class="action-btn">🎤</button>' : ''}
                </div>
            </div>
        `;

        this.attachEvents();
    }

    private attachEvents() {
        const launcher = this.shadow.getElementById('launcher')!;
        const chatWindow = this.shadow.getElementById('chat-window')!;
        const closeBtn = this.shadow.getElementById('close-btn')!;
        const sendBtn = this.shadow.getElementById('send-btn') as HTMLButtonElement;
        const chatInput = this.shadow.getElementById('chat-input') as HTMLInputElement;
        const voiceBtn = this.shadow.getElementById('voice-btn') as HTMLButtonElement | null;
        const messagesEl = this.shadow.getElementById('messages')!;

        const toggleChat = () => {
            this.isOpen = !this.isOpen;
            chatWindow.style.display = this.isOpen ? 'flex' : 'none';
            launcher.style.display = this.isOpen ? 'none' : 'flex';
        };

        launcher.addEventListener('click', toggleChat);
        closeBtn.addEventListener('click', toggleChat);

        const appendMessage = (role: 'user' | 'assistant', text: string): HTMLElement => {
            const div = document.createElement('div');
            div.className = `msg msg-${role}`;
            div.textContent = text;
            messagesEl.appendChild(div);
            messagesEl.scrollTop = messagesEl.scrollHeight;
            return div;
        };

        const sendMessage = async () => {
            const text = chatInput.value.trim();
            if (!text) return;
            
            chatInput.value = '';
            chatInput.disabled = true;
            sendBtn.disabled = true;
            if (voiceBtn) voiceBtn.disabled = true;

            appendMessage('user', text);
            const responseEl = appendMessage('assistant', '');

            await this.client.streamChat(
                text,
                (token) => {
                    responseEl.textContent += token;
                    messagesEl.scrollTop = messagesEl.scrollHeight;
                },
                () => {
                    chatInput.disabled = false;
                    sendBtn.disabled = false;
                    if (voiceBtn) voiceBtn.disabled = false;
                    chatInput.focus();
                },
                (err) => {
                    responseEl.textContent = err;
                    chatInput.disabled = false;
                    sendBtn.disabled = false;
                    if (voiceBtn) voiceBtn.disabled = false;
                }
            );
        };

        sendBtn.addEventListener('click', sendMessage);
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        if (voiceBtn) {
            voiceBtn.addEventListener('click', async () => {
                const responseEl = appendMessage('assistant', '🎤 Listening...');
                chatInput.disabled = true;
                sendBtn.disabled = true;
                voiceBtn.disabled = true;

                await this.client.startVoiceSession(
                    (transcript) => {
                        appendMessage('user', transcript);
                    },
                    () => {
                        responseEl.textContent = 'Thinking...';
                    },
                    () => {
                        responseEl.textContent = 'Done.';
                        chatInput.disabled = false;
                        sendBtn.disabled = false;
                        voiceBtn.disabled = false;
                    },
                    (err) => {
                        responseEl.textContent = err;
                        chatInput.disabled = false;
                        sendBtn.disabled = false;
                        voiceBtn.disabled = false;
                    }
                );
            });
        }
    }
}
