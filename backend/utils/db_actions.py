from models.db import DocumentEmbedding
from utils.db_connection import SessionLocal

def save_chunks_to_db(nodes, doc_id: str):
    db = SessionLocal()
    try:
        for node in nodes:
            if node.embedding is None:
                print(f"❌ Nodo sin embedding: {node.text[:30]}...")
                continue
            print(f"✅ Guardando chunk: {node.node_id}")
            chunk = DocumentEmbedding(
                doc_id=doc_id,
                chunk_id=node.node_id,
                text=node.text,
                embedding=node.embedding
            )
            db.add(chunk)
        db.commit()
        print("✅ Commit realizado con éxito.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise e
    finally:
        db.close()