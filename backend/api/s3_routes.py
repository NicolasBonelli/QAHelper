from fastapi import APIRouter, HTTPException
from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME
from utils.s3_utils import upload_text_to_s3
from tasks import process_s3_file
from models.api import S3ProcessRequest, S3UploadRequest
router = APIRouter(prefix="/s3", tags=["S3 Operations"])

@router.post("/upload")
async def upload_text_to_s3_endpoint(request: S3UploadRequest):
    """
    Uploads text to S3 and returns information about the uploaded file
    """
    try:
        # Use default bucket if not specified
        bucket = request.bucket or S3_BUCKET_NAME
        if not bucket:
            raise HTTPException(status_code=400, detail="Bucket no especificado")
        
        # Generate unique name for the file
        import uuid
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        s3_object_name = f"gemini_texts/{timestamp}_{request.filename}.txt"
        
        # Upload to S3
        upload_text_to_s3(
            request.text, 
            bucket, 
            s3_object_name, 
            AWS_ACCESS_KEY_ID, 
            AWS_SECRET_ACCESS_KEY
        )
        
        return {
            "status": "success",
            "message": "Texto subido a S3 correctamente",
            "bucket": bucket,
            "key": s3_object_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir a S3: {str(e)}")



@router.get("/health")
async def s3_health_check():
    """
    Verifies S3 connectivity
    """
    try:
        # Here you could add a real S3 verification
        return {"status": "healthy", "service": "S3"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"S3 no disponible: {str(e)}") 