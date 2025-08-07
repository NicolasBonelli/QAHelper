from pydantic import BaseModel
from typing import Optional, Dict, Any

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    context: Optional[Dict[str, Any]] = None

class FileInfo(BaseModel):
    filename: str
    file_id: str
    upload_date: str
    file_size: int
    file_path: str

class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    upload_date: str
    file_size: int
    message: str

class S3UploadRequest(BaseModel):
    text: str
    filename: str
    bucket: Optional[str] = None

class S3ProcessRequest(BaseModel):
    bucket: str
    key: str