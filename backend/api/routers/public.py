import json
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.database import get_db
from db.models import Agent, AgentSetting, Conversation, Message
from agent.runtime import AgentRuntime
from voice.service import voice_service
from .rate_limiter import check_rate_limit

router = APIRouter(prefix="/api/public/agents", tags=["public"])

class ChatRequest(BaseModel):
    message: str
    session_id: str

async def _resolve_active_agent(public_agent_id: str, db: AsyncSession) -> tuple[Agent, AgentSetting]:
    result = await db.execute(select(Agent).where(Agent.public_id == public_agent_id))
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")
    
    # In MVP, assume agent is active if it's not explicitly disabled, or we require 'active'.
    if agent.status != 'active':
        raise HTTPException(status_code=403, detail="This assistant is currently unavailable.")
        
    settings_res = await db.execute(select(AgentSetting).where(AgentSetting.agent_id == str(agent.id)))
    settings = settings_res.scalars().first()
    
    return agent, settings

async def _get_or_create_conversation(agent_id: str, session_id: str, db: AsyncSession) -> Conversation:
    res = await db.execute(select(Conversation).where(
        Conversation.agent_id == agent_id,
        Conversation.session_id == session_id
    ))
    conv = res.scalars().first()
    if not conv:
        conv = Conversation(agent_id=agent_id, session_id=session_id)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
    return conv

async def _get_history(conversation_id: str, db: AsyncSession) -> List[dict]:
    res = await db.execute(select(Message).where(Message.conversation_id == str(conversation_id)).order_by(Message.created_at.asc()))
    msgs = res.scalars().all()
    return [{"role": m.role, "content": m.content} for m in msgs[-10:]] # bounded to last 10

@router.get("/{public_agent_id}/config")
async def get_config(public_agent_id: str, session_id: str, db: AsyncSession = Depends(get_db)):
    check_rate_limit("config", public_agent_id, session_id, max_requests=20, window_seconds=60)
    agent, settings = await _resolve_active_agent(public_agent_id, db)
    
    return {
        "agent_id": public_agent_id,
        "name": agent.name,
        "theme": "light",
        "primary_color": "#000000",
        "position": "bottom-right",
        "greeting": settings.greeting if settings else "Hi! How can I help?",
        "voice_enabled": True
    }

@router.post("/{public_agent_id}/chat/stream")
async def chat_stream(public_agent_id: str, req: ChatRequest, db: AsyncSession = Depends(get_db)):
    check_rate_limit("chat", public_agent_id, req.session_id, max_requests=10, window_seconds=60)
    
    agent, settings = await _resolve_active_agent(public_agent_id, db)
    conv = await _get_or_create_conversation(str(agent.id), req.session_id, db)
    
    # Save user message
    user_msg = Message(conversation_id=str(conv.id), role="user", content=req.message)
    db.add(user_msg)
    await db.commit()
    
    history = await _get_history(str(conv.id), db)
    
    runtime = AgentRuntime(db)
    
    async def event_stream():
        full_response = ""
        try:
            async for token in runtime.stream(str(agent.id), req.message, history=history):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"
            
            # Save assistant message
            ast_msg = Message(conversation_id=str(conv.id), role="assistant", content=full_response)
            db.add(ast_msg)
            await db.commit()
            
            yield f"data: [DONE]\n\n"
        except Exception as e:
            # We must not expose raw errors. Return safe message.
            err = "I am currently unable to answer due to a technical issue."
            yield f"data: {json.dumps({'error': err})}\n\n"
            yield f"data: [DONE]\n\n"
            
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@router.websocket("/{public_agent_id}/voice")
async def voice_websocket(websocket: WebSocket, public_agent_id: str, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    
    try:
        agent, settings = await _resolve_active_agent(public_agent_id, db)
    except Exception:
        await websocket.send_json({"type": "error", "message": "Agent unavailable."})
        await websocket.close()
        return

    session_id = None
    conv = None
    runtime = AgentRuntime(db)
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            if msg["type"] == "start":
                session_id = msg["session_id"]
                check_rate_limit("voice", public_agent_id, session_id, max_requests=10, window_seconds=60)
                conv = await _get_or_create_conversation(str(agent.id), session_id, db)
                await websocket.send_json({"type": "session_ready"})
                
            elif msg["type"] == "audio_data":
                if not session_id:
                    continue
                # In MVP, client might send base64 or binary. Assuming base64 text for simplicity.
                import base64
                audio_bytes = base64.b64decode(msg["audio"])
                
                # 1. Transcribe
                transcript = await voice_service.transcribe(audio_bytes)
                if not transcript.strip():
                    continue
                    
                await websocket.send_json({"type": "transcript", "text": transcript})
                
                # Save user message
                user_msg = Message(conversation_id=str(conv.id), role="user", content=transcript)
                db.add(user_msg)
                await db.commit()
                
                history = await _get_history(str(conv.id), db)
                
                # 2. Get Agent Response
                await websocket.send_json({"type": "response_start"})
                response = await runtime.respond(str(agent.id), transcript, history=history)
                
                # Save assistant message
                ast_msg = Message(conversation_id=str(conv.id), role="assistant", content=response.text)
                db.add(ast_msg)
                await db.commit()
                
                # 3. TTS Stream
                async for chunk in voice_service.stream_synthesize(response.text, voice_id="default"):
                    # Send as base64
                    await websocket.send_json({
                        "type": "audio_response",
                        "audio": base64.b64encode(chunk).decode('utf-8')
                    })
                    
                await websocket.send_json({"type": "response_complete"})
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "message": "An error occurred."})
        except Exception:
            pass
