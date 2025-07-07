from db.models import DocumentEmbedding
from db.base import SessionLocal

def save_nodes_to_db(nodes, doc_id: str):
    db = SessionLocal()
    try:
        for node in nodes:
            if node.embedding:
                embedding_record = DocumentEmbedding(
                    doc_id=doc_id,
                    chunk_id=node.node_id,
                    text=node.text,
                    embedding=node.embedding,
                )
                db.add(embedding_record)
        db.commit()
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
