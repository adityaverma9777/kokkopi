import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Enum as SQLEnum, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from pgvector.sqlalchemy import Vector
from .database import Base

def generate_uuid():
    return str(uuid.uuid4())

def generate_public_id(prefix: str):
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    memberships = relationship("TenantMember", back_populates="user")


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    members = relationship("TenantMember", back_populates="tenant")
    agents = relationship("Agent", back_populates="tenant")
    credentials = relationship("ProviderCredential", back_populates="tenant")


class TenantMember(Base):
    __tablename__ = "tenant_members"

    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    role = Column(String(50), nullable=False, default="member") # owner, admin, member

    user = relationship("User", back_populates="memberships")
    tenant = relationship("Tenant", back_populates="members")


class ProviderCredential(Base):
    __tablename__ = "provider_credentials"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False) # e.g. "groq"
    encrypted_secret = Column(String, nullable=False) # MUST NEVER LEAK
    key_last4 = Column(String(4))
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="credentials")

    def __repr__(self):
        # Defend against accidental leakage in logs/repr
        return f"<ProviderCredential id={self.id} tenant_id={self.tenant_id} provider={self.provider}>"


class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    tenant_id = Column(UUID(as_uuid=False), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    public_id = Column(String(50), unique=True, index=True, nullable=False, default=lambda: generate_public_id("agt"))
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False, default="chat_voice") # chat, voice, chat_voice
    status = Column(String(50), default="draft")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    tenant = relationship("Tenant", back_populates="agents")
    settings = relationship("AgentSetting", back_populates="agent", uselist=False, cascade="all, delete-orphan")
    
    # Phase 3 relationships prepared
    document_chunks = relationship("DocumentChunk", back_populates="agent", cascade="all, delete-orphan")


class AgentSetting(Base):
    __tablename__ = "agent_settings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id", ondelete="CASCADE"), unique=True, nullable=False)
    greeting = Column(String, nullable=True)
    theme = Column(String(50), nullable=True)
    color = Column(String(50), nullable=True)
    position = Column(String(50), nullable=True)
    language = Column(String(50), nullable=True)
    voice_id = Column(String(100), nullable=True)
    response_style = Column(String(100), nullable=True)

    agent = relationship("Agent", back_populates="settings")


# ---------------------------------------------------------
# Phase 3: Knowledge Ingestion Models
# ---------------------------------------------------------

class Source(Base):
    __tablename__ = "sources"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False, index=True)
    source_type = Column(String(50), nullable=False) # webpage, sitemap, pdf
    canonical_url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    content_type = Column(String(100), nullable=True)
    status = Column(String(50), default="discovered")
    content_hash = Column(String, nullable=True)
    last_crawled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent")
    documents = relationship("Document", back_populates="source", cascade="all, delete-orphan")


class CrawlJob(Base):
    __tablename__ = "crawl_jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), default="queued") # queued, discovering, crawling, processing, indexing, completed, failed, cancelled
    source_url = Column(String, nullable=False)
    
    total_discovered = Column(Integer, default=0)
    total_processed = Column(Integer, default=0)
    total_failed = Column(Integer, default=0)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent")


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    source_id = Column(UUID(as_uuid=False), ForeignKey("sources.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    language = Column(String(50), nullable=True)
    content_hash = Column(String, nullable=False)
    metadata_json = Column(JSON, default=dict)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent")
    source = relationship("Source", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """
    Retrieval-ready semantic content with pgvector embeddings.
    """
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=False), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    token_count = Column(Integer, nullable=True)
    metadata_json = Column(JSON, default=dict)
    
    # 384 dimensions for all-MiniLM-L6-v2
    embedding = Column(Vector(384))
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent", overlaps="document_chunks")
    document = relationship("Document", back_populates="chunks")


class BusinessProfile(Base):
    __tablename__ = "business_profiles"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, unique=True)

    business_name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    industry = Column(String, nullable=True)

    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)

    address = Column(String, nullable=True)
    locations = Column(JSON, default=list) # Array of locations

    hours = Column(JSON, default=list)

    products = Column(JSON, default=list)
    services = Column(JSON, default=list)

    faqs = Column(JSON, default=list)
    policies = Column(JSON, default=list)

    booking_links = Column(JSON, default=list)
    social_links = Column(JSON, default=list)

    raw_structured_data = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    agent_id = Column(UUID(as_uuid=False), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String, nullable=False, index=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    agent = relationship("Agent")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    conversation_id = Column(UUID(as_uuid=False), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String, nullable=False) # 'user' or 'assistant'
    content = Column(Text, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")
