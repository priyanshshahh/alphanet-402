"""SQLite via SQLAlchemy. One process, one DB file. Simple and durable.

Schema is denormalized intentionally for MVP: every row captures the
agent's full reasoning context at the moment of decision, so post-mortems
are a single SELECT.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)
Base = declarative_base()


@contextmanager
def session_scope() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def init_db() -> None:
    from . import models  # noqa: F401  (registers tables)
    Base.metadata.create_all(bind=engine)
