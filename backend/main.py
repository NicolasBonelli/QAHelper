from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from utils.db_connection import Base, engine


# Importar routers
from api.s3_routes import router as s3_router
from api.chat_routes import router as chat_router
from api.files_routes import router as files_router

from api.config import (
    API_TITLE, API_DESCRIPTION, API_VERSION,
    CORS_ORIGINS, CORS_ALLOW_CREDENTIALS, CORS_ALLOW_METHODS, CORS_ALLOW_HEADERS,
    HOST, PORT
)

# Configuración de la base de datos
print("🛠️ Habilitando extensión vector en la base...")
with engine.connect() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    connection.commit()
print("✅ Extensión vector habilitada.")

# Crear las tablas en la base si no existen
print("🛠️ Creando tablas en la base...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas con éxito.")

# Crear aplicación FastAPI
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=CORS_ALLOW_CREDENTIALS,
    allow_methods=CORS_ALLOW_METHODS,
    allow_headers=CORS_ALLOW_HEADERS,
)

# Incluir routers
app.include_router(s3_router)
app.include_router(chat_router)
app.include_router(files_router)

@app.get("/")
async def root():
    """
    Endpoint raíz de la API
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
    Endpoint de verificación de salud general del sistema
    """
    return {
        "status": "healthy",
        "service": "QAHelper API",
        "database": "connected",
    }

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    Manejador global de excepciones
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