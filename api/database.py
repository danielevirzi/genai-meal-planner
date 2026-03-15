"""Database engine, session, and metadata setup for the API layer."""

from __future__ import annotations

import os
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./meal_planner.db")

# SQLite needs this flag when connections are shared across request threads.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, class_=Session
)


class Base(DeclarativeBase):
    """Declarative base class inherited by all ORM models."""


def get_db() -> Iterator[Session]:
    """Yield a DB session and always close it after request handling."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(seed_data: bool = False) -> None:
    """Create all tables declared in ORM models and optionally seed mock data."""
    # Import models so SQLAlchemy registers table metadata before create_all.
    import api.models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    if seed_data:
        from api.seeds import seed_mock_data

        with SessionLocal() as db:
            seed_mock_data(db)
