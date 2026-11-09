import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import String, DateTime, ForeignKey, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RecommendationHistory(Base):
    """Stores the execution trace of deterministic 3-pillar major recommendations."""
    __tablename__ = "recommendation_histories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Weights applied: {"w_riasec": 0.45, "w_academic": 0.35, "w_preference": 0.20}
    weights_applied: Mapped[Dict[str, float]] = mapped_column(
        JSONB, nullable=False, comment="Weights applied to the 3 pillars"
    )
    ranked_results: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=False,
        comment="Ranked list of major recommendations with component score breakdowns and gap analyses"
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
