from sqlalchemy import create_engine
from sqlalchemy.sql import text
from backend.config import DB_URL_LOCAL
from backend.models.db import Base, DocumentEmbedding

# Habilitar la extensión pgvector
print("🛠️ Habilitando extensión vector en la base...")
engine = create_engine(DB_URL_LOCAL)
with engine.connect() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    connection.commit()
print("✅ Extensión vector habilitada.")

# Crear las tablas en la base si no existen
print("🛠️ Creando tablas en la base...")
Base.metadata.create_all(engine)
print("✅ Tablas creadas con éxito.")

if __name__ == "__main__": 
    print("[+] Creando tablas...") 
    Base.metadata.create_all(engine) 
    print("[✓] Tablas creadas correctamente.")