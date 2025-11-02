# app/schemas/session.py
from pydantic import BaseModel, Field
from typing import Optional, List
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./snore.db")

class Base(DeclarativeBase):
    pass

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class ClipIn(BaseModel):
    start_sec: float = Field(ge=0)
    end_sec: float = Field(gt=0)
    confidence: Optional[int] = Field(default=None, ge=0, le=100)

class ClipRes(BaseModel):
    id: int
    file_path: str
    start_sec: float
    end_sec: float
    duration_sec: int
    confidence: Optional[int]

class SessionCreateRes(BaseModel):
    id: int
    status: str

class SessionRes(BaseModel):
    id: int
    status: str
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    has_snore: bool
    snore_count: int
    snore_total_sec: int
    advice: Optional[str] = None
    clips: List[ClipRes] = []

class FinalizeReq(BaseModel):
    started_at: Optional[str] = None  # ISO8601
    ended_at: Optional[str] = None    # ISO8601
    snore_count: Optional[int] = None
    snore_total_sec: Optional[int] = None
    advice: Optional[str] = None
