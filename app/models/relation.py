import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class RelationType(str, enum.Enum):
    ANSWER_KEY_FOR = "ANSWER_KEY_FOR"
    SUPPLEMENT_FOR = "SUPPLEMENT_FOR"
    RELATED_TO = "RELATED_TO"

class DocumentRelation(Base):
    __tablename__ = "document_relations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    target_document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    relationship_type = Column(Enum(RelationType), default=RelationType.ANSWER_KEY_FOR)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    source_document = relationship("Document", foreign_keys=[source_document_id], back_populates="outgoing_relations")
    target_document = relationship("Document", foreign_keys=[target_document_id], back_populates="incoming_relations")
