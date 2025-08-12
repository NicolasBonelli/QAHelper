from sqlalchemy import create_engine
from sqlalchemy.sql import text
from backend.utils.db_connection import Base, engine
from backend.models.db import DocumentEmbedding
from backend.config import DB_URL_LOCAL
# Habilitar la extensión pgvector
print("🛠️ Habilitando extensión vector en la base...")
with engine.connect() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    connection.commit()
print("✅ Extensión vector habilitada.")

# Crear las tablas en la base si no existen
print("🛠️ Creando tablas en la base...")
print("✅ Tablas creadas con éxito.")
engine = create_engine(DB_URL_LOCAL) 

if __name__ == "__main__": 
    print("[+] Creando tablas...") 
    Base.metadata.create_all(engine) 
    print("[✓] Tablas creadas correctamente.")