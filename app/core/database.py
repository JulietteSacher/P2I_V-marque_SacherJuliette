from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Chemin RACINE du projet : .../v-marque-backend/
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "vmarque.db"

DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # évite les "database is locked" trop rapides
    },
)

# Optimisations SQLite pour accès concurrents (dev)
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")      # meilleure concurrence
    cursor.execute("PRAGMA synchronous=NORMAL;")    # perf/dev
    cursor.execute("PRAGMA foreign_keys=ON;")       # active les FK SQLite
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
