from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.database import get_db
from db.models import Tenant, Agent, AgentSetting
from auth.dependencies import get_current_tenant

router = APIRouter(prefix="/api/agents", tags=["agents"])

class AgentSettingBase(BaseModel):
    greeting: str | None = None
    theme: str | None = None
    color: str | None = None
    position: str | None = None
    language: str | None = None
    voice_id: str | None = None
    response_style: str | None = None

class AgentCreate(BaseModel):
    name: str
    type: str = "chat_voice"

class AgentResponse(BaseModel):
    id: str
    public_id: str
    name: str
    type: str
    status: str
    settings: AgentSettingBase | None = None

@router.post("", response_model=AgentResponse)
async def create_agent(agent_in: AgentCreate, tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    new_agent = Agent(
        tenant_id=tenant.id,
        name=agent_in.name,
        type=agent_in.type
    )
    db.add(new_agent)
    await db.flush() # To get the agent ID

    # Create empty settings
    settings = AgentSetting(agent_id=new_agent.id)
    db.add(settings)
    await db.commit()
    
    return AgentResponse(
        id=str(new_agent.id),
        public_id=new_agent.public_id,
        name=new_agent.name,
        type=new_agent.type,
        status=new_agent.status,
        settings=AgentSettingBase()
    )

@router.get("", response_model=List[AgentResponse])
async def list_agents(tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(Agent.tenant_id == tenant.id)
    )
    agents = result.scalars().all()
    
    responses = []
    for agent in agents:
        # Note: In a real app we would join settings or load them
        result_set = await db.execute(select(AgentSetting).where(AgentSetting.agent_id == agent.id))
        setting = result_set.scalars().first()
        setting_base = None
        if setting:
            setting_base = AgentSettingBase(
                greeting=setting.greeting,
                theme=setting.theme,
                color=setting.color,
                position=setting.position,
                language=setting.language,
                voice_id=setting.voice_id,
                response_style=setting.response_style
            )
        
        responses.append(AgentResponse(
            id=str(agent.id),
            public_id=agent.public_id,
            name=agent.name,
            type=agent.type,
            status=agent.status,
            settings=setting_base
        ))
    return responses

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, tenant: Tenant = Depends(get_current_tenant), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id, Agent.tenant_id == tenant.id)
    )
    agent = result.scalars().first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    result_set = await db.execute(select(AgentSetting).where(AgentSetting.agent_id == agent.id))
    setting = result_set.scalars().first()
    setting_base = None
    if setting:
        setting_base = AgentSettingBase(
            greeting=setting.greeting,
            theme=setting.theme,
            color=setting.color,
            position=setting.position,
            language=setting.language,
            voice_id=setting.voice_id,
            response_style=setting.response_style
        )
        
    return AgentResponse(
        id=str(agent.id),
        public_id=agent.public_id,
        name=agent.name,
        type=agent.type,
        status=agent.status,
        settings=setting_base
    )
