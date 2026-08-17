"""
SQLAlchemy models for the future SQLite/Postgres migration path (Section 14).

These are defined now so the transition away from JSONStore doesn't require
a redesign later -- only a swap of the storage engine used by each module.
Not wired into the app by default in v0.7/v0.8; JSONStore is the active
backend. Enable by pointing engines at `get_engine()` / `SessionLocal`.
"""
from datetime import datetime

from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from david.config.settings import get_settings

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Session(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=False)
    token_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class Upload(Base):
    __tablename__ = "uploads"
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=True)
    original_name = Column(String, nullable=False)
    stored_name = Column(String, nullable=False)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApiUsage(Base):
    __tablename__ = "api_usage"
    id = Column(String, primary_key=True)
    provider = Column(String, index=True, nullable=False)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Float, default=0.0)
    success = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Note(Base):
    __tablename__ = "notes"
    id = Column(String, primary_key=True)
    user_id = Column(String, index=True, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_engine():
    settings = get_settings()
    return create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    )


def get_session_factory():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


SessionLocal = None  # lazily created via get_session_factory() when SQL mode is enabled
