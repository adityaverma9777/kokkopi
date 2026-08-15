from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from backend.voice.service import voice_service
from backend.api.routers import auth, providers, agents, ingestion, public
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("kokkopi")

app = FastAPI(title="Kokkopi Backend API", description="B2B AI Agent SaaS API")

app.include_router(auth.router)
app.include_router(providers.router)
app.include_router(agents.router)
app.include_router(ingestion.router)
app.include_router(public.router)

class SynthesizeRequest(BaseModel):
    text: str
    voice_id: str = "vstudio_default"

@app.get("/api/health")
async def health_check():
    voice_health = await voice_service.health()
    return {"status": "ok", "voice_backend": voice_health}

@app.post("/api/voice/test")
async def test_synthesize(req: SynthesizeRequest):
    try:
        logger.info(f"Synthesizing text: '{req.text}' using voice: '{req.voice_id}'")
        audio_bytes = await voice_service.synthesize(req.text, req.voice_id)
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
