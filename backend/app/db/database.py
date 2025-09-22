from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

DB_TYPE = os.getenv("DB_TYPE", "mysql")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "141201")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "parking_db")

# Proper SQLAlchemy URL
DATABASE_URL = f"{DB_TYPE}+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
# Create engine
engine = create_engine(DATABASE_URL, echo=True)

# Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

# -------------------------
# Dependency for FastAPI
# -------------------------
def get_db():
    """
    Dependency that provides a database session.
    Closes the session after request is finished.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()