from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.database import get_db
from db.models import User, Tenant, TenantMember
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
        
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    
    if user is None:
        raise credentials_exception
        
    return user

async def get_current_tenant(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_db),
    # Optional header if user has multiple tenants, but default to first for MVP
    x_tenant_id: str = Header(None) 
) -> Tenant:
    # Get all memberships for user
    result = await db.execute(
        select(TenantMember).where(TenantMember.user_id == current_user.id)
    )
    memberships = result.scalars().all()
    
    if not memberships:
        raise HTTPException(status_code=403, detail="User does not belong to any tenant")
        
    if x_tenant_id:
        # Validate the requested tenant
        valid_membership = next((m for m in memberships if str(m.tenant_id) == x_tenant_id), None)
        if not valid_membership:
            raise HTTPException(status_code=403, detail="Not a member of this tenant")
        tenant_id = x_tenant_id
    else:
        # Default to the first tenant
        tenant_id = memberships[0].tenant_id

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalars().first()
    
    if tenant is None:
        raise HTTPException(status_code=403, detail="Tenant not found")
        
    return tenant
