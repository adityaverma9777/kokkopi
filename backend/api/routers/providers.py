import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.database import get_db
from db.models import Tenant, ProviderCredential
from auth.dependencies import get_current_tenant
from auth.encryption import encrypt_secret

router = APIRouter(prefix="/api/providers", tags=["providers"])

class GroqKeySubmit(BaseModel):
    api_key: str

class ProviderStatus(BaseModel):
    provider: str
    status: str
    key_last4: str | None = None

async def _verify_groq_key(api_key: str) -> bool:
    """Actually calls Groq to verify the key."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=5.0
            )
            return response.status_code == 200
    except Exception:
        return False

@router.post("/groq/verify")
async def verify_groq(submit: GroqKeySubmit):
    is_valid = await _verify_groq_key(submit.api_key)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Groq API key")
    return {"status": "valid"}

@router.post("/groq")
async def save_groq(submit: GroqKeySubmit, tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    is_valid = await _verify_groq_key(submit.api_key)
    if not is_valid:
        raise HTTPException(status_code=400, detail="Invalid Groq API key")

    # Check if a credential already exists for this tenant
    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.tenant_id == tenant.id, ProviderCredential.provider == "groq")
    )
    cred = result.scalars().first()

    encrypted = encrypt_secret(submit.api_key)
    last4 = submit.api_key[-4:] if len(submit.api_key) >= 4 else "****"

    if cred:
        cred.encrypted_secret = encrypted
        cred.key_last4 = last4
        cred.status = "active"
    else:
        cred = ProviderCredential(
            tenant_id=tenant.id,
            provider="groq",
            encrypted_secret=encrypted,
            key_last4=last4
        )
        db.add(cred)

    await db.commit()
    return {"status": "saved", "key_last4": last4}

@router.get("/groq/status", response_model=ProviderStatus)
async def get_groq_status(tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.tenant_id == tenant.id, ProviderCredential.provider == "groq")
    )
    cred = result.scalars().first()
    
    if not cred:
        return ProviderStatus(provider="groq", status="missing")
        
    return ProviderStatus(provider="groq", status=cred.status, key_last4=cred.key_last4)

@router.delete("/groq")
async def delete_groq(tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProviderCredential)
        .where(ProviderCredential.tenant_id == tenant.id, ProviderCredential.provider == "groq")
    )
    cred = result.scalars().first()
    
    if cred:
        await db.delete(cred)
        await db.commit()
        
    return {"status": "deleted"}
