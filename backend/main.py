import os
import logging
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from voice.service import voice_service
from api.routers import auth, providers, agents, ingestion, public, voice
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kokkopi")

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("KOKKOPI_ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

app = FastAPI(title="Kokkopi API", description="Kokkopi B2B AI Agent SaaS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(agents.router)
app.include_router(ingestion.router)
app.include_router(public.router)
app.include_router(voice.router)

class SynthesizeRequest(BaseModel):
    text: str
    voice_id: str = "vstudio_default"

@app.get("/api/health")
async def health_check():
    from voice.pipeline.asr import is_available as asr_available
    from voice.pipeline.model_lifecycle import registry
    asr_ok, asr_msg = asr_available()
    voice_health = await voice_service.health()
    return {
        "status": "ok",
        "voice_backend": voice_health,
        "asr": {"available": asr_ok, "message": asr_msg},
        "models_loaded": len(registry.status()),
        "vram_used_mb": registry.total_vram_used_mb,
    }

@app.post("/api/voice/test")
async def test_synthesize(req: SynthesizeRequest):
    try:
        audio_bytes = await voice_service.synthesize(req.text, req.voice_id)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        logger.error("Synthesis failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)

