import sys
sys.path.append("..")

from backend.utils.db_connection import SessionLocal
from backend.models.db import DocumentEmbedding, ChatSession, ChatMessage
from llama_index.core import VectorStoreIndex, Document
from llama_index.core.schema import Node
import numpy as np

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
        session = db.query(ChatSession).filter_by(id=session_id).first()
        if not session:
            session = ChatSession(id=session_id)
            db.add(session)

        msg = ChatMessage(session_id=session_id, role=role, message=message)
        db.add(msg)
        db.commit()
    except Exception as e:
        db.rollback()
        print("[DB Logger Error]", e)
    finally:
        db.close()


from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings, StorageContext, load_index_from_storage, VectorStoreIndex
from llama_index.vector_stores.postgres import PGVectorStore  # integración LlamaIndex
# otras importaciones tuyas siguen igual...

# 1) configurar el modelo de embeddings globalmente (Settings)
embed_model = HuggingFaceEmbedding(model_name="intfloat/e5-base-v2")
Settings.embed_model = embed_model

# 2) crear el vector store (ajusta params a tu version/tabla)
vector_store = PGVectorStore.from_params(
    database="qahelper",
    host="localhost",
    user="postgres",
    password="postgres",
    port=5432,
    table_name="document_embeddings",  # tu tabla
    embed_dim=768,
)
from llama_index.core import Document
from llama_index.core.schema import TextNode

def load_chunks_into_vectorstore():
    db = SessionLocal()
    try:
        chunks = db.query(DocumentEmbedding).all()
        nodes = []
        for chunk in chunks:
            node = TextNode(text=chunk.text, id_=chunk.chunk_id, embedding=np.array(chunk.embedding))
            nodes.append(node)
        index = VectorStoreIndex(nodes, storage_context=StorageContext.from_defaults(vector_store=vector_store))
        return index
    finally:
        db.close()

        
def create_index_from_pg():

    index = load_chunks_into_vectorstore()
    print("✅ Índice cargado desde storage_context")

    return index

def insert_chat_session(session_id: str):
    """Inserta una nueva sesión en la tabla chat_sessions"""
    try:
        db = SessionLocal()
        # Verificar si la sesión ya existe
        existing_session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        
        if not existing_session:
            new_session = ChatSession(id=session_id)
            db.add(new_session)
            db.commit()
            print(f"[DB Actions] Nueva sesión creada: {session_id}")
        else:
            print(f"[DB Actions] Sesión ya existe: {session_id}")
        
        db.close()
    except Exception as e:
        print(f"[DB Actions] Error insertando sesión: {e}")
        if db:
            db.close()

if __name__ == "__main__":
    save_message("39105cb8-ba8c-40c6-aaf7-dd8571b605e0","ai","A ver")
    print("Anduvo")
