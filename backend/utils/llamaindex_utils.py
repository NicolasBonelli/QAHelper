import sys
sys.path.append("..")
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from .db_actions import  create_index_from_pg, save_chunks_to_db
from .db_connection import SessionLocal
import uuid


def chunk_faq_recursive(text: str, doc_id: str = None):
    """
    Recursive chunker for FAQs with RecursiveCharacterTextSplitter to optimize database storage
    Args:
        text: Text to process
        doc_id: Document ID (if not provided, one is generated)
    Returns:
        doc_id: Processed document ID
    """
    if doc_id is None:
        doc_id = str(uuid.uuid4())
    
    doc = Document(text=text)
    
    # Use RecursiveCharacterTextSplitter with minimal overlap to optimize database
    chunker = SentenceSplitter(
        chunk_size=120,  # Optimal size for database
        chunk_overlap=5,  # Minimal overlap to maintain context
    )
    
    nodes = chunker.get_nodes_from_documents([doc])
    
    # Embeddings with e5-base-v2 model for semantic similarity
    embed_model = HuggingFaceEmbedding(model_name="intfloat/e5-base-v2")
    embeddings = embed_model.get_text_embedding_batch([n.text for n in nodes])
    
    # Assign embeddings to each node
    for node, embedding in zip(nodes, embeddings):
        node.embedding = embedding
    
    # Save chunks to database
    print(f"💾 Saving {len(nodes)} chunks to PostgreSQL...")
    save_chunks_to_db(nodes, doc_id)
    print(f"✅ Chunks saved successfully with doc_id: {doc_id}")
    
    return doc_id


def retrieve_chunks(query: str, top_k: int = 5):
    index = create_index_from_pg()
    retriever = index.as_retriever(similarity_top_k=top_k)

    results = retriever.retrieve(query)

    for i, res in enumerate(results):
        print(f"{i+1}. Score: {res.score:.3f} - Texto: {res.text[:100]}...")

    return results


def process_and_store_faqs(faq_text: str, doc_id: str = None):
    """
    Main function to process FAQs and store them in the database
    Args:
        faq_text: FAQ text
        doc_id: Document ID (optional)
    Returns:
        doc_id: Processed document ID
    """
    try:
        print("🔄 Processing FAQs and storing in PostgreSQL...")
        doc_id = chunk_faq_recursive(faq_text, doc_id)
        print(f"✅ FAQs processed and stored. Doc ID: {doc_id}")
        return doc_id
    except Exception as e:
        print(f"❌ Error processing FAQs: {e}")
        return None



