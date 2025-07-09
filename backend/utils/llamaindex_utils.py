from llama_index.core import Document
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from backend.utils.db_actions import save_chunks_to_db
import uuid

def chunk_faq_semantic(text: str):
    """Chunker semántico para FAQs con embeddings de e5-base-v2"""
    doc = Document(text=text)
    embed_model = HuggingFaceEmbedding(model_name="intfloat/e5-base-v2")
    
    chunker = SemanticSplitterNodeParser(
        embed_model=embed_model,
        buffer_size=2,
        breakpoint_percentile_threshold=94
    )
    nodes = chunker.get_nodes_from_documents([doc])
    
    # 💥 Embedding manual de los nodos
    embeddings = embed_model.get_text_embedding_batch([n.text for n in nodes])
    for node, embedding in zip(nodes, embeddings):
        node.embedding = embedding
    
    return nodes

# Ejemplo de uso
faq_texto = """
    Pregunta: ¿Qué es el producto AIStart?
    Respuesta: AIStart es una plataforma de inteligencia artificial que ayuda a las startups a automatizar procesos de marketing...

    Pregunta: ¿Cómo se integra AIStart con otras herramientas?
    Respuesta: AIStart ofrece una API RESTful...

    Pregunta: ¿Es seguro usar AIStart con datos sensibles?
    Respuesta: Sí, la seguridad es una prioridad...

    Pregunta: ¿Cuánto tiempo lleva implementar AIStart?
    Respuesta: La implementación depende del caso de uso...
    """

if __name__ == "__main__":
    print("➡️ Procesando chunks semánticos con embeddings...")
    chunks = chunk_faq_semantic(faq_texto)
    print(f"✅ Chunks generados: {len(chunks)}")

    doc_id = str(uuid.uuid4())  # ID único del documento
    print(f"📥 Guardando chunks en PostgreSQL con doc_id = {doc_id}...")
    save_chunks_to_db(chunks, doc_id)
    print("✅ Chunks guardados con éxito.")
