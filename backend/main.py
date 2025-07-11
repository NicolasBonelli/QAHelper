from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from utils.s3_utils import upload_text_to_s3
#from utils.db_connection import Base, engine
import os
from dotenv import load_dotenv
import uuid
from pydantic import BaseModel
from tasks import process_s3_file
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from utils.db_connection import Base, engine
from models.db import DocumentEmbedding

# Habilitar la extensión pgvector
print("🛠️ Habilitando extensión vector en la base...")
with engine.connect() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    connection.commit()
print("✅ Extensión vector habilitada.")

# Crear las tablas en la base si no existen
print("🛠️ Creando tablas en la base...")
Base.metadata.create_all(bind=engine)

print("✅ Tablas creadas con éxito.")from supervisor.graph_builder import app as graph_app  # El grafo ya compilado



# Cargar variables del archivo .env
load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")

app = FastAPI()

# Crear tablas si no existen
Base.metadata.create_all(bind=engine)

@app.post("/chat")
def chat_endpoint(state: dict):
    result = graph_app.invoke(state)
    return result

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Solo PDFs.")

    object_name = upload_to_s3(file.file, BUCKET_NAME, file.filename)
    nodes = process_pdf_from_s3(BUCKET_NAME, object_name)
    doc_id = str(uuid.uuid4())

    save_nodes_to_db(nodes, doc_id)

    return JSONResponse(content={"message": "PDF procesado y guardado.", "doc_id": doc_id})