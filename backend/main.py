from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from utils.s3_utils import upload_text_to_s3
#from utils.db_connection import Base, engine
import os
from dotenv import load_dotenv
import uuid
from pydantic import BaseModel
from tasks import process_s3_file

app = FastAPI()
# Cargar variables del archivo .env
load_dotenv()

BUCKET_NAME = os.getenv("BUCKET_NAME")

app = FastAPI()

# Crear tablas si no existen
#Base.metadata.create_all(bind=engine)

class TaskInput(BaseModel):
    bucket: str
    key: str



@app.post("/process-s3")
async def trigger_process_s3_file(data: TaskInput):
    process_s3_file.delay(data.bucket, data.key)
    return {"status": "ok", "message": "Tarea enviada"}