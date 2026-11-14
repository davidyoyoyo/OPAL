"""Database engine and request-scoped SQLAlchemy sessions."""
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://opal:opal@localhost:5432/opal",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Yield one session per request; callers own transaction boundaries."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
