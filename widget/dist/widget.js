(()=>{function f(){let c=sessionStorage.getItem("kokkopi_session");return c||(c="sess_"+Math.random().toString(36).substr(2,9),sessionStorage.setItem("kokkopi_session",c)),c}var b=class{baseUrl;config;ws=null;mediaRecorder=null;audioContext=null;constructor(s,n){this.baseUrl=s,this.config=n}async streamChat(s,n,d,i){try{let e=await fetch(`${this.baseUrl}/api/public/agents/${this.config.agent_id}/chat/stream`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:s,session_id:f()})});if(!e.ok){i("Failed to connect to agent.");return}let t=e.body?.getReader(),o=new TextDecoder("utf-8");if(!t)return;for(;;){let{done:a,value:h}=await t.read();if(a)break;let r=o.decode(h,{stream:!0}).split(`
`);for(let l of r)if(l.startsWith("data: ")){let p=l.slice(6);if(p==="[DONE]"){d();return}try{let u=JSON.parse(p);if(u.error){i(u.error);return}u.token&&n(u.token)}catch{}}}d()}catch{i("Connection error.")}}async startVoiceSession(s,n,d,i){this.stopVoiceSession();let e;try{e=await navigator.mediaDevices.getUserMedia({audio:!0})}catch{i("Microphone access denied.");return}let t=this.baseUrl.replace("http","ws")+`/api/public/agents/${this.config.agent_id}/voice`;this.ws=new WebSocket(t),this.ws.onopen=()=>{this.ws?.send(JSON.stringify({type:"start",session_id:f()}))},this.ws.onmessage=async o=>{let a=JSON.parse(o.data);a.type==="session_ready"?(this.mediaRecorder=new MediaRecorder(e,{mimeType:"audio/webm"}),this.mediaRecorder.ondataavailable=h=>{if(h.data.size>0&&this.ws?.readyState===WebSocket.OPEN){let g=new FileReader;g.readAsDataURL(h.data),g.onloadend=()=>{let r=g.result.split(",")[1];this.ws?.send(JSON.stringify({type:"audio_data",audio:r}))}}},this.mediaRecorder.start(500)):a.type==="transcript"?s(a.text):a.type==="response_start"?(n(),this.mediaRecorder&&this.mediaRecorder.state==="recording"&&this.mediaRecorder.stop()):a.type==="audio_response"?await this.playAudioBase64(a.audio):a.type==="response_complete"?(d(),this.stopVoiceSession()):a.type==="error"&&(i(a.message),this.stopVoiceSession())},this.ws.onclose=()=>{this.stopVoiceSession()}}async playAudioBase64(s){this.audioContext||(this.audioContext=new AudioContext);try{let n=window.atob(s),d=n.length,i=new Uint8Array(d);for(let o=0;o<d;o++)i[o]=n.charCodeAt(o);let e=await this.audioContext.decodeAudioData(i.buffer),t=this.audioContext.createBufferSource();t.buffer=e,t.connect(this.audioContext.destination),t.start(0)}catch(n){console.error("Audio playback error",n)}}stopVoiceSession(){this.mediaRecorder&&this.mediaRecorder.state!=="inactive"&&(this.mediaRecorder.stop(),this.mediaRecorder.stream.getTracks().forEach(s=>s.stop())),this.ws&&(this.ws.close(),this.ws=null)}};var m=class{config;client;root;shadow;isOpen=!1;constructor(s,n){this.config=s,this.client=n,this.root=document.createElement("div"),this.root.id="kokkopi-widget-root",document.body.appendChild(this.root),this.shadow=this.root.attachShadow({mode:"closed"})}render(){this.shadow.innerHTML=`
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
                    background: ${this.config.primary_color||"#000"};
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
                    background: ${this.config.primary_color||"#000"};
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
                    background: ${this.config.primary_color||"#000"};
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
                    border-color: ${this.config.primary_color||"#000"};
                }

                .action-btn {
                    background: ${this.config.primary_color||"#000"};
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
            
            <button id="launcher">\u{1F4AC}</button>
            
            <div id="chat-window">
                <div id="chat-header">
                    <span>${this.config.name||"Assistant"}</span>
                    <button id="close-btn">\xD7</button>
                </div>
                <div id="messages">
                    <div class="msg msg-assistant">${this.config.greeting}</div>
                </div>
                <div id="input-area">
                    <input type="text" id="chat-input" placeholder="Type a message..." />
                    <button id="send-btn" class="action-btn">\u2794</button>
                    ${this.config.voice_enabled?'<button id="voice-btn" class="action-btn">\u{1F3A4}</button>':""}
                </div>
            </div>
        `,this.attachEvents()}attachEvents(){let s=this.shadow.getElementById("launcher"),n=this.shadow.getElementById("chat-window"),d=this.shadow.getElementById("close-btn"),i=this.shadow.getElementById("send-btn"),e=this.shadow.getElementById("chat-input"),t=this.shadow.getElementById("voice-btn"),o=this.shadow.getElementById("messages"),a=()=>{this.isOpen=!this.isOpen,n.style.display=this.isOpen?"flex":"none",s.style.display=this.isOpen?"none":"flex"};s.addEventListener("click",a),d.addEventListener("click",a);let h=(r,l)=>{let p=document.createElement("div");return p.className=`msg msg-${r}`,p.textContent=l,o.appendChild(p),o.scrollTop=o.scrollHeight,p},g=async()=>{let r=e.value.trim();if(!r)return;e.value="",e.disabled=!0,i.disabled=!0,t&&(t.disabled=!0),h("user",r);let l=h("assistant","");await this.client.streamChat(r,p=>{l.textContent+=p,o.scrollTop=o.scrollHeight},()=>{e.disabled=!1,i.disabled=!1,t&&(t.disabled=!1),e.focus()},p=>{l.textContent=p,e.disabled=!1,i.disabled=!1,t&&(t.disabled=!1)})};i.addEventListener("click",g),e.addEventListener("keypress",r=>{r.key==="Enter"&&g()}),t&&t.addEventListener("click",async()=>{let r=h("assistant","\u{1F3A4} Listening...");e.disabled=!0,i.disabled=!0,t.disabled=!0,await this.client.startVoiceSession(l=>{h("user",l)},()=>{r.textContent="Thinking..."},()=>{r.textContent="Done.",e.disabled=!1,i.disabled=!1,t.disabled=!1},l=>{r.textContent=l,e.disabled=!1,i.disabled=!1,t.disabled=!1})})}};async function w(){let c=document.getElementsByTagName("script"),s=c[c.length-1];for(let e=0;e<c.length;e++)if(c[e].getAttribute("data-agent")){s=c[e];break}let n=s.getAttribute("data-agent");if(!n){console.error("Kokkopi Widget: Missing data-agent attribute on script tag.");return}let d="",i=s.getAttribute("src");if(i&&i.startsWith("http")){let e=new URL(i);d=`${e.protocol}//${e.host}`}else d="http://127.0.0.1:8000";try{let e=f(),t=await fetch(`${d}/api/public/agents/${n}/config?session_id=${e}`);if(!t.ok){console.warn("Kokkopi Widget: Agent is unavailable or invalid.");return}let o=await t.json(),a=new b(d,o);new m(o,a).render()}catch(e){console.warn("Kokkopi Widget: Failed to load configuration.",e)}}document.readyState==="loading"?document.addEventListener("DOMContentLoaded",w):w();})();
//# sourceMappingURL=widget.js.map
