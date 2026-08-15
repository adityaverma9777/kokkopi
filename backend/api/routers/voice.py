"""Voice API routes — gallery, preview, cloning, and pronunciation.

All routes require authentication and are tenant-scoped. The cloning
endpoints enforce explicit consent before processing any audio.
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from auth.dependencies import get_current_tenant
from voice.pipeline.speaker_clone import extract_and_save_reference, list_builtin_voices
from voice.pipeline.audio_dsp import list_effect_presets
from voice.pipeline.asr import is_available as asr_available

logger = logging.getLogger("kokkopi.api.voice")

router = APIRouter(prefix="/api/voice", tags=["voice"])


class PronunciationEntry(BaseModel):
    term: str
    replacement: str


class PronunciationUpdate(BaseModel):
    entries: list[PronunciationEntry]


@router.get("/gallery")
async def get_voice_gallery(
    tenant=Depends(get_current_tenant),
):
    """Return the full gallery of built-in voices available for selection."""
    return {
        "voices": list_builtin_voices(),
        "total": len(list_builtin_voices()),
    }


@router.get("/gallery/{voice_id}/preview")
async def preview_voice(
    voice_id: str,
    text: str = "Hello! I'm here to help you with any questions about this business.",
    tenant=Depends(get_current_tenant),
):
    """Generate a short audio preview for a gallery voice.

    Returns synthesized audio as WAV bytes. This hits the real TTS engine
    so the user hears exactly what their customers will hear.
    """
    voices = {v["id"]: v for v in list_builtin_voices()}
    if voice_id not in voices:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found.")

    from voice.service import VoiceService
    from fastapi.responses import Response

    try:
        service = VoiceService()
        audio_bytes = await service.synthesize(text, voice_id=voice_id)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        logger.error("Preview generation failed for voice %s: %s", voice_id, e)
        raise HTTPException(status_code=503, detail="TTS service unavailable.")


@router.post("/clone")
async def clone_voice(
    agent_id: str = Form(...),
    profile_name: str = Form(...),
    consent_confirmed: bool = Form(...),
    audio: UploadFile = File(...),
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Clone a voice from an uploaded audio sample.

    Enforces explicit consent. Stores the resulting VoiceProfile
    in the database tied to the given agent and tenant.

    The UI must display the consent checkbox and not submit without it.
    """
    if not consent_confirmed:
        raise HTTPException(
            status_code=400,
            detail="Voice cloning requires explicit consent. You must confirm that you own or have authorization to use this voice.",
        )

    allowed_types = {"audio/wav", "audio/webm", "audio/mp4", "audio/mpeg", "audio/ogg", "audio/flac"}
    if audio.content_type and audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {audio.content_type}. Please upload WAV, WebM, MP4, MP3, OGG, or FLAC.",
        )

    audio_bytes = await audio.read()
    if len(audio_bytes) > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio file too large. Maximum is 50 MB.")

    result = await extract_and_save_reference(
        audio_bytes,
        agent_id=agent_id,
        tenant_id=str(tenant.id),
        profile_name=profile_name,
        consent_confirmed=consent_confirmed,
    )

    if result["status"] != "ok":
        raise HTTPException(
            status_code=422,
            detail={
                "status": result["status"],
                "message": result["message"],
                "duration_s": result.get("duration_s"),
            },
        )

    return {
        "profile_id": result["profile_id"],
        "duration_s": result["duration_s"],
        "message": result["message"],
        "status": "created",
    }


@router.get("/effects")
async def get_effect_presets(tenant=Depends(get_current_tenant)):
    """Return available DSP effect presets for the customize screen."""
    return {"presets": list_effect_presets()}


@router.get("/agents/{agent_id}/pronunciation")
async def get_pronunciation(
    agent_id: str,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Get the pronunciation dictionary for an agent."""
    from db.models import Agent, AgentSetting
    from sqlalchemy import select

    result = await db.execute(
        select(AgentSetting).where(
            AgentSetting.agent_id == agent_id,
            AgentSetting.key == "pronunciation_lexicon",
        )
    )
    setting = result.scalar_one_or_none()
    if not setting:
        return {"entries": []}

    import json
    try:
        lexicon = json.loads(setting.value)
        entries = [{"term": k, "replacement": v} for k, v in lexicon.items()]
        return {"entries": entries}
    except Exception:
        return {"entries": []}


@router.put("/agents/{agent_id}/pronunciation")
async def update_pronunciation(
    agent_id: str,
    payload: PronunciationUpdate,
    tenant=Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
):
    """Update the pronunciation dictionary for an agent."""
    from db.models import Agent, AgentSetting
    from sqlalchemy import select
    import json

    agent_result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant.id)
    )
    agent = agent_result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found.")

    lexicon = {e.term: e.replacement for e in payload.entries if e.term.strip()}

    result = await db.execute(
        select(AgentSetting).where(
            AgentSetting.agent_id == agent_id,
            AgentSetting.key == "pronunciation_lexicon",
        )
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.value = json.dumps(lexicon, ensure_ascii=False)
    else:
        setting = AgentSetting(
            agent_id=agent_id,
            key="pronunciation_lexicon",
            value=json.dumps(lexicon, ensure_ascii=False),
        )
        db.add(setting)

    await db.commit()
    return {"status": "updated", "entries": len(lexicon)}


@router.get("/system/status")
async def voice_system_status(tenant=Depends(get_current_tenant)):
    """Return the health status of ASR, TTS, and loaded models."""
    from voice.pipeline.model_lifecycle import registry

    asr_ok, asr_msg = asr_available()

    return {
        "asr": {"available": asr_ok, "message": asr_msg},
        "models": registry.status(),
        "vram_used_mb": registry.total_vram_used_mb,
    }
