from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from auth.dependencies import get_current_tenant
from voice.pipeline.speaker_clone import extract_and_save_reference
from voice.pipeline.audio_dsp import list_effect_presets
from voice.pipeline.asr import is_available as asr_available
from voice.adapters.kokoro_tts import VOICE_CATALOG, voices_for_language

logger = logging.getLogger("kokkopi.api.voice")

router = APIRouter(prefix="/api/voice", tags=["voice"])


class PronunciationEntry(BaseModel):
    term: str
    replacement: str


class PronunciationUpdate(BaseModel):
    entries: list[PronunciationEntry]


@router.get("/gallery")
async def get_voice_gallery(
    language: Optional[str] = None,
    gender: Optional[str] = None,
    tenant=Depends(get_current_tenant),
):
    """Return the full gallery of built-in Kokoro voices.

    Optional filters:
      - language: filter by lang_code (e.g. 'en-us', 'es-es', 'ja')
      - gender: filter by 'male' or 'female'
    """
    voices = VOICE_CATALOG
    if language:
        voices = [v for v in voices if v["lang_code"] == language or v["lang_code"].split("-")[0] == language.split("-")[0]]
    if gender:
        voices = [v for v in voices if v.get("gender") == gender]
    return {
        "voices": voices,
        "total": len(voices),
        "languages": sorted({v["lang_code"] for v in VOICE_CATALOG}),
    }


@router.get("/gallery/{voice_id}/preview")
async def preview_voice(
    voice_id: str,
    text: str = "Hello! I'm here to help you with any questions about this business.",
    tenant=Depends(get_current_tenant),
):
    """Generate a short WAV preview for a gallery voice using Kokoro TTS."""
    from voice.adapters.kokoro_tts import get_voice, synthesize as kokoro_synthesize, _is_kokoro_available
    from fastapi.responses import Response

    voice_meta = get_voice(voice_id)
    if not voice_meta:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found.")

    ok, msg = _is_kokoro_available()
    if not ok:
        raise HTTPException(status_code=503, detail=f"TTS engine unavailable: {msg}")

    preview_text = voice_meta.get("preview_text") or text
    try:
        audio_bytes = await kokoro_synthesize(preview_text, voice_id, language=voice_meta.get("lang_code", "en-us"))
        if not audio_bytes:
            raise HTTPException(status_code=503, detail="TTS synthesis returned empty audio.")
        return Response(content=audio_bytes, media_type="audio/wav")
    except HTTPException:
        raise
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
