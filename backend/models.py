from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Float, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(256), primary_key=True)  # Firebase UID
    email = Column(String(320), nullable=True)
    display_name = Column(String(256), nullable=True)
    selected_major = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    documents = relationship("UserDocument", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")


class UserDocument(Base):
    __tablename__ = "user_docs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(256), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(512), nullable=True)
    doc_type = Column(String(64), nullable=True)
    text = Column(Text, nullable=True)
    analysis_json = Column(Text, nullable=True)
    audit_parse_json = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="documents")

    __table_args__ = (
        Index("ix_user_docs_user_id", "user_id"),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True)  # UUID generated on frontend
    user_id = Column(String(256), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    __table_args__ = (
        Index("ix_conversations_user_id", "user_id"),
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(16), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    intent = Column(String(64), nullable=True)
    sources_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    conversation = relationship("Conversation", back_populates="messages")

    __table_args__ = (
        Index("ix_messages_conversation_id", "conversation_id"),
    )
