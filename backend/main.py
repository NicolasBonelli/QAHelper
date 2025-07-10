from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from s3_utils import upload_to_s3
from llamaindex_utils import process_pdf_from_s3
from db.crud import save_nodes_to_db
from db.base import Base, engine
import os
from dotenv import load_dotenv
import uuid
from supervisor.graph_builder import app as graph_app  # El grafo ya compilado



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