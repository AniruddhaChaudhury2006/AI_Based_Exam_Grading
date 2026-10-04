from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Uses SQLite for simplicity; replace with PostgreSQL/MySQL connection string for production
SQLALCHEMY_DATABASE_URL = "sqlite:///./grading_app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# FastAPI Dependency to yield DB sessions per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()