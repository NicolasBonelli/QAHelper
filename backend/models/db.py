from sqlalchemy import Column, String, Integer, Text, ARRAY
from db.base import Base

class DocumentEmbedding(Base):
    __tablename__ = "document_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, index=True)
    chunk_id = Column(String, index=True)
    text = Column(Text)
    embedding = Column(ARRAY(float))  # usa ARRAY de float para PostgreSQL