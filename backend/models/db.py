from sqlalchemy import Column, Integer, Text, String, TIMESTAMP, UUID, ForeignKey, func
from pgvector.sqlalchemy import Vector  # <-- IMPORT CORRECTO
from utils.db_connection import Base  # <-- Usá la ruta real a Base


class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True)
    chunk_id = Column(String, index=True)
    text = Column(Text)
    embedding = Column(Vector(768)) 

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id= Column(UUID, primary_key=True)
    started_at = Column(TIMESTAMP, server_default=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(UUID, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(Text, nullable=False)  # 'user' o 'agent'
    message = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())