from sqlalchemy import Column, Integer, Text, String
from pgvector.sqlalchemy import Vector  # <-- IMPORT CORRECTO
from utils.db_connection import Base  # <-- Usá la ruta real a Base

class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True)
    chunk_id = Column(String, index=True)
    text = Column(Text)
    embedding = Column(Vector(768)) 