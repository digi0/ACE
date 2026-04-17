import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Local dev fallback to SQLite
    DATABASE_URL = "sqlite:///backend/data/ace_users.db"

# Railway PostgreSQL URLs use "postgres://" but SQLAlchemy needs "postgresql://"
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

_is_postgres = "postgresql" in DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    **({"pool_size": 5, "max_overflow": 10} if _is_postgres else {}),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
