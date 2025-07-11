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