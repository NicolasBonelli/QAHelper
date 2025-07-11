from utils.db_connection import SessionLocal
from ..models.db import DocumentEmbedding, ChatSession, ChatMessage

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

def save_message(session_id: str, role: str, message: str):
    db = SessionLocal()
    try:
        # Asegurar que exista la sesión
        session = db.query(ChatSession).filter_by(session_id=session_id).first()
        if not session:
            session = ChatSession(session_id=session_id)
            db.add(session)

        msg = ChatMessage(session_id=session_id, role=role, message=message)
        db.add(msg)
        db.commit()
    except Exception as e:
        db.rollback()
        print("[DB Logger Error]", e)
    finally:
        db.close()