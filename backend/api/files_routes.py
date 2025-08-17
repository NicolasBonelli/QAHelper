from fastapi import APIRouter, HTTPException, UploadFile, File


from typing import List
import os
import shutil
from datetime import datetime
import uuid
from pathlib import Path
from backend.models.api import FileUploadResponse, FileInfo
router = APIRouter(prefix="/files", tags=["File Management"])

from config import PDF_STORAGE_DIR



@router.post("/upload", response_model=FileUploadResponse)
async def upload_pdf_file(file: UploadFile = File(...)):
    """
    Uploads a PDF file to local storage
    """
    try:
        # Validate that it's a PDF
        if not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Solo se permiten archivos PDF")
        
        # Generate unique ID for the file
        file_id = str(uuid.uuid4())
        timestamp = datetime.now()
        
        # Create unique filename
        original_filename = file.filename
        safe_filename = f"{timestamp}_{file_id}_{original_filename}"
        file_path = PDF_STORAGE_DIR / safe_filename
        
        # Save the file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Get file size
        file_size = file_path.stat().st_size
        
        return FileUploadResponse(
            file_id=file_id,
            filename=original_filename,
            upload_date=datetime.now().isoformat(),
            file_size=file_size,
            message="Archivo PDF subido correctamente"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir archivo: {str(e)}")

@router.get("/list", response_model=List[FileInfo])
async def list_pdf_files():
    """
    Lists all stored PDF files
    """
    try:
        files = []
        for file_path in PDF_STORAGE_DIR.glob("*.pdf"):
            stat = file_path.stat()
            # Extract information from filename
            filename_parts = file_path.stem.split("_", 2)
            if len(filename_parts) >= 3:
                timestamp, file_id, original_name = filename_parts[0], filename_parts[1], "_".join(filename_parts[2:])
            else:
                original_name = file_path.name
                file_id = "unknown"
            
            files.append(FileInfo(
                filename=original_name,
                file_id=file_id,
                upload_date=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                file_size=stat.st_size,
                file_path=str(file_path)
            ))
        
        return sorted(files, key=lambda x: x.upload_date, reverse=True)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar archivos: {str(e)}")



@router.get("/health")
async def files_health_check():
    """
    Verifies the status of the file service
    """
    try:
        # Verify that the directory exists and is accessible
        if not PDF_STORAGE_DIR.exists():
            PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        
        file_count = len(list(PDF_STORAGE_DIR.glob("*.pdf")))
        
        return {
            "status": "healthy",
            "service": "File Storage",
            "storage_path": str(PDF_STORAGE_DIR),
            "file_count": file_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"File service no disponible: {str(e)}") 