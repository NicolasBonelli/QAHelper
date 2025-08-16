import sys
sys.path.append("..")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.config import DB_URL_LOCAL

engine = create_engine(DB_URL_LOCAL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Importar la base desde models.db para evitar duplicación
from backend.models.db import Base

