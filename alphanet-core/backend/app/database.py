"""SQLite + SQLAlchemy engine/session wiring."""
from __future__ import annotations

import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.environ.get(
    "ALPHANET_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "alphanet.db"),
)
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}, future=True
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_add_column_if_missing(table: str, column: str, ddl: str) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        names = {r[1] for r in rows}
        if column not in names:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {ddl}"))
            conn.commit()


def init_db() -> None:
    # Imported for side effect: registers models on Base.metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    # Lightweight migrations for existing SQLite files (create_all is no-op for new cols).
    try:
        _sqlite_add_column_if_missing(
            "signals", "idempotency_key", "idempotency_key VARCHAR(128)"
        )
        _sqlite_add_column_if_missing(
            "signals", "nlp_features_json", "nlp_features_json TEXT"
        )
        _sqlite_add_column_if_missing("signals", "evidence_json", "evidence_json TEXT")
    except Exception:
        pass
