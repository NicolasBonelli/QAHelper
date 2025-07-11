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

print("✅ Tablas creadas con éxito.")
# Cargar variables del archivo .env
load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")

app = FastAPI()


class TaskInput(BaseModel):
    bucket: str
    key: str



@app.post("/process-s3")
async def trigger_process_s3_file(data: TaskInput):
    process_s3_file.delay(data.bucket, data.key)
    return {"status": "ok", "message": "Tarea enviada"}