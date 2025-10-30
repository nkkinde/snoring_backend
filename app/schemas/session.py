from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from datetime import datetime

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
    sleep_duration: Optional[float] = None  # 시간 단위
    sleep_quality: Optional[str] = None
    clips: List[ClipRes] = []

class FinalizeReq(BaseModel):
    started_at: Optional[str] = None  # ISO8601
    ended_at: Optional[str] = None    # ISO8601
    snore_count: Optional[int] = None
    snore_total_sec: Optional[int] = None
    advice: Optional[str] = None
    sleep_duration: Optional[float] = None  # 시간 단위(예: 7.5). 미지정시 자동계산
    sleep_quality: Optional[str] = None     # "매우 좋음" 등. 미지정시 규칙으로 추정

class SessionListItem(BaseModel):
    id: int
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    has_snore: bool
    snore_count: int
    snore_total_sec: int
    advice: Optional[str] = None
    sleep_duration: Optional[float] = None
    sleep_quality: Optional[str] = None
