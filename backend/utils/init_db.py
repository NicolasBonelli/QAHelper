from sqlalchemy import create_engine
from sqlalchemy.sql import text
try:
    from backend.config import DB_URL_LOCAL
except ModuleNotFoundError:
    from config import DB_URL_LOCAL  # type: ignore
try:
    from backend.models.db import Base, DocumentEmbedding
except ModuleNotFoundError:
    from models.db import Base, DocumentEmbedding  # type: ignore

# Enable the pgvector extension
print("🛠️ Enabling vector extension in database...")
engine = create_engine(DB_URL_LOCAL)
with engine.connect() as connection:
    connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    connection.commit()
print("✅ Vector extension enabled.")

# Create tables in database if they don't exist
print("🛠️ Creating tables in database...")
Base.metadata.create_all(engine)
print("✅ Tables created successfully.")

if __name__ == "__main__": 
    print("[+] Creating tables...") 
    Base.metadata.create_all(engine) 
    print("[✓] Tables created correctly.")