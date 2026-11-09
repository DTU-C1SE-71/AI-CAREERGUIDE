import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class KnowledgeEmbedding(Base):
    """
    Vector storage using PostgreSQL pgvector extension (1536 dimensions for text-embedding-3-small).
    Supports metadata-filtered retrieval by major_code and skill_id for LlamaIndex Dual RAG.
    """
    __tablename__ = "knowledge_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    major_code: Mapped[Optional[str]] = mapped_column(
        String(20), index=True, nullable=True,
        comment="Metadata filter for major-specific semantic queries"
    )
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True,
        comment="Metadata filter for skill-gap semantic queries"
    )
    chunk_text: Mapped[str] = mapped_column(
        Text, nullable=False,
        comment="Semantically chunked text from verified curriculum or study guide"
    )
    
    # 1536-dimensional embedding vector matching OpenAI text-embedding-3-small
    embedding = mapped_column(
        Vector(1536), nullable=False,
        comment="1536-dim dense vector embedding"
    )
    
    # Provenance metadata
    source_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_page: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    metadata_payload: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, nullable=False,
        comment="Extensible chunk metadata (e.g. section, headings, token_count)"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    skill: Mapped[Optional["Skill"]] = relationship("Skill")
