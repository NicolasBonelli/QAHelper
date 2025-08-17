import sys
sys.path.append("..")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
try:
    from backend.config import DB_URL_LOCAL
except ModuleNotFoundError:
    # Fallback when imported as top-level in CI/pytest without package context
    from config import DB_URL_LOCAL  # type: ignore

engine = create_engine(DB_URL_LOCAL)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

try:
    from backend.models.db import Base
except ModuleNotFoundError:
    from models.db import Base  # type: ignore

