---
title: Kokkopi Backend
emoji: 🐓
colorFrom: red
colorTo: yellow
sdk: docker
pinned: true
license: proprietary
app_port: 7860
---

# Kokkopi Backend

FastAPI backend for the Kokkopi AI Agent SaaS platform.

## Environment Variables (set via HF Spaces Secrets)

| Variable | Required | Description |
|---|---|---|
| `KOKKOPI_DATABASE_URL` | ✅ | PostgreSQL connection string (Supabase/Neon) |
| `KOKKOPI_JWT_SECRET` | ✅ | Secret for signing JWT tokens |
| `KOKKOPI_ENCRYPTION_KEY` | ✅ | Fernet key for encrypting Groq API keys at rest |
| `KOKKOPI_ALLOWED_ORIGINS` | ✅ | Comma-separated list of allowed CORS origins (e.g. `https://kokkopi.vercel.app`) |
| `REDIS_URL` | ✅ | Redis connection URL (Upstash or Railway) |
| `KOKKOPI_ASR_MODEL` | ⚙️ | Whisper model size: `tiny`, `base`, `small`, `medium`, `large-v3` (default: `small`) |
| `KOKKOPI_VRAM_BUDGET_MB` | ⚙️ | VRAM budget in MB (default: `6000`) |
| `KOKKOPI_TEXT_NORMALIZATION` | ⚙️ | Set to `0` to disable text normalization |
| `KOKKOPI_VOICE_PROFILES_DIR` | ⚙️ | Path to store cloned voice WAV files (default: `/tmp/kokkopi_voice_profiles`) |
