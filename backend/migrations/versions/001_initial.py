"""Initial tables

Revision ID: 001_initial
Revises: 
Create Date: 2026-08-15 10:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Ensure pgvector is installed in Postgres
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # users
    op.create_table('users',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # tenants
    op.create_table('tenants',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # tenant_members
    op.create_table('tenant_members',
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=False), sa.ForeignKey('tenants.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(length=50), nullable=False),
    )

    # provider_credentials
    op.create_table('provider_credentials',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=False), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('encrypted_secret', sa.String(), nullable=False),
        sa.Column('key_last4', sa.String(length=4), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_provider_credentials_tenant_id'), 'provider_credentials', ['tenant_id'], unique=False)

    # agents
    op.create_table('agents',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('tenant_id', UUID(as_uuid=False), sa.ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False),
        sa.Column('public_id', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_agents_tenant_id'), 'agents', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_agents_public_id'), 'agents', ['public_id'], unique=True)

    # agent_settings
    op.create_table('agent_settings',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=False), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('greeting', sa.String(), nullable=True),
        sa.Column('theme', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('position', sa.String(length=50), nullable=True),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('voice_id', sa.String(length=100), nullable=True),
        sa.Column('response_style', sa.String(length=100), nullable=True),
    )
    op.create_index(op.f('ix_agent_settings_agent_id'), 'agent_settings', ['agent_id'], unique=True)

    # sources
    op.create_table('sources',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=False), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('canonical_url', sa.String(), nullable=True),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('content_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=True),
        sa.Column('last_crawled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_sources_agent_id'), 'sources', ['agent_id'], unique=False)
    op.create_index(op.f('ix_sources_url'), 'sources', ['url'], unique=False)

    # crawl_jobs
    op.create_table('crawl_jobs',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=False), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('source_url', sa.String(), nullable=False),
        sa.Column('total_discovered', sa.Integer(), nullable=True),
        sa.Column('total_processed', sa.Integer(), nullable=True),
        sa.Column('total_failed', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_crawl_jobs_agent_id'), 'crawl_jobs', ['agent_id'], unique=False)

    # documents
    op.create_table('documents',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=False), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_id', UUID(as_uuid=False), sa.ForeignKey('sources.id', ondelete='CASCADE'), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=True),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('language', sa.String(length=50), nullable=True),
        sa.Column('content_hash', sa.String(), nullable=False),
        sa.Column('metadata_json', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_documents_agent_id'), 'documents', ['agent_id'], unique=False)
    op.create_index(op.f('ix_documents_source_id'), 'documents', ['source_id'], unique=False)

    # document_chunks
    op.create_table('document_chunks',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=False), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_id', UUID(as_uuid=False), sa.ForeignKey('documents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('metadata_json', JSON, nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_document_chunks_agent_id'), 'document_chunks', ['agent_id'], unique=False)
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)

    # business_profiles
    op.create_table('business_profiles',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('agent_id', UUID(as_uuid=False), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False),
        sa.Column('business_name', sa.String(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('industry', sa.String(), nullable=True),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('email', sa.String(), nullable=True),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('locations', JSON, nullable=True),
        sa.Column('hours', JSON, nullable=True),
        sa.Column('products', JSON, nullable=True),
        sa.Column('services', JSON, nullable=True),
        sa.Column('faqs', JSON, nullable=True),
        sa.Column('policies', JSON, nullable=True),
        sa.Column('booking_links', JSON, nullable=True),
        sa.Column('social_links', JSON, nullable=True),
        sa.Column('raw_structured_data', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_business_profiles_agent_id'), 'business_profiles', ['agent_id'], unique=True)


def downgrade() -> None:
    pass
