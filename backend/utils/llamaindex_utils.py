from llama_index.readers.file.base import PDFReader
from llama_index.core.node_parser import SemanticChunker
from llama_index.embeddings.openai import OpenAIEmbedding  # reemplazable
from llama_index.core import Document
import boto3
import tempfile

def process_pdf_from_s3(bucket_name, object_name):
    s3 = boto3.client('s3')
    with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp_file:
        s3.download_fileobj(bucket_name, object_name, tmp_file)
        tmp_file.seek(0)

        reader = PDFReader()
        docs = reader.load_data(tmp_file.name)

        embed_model = OpenAIEmbedding()  # usar Gemini u Ollama si querés
        chunker = SemanticChunker(embed_model)
        nodes = chunker.get_nodes_from_documents(docs)

        return nodes
