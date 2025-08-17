from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from sqlalchemy.sql import text
from backend.utils.db_connection import Base, engine


# Import routers
from backend.api.s3_routes import router as s3_router
from backend.api.chat_routes import router as chat_router
from backend.api.files_routes import router as files_router

from backend.api.config import (
    API_TITLE, API_DESCRIPTION, API_VERSION,
    CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS,
    HOST, PORT
)

# Database configuration
print("🛠️ Enabling vector extension in database...")
with engine.connect() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    connection.commit()
print("✅ Vector extension enabled.")

# Create tables in database if they don't exist
print("🛠️ Creating tables in database...")
Base.metadata.create_all(bind=engine)
print("✅ Tables created successfully.")


app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)


app.include_router(s3_router)
app.include_router(chat_router)
app.include_router(files_router)

@app.get("/")
async def root():
    """
    API root endpoint
    """
    return {
        "message": "QAHelper API - Sistema de soporte inteligente",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    """
    General system health verification endpoint
    """
    return {
        "status": "healthy",
        "service": "QAHelper API",
        "database": "connected",
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Global exception handler
    """
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)