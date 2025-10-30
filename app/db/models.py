from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.session import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("SnoreSession", back_populates="user")

class SnoreSession(Base):
    __tablename__ = "snore_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    has_snore = Column(Boolean, default=False)       # 코골이 유무
    snore_count = Column(Integer, default=0)         # 구간 수
    snore_total_sec = Column(Integer, default=0)     # 총 길이(초)
    advice = Column(Text, nullable=True)             # 피드백
    sleep_duration = Column(Float, nullable=True)  # 단위: 시간 (예: 7.5)
    sleep_quality = Column(String(20), nullable=True)  # "매우 좋음" | "보통" | "오류" 등
    status = Column(String(20), default="open")      # open|finalized
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")
    clips = relationship("SnoreClip", back_populates="session", cascade="all, delete-orphan")

class SnoreClip(Base):
    __tablename__ = "snore_clips"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("snore_sessions.id"), nullable=False, index=True)
    file_path = Column(Text, nullable=False)         # 로컬 경로 또는 S3 URL
    start_sec = Column(Float, nullable=False)
    end_sec = Column(Float, nullable=False)
    duration_sec = Column(Integer, nullable=False)
    confidence = Column(Integer, nullable=True)      # 0~100

    session = relationship("SnoreSession", back_populates="clips")
