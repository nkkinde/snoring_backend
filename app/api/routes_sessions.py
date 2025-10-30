from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from datetime import datetime
from pathlib import Path
import uuid, shutil, math

from app.api.deps import get_db, get_current_user
from app.db.models import SnoreSession, SnoreClip
from app.schemas.session import SessionCreateRes, SessionRes, ClipRes, FinalizeReq
from app.services.advice import build_advice
from app.core.config import os
from fastapi import Query
from app.schemas.session import SessionListItem
from typing import Optional

# 오디오 저장 루트 (개발용)
AUDIO_DIR = os.getenv("AUDIO_DIR", "./data")
Path(AUDIO_DIR).mkdir(parents=True, exist_ok=True)

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.post("", response_model=SessionCreateRes)
def create_session(
    started_at: str | None = Form(None),
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    ss = SnoreSession(
        user_id=user.id,
        started_at=datetime.fromisoformat(started_at) if started_at else None,
        status="open",
    )
    db.add(ss); db.commit(); db.refresh(ss)
    return SessionCreateRes(id=ss.id, status=ss.status)

@router.post("/{session_id}/clips/upload", response_model=ClipRes)
def upload_clip(
    session_id: int,
    start_sec: float = Form(...),
    end_sec: float = Form(...),
    confidence: int | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    ss = db.get(SnoreSession, session_id)
    if not ss or ss.user_id != user.id:
        raise HTTPException(404, "session not found")
    if ss.status != "open":
        raise HTTPException(400, "session already finalized")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".wav", ".m4a", ".mp3"]:
        raise HTTPException(415, "unsupported audio format")

    fname = f"clip_{session_id}_{uuid.uuid4()}{ext}"
    path = Path(AUDIO_DIR) / fname
    with path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    dur = max(1, int(math.ceil(end_sec - start_sec)))
    clip = SnoreClip(
        session_id=session_id,
        file_path=str(path),
        start_sec=start_sec,
        end_sec=end_sec,
        duration_sec=dur,
        confidence=confidence
    )
    db.add(clip)

    # 세션 집계 갱신
    ss.has_snore = True
    ss.snore_count = (ss.snore_count or 0) + 1
    ss.snore_total_sec = (ss.snore_total_sec or 0) + dur

    db.commit(); db.refresh(clip)

    return ClipRes(
        id=clip.id, file_path=clip.file_path, start_sec=clip.start_sec,
        end_sec=clip.end_sec, duration_sec=clip.duration_sec, confidence=clip.confidence
    )

@router.post("/{session_id}/finalize", response_model=SessionRes)
def finalize_session(
    session_id: int,
    body: FinalizeReq,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    ss = db.get(SnoreSession, session_id)
    if not ss or ss.user_id != user.id:
        raise HTTPException(404, "session not found")
    if ss.status != "open":
        raise HTTPException(400, "already finalized")

    if body.started_at: ss.started_at = datetime.fromisoformat(body.started_at)
    if body.ended_at:   ss.ended_at   = datetime.fromisoformat(body.ended_at)

    if body.snore_count is not None: ss.snore_count = body.snore_count
    if body.snore_total_sec is not None: ss.snore_total_sec = body.snore_total_sec
    ss.has_snore = (ss.snore_count or 0) > 0

    ss.advice = body.advice or build_advice(ss.snore_count or 0, ss.snore_total_sec or 0)
    ss.status = "finalized"
    db.commit(); db.refresh(ss)

    return _to_session_res(ss)

@router.get("/{session_id}", response_model=SessionRes)
def get_session(session_id: int, db: Session = Depends(get_db), user = Depends(get_current_user)):
    ss = db.get(SnoreSession, session_id)
    if not ss or ss.user_id != user.id:
        raise HTTPException(404, "session not found")
    return _to_session_res(ss)

def _to_session_res(ss: SnoreSession) -> SessionRes:
    clips = [
        ClipRes(
            id=c.id, file_path=c.file_path, start_sec=c.start_sec,
            end_sec=c.end_sec, duration_sec=c.duration_sec, confidence=c.confidence
        ) for c in ss.clips
    ]
    return SessionRes(
        id=ss.id, status=ss.status,
        started_at=ss.started_at.isoformat() if ss.started_at else None,
        ended_at=ss.ended_at.isoformat() if ss.ended_at else None,
        has_snore=bool(ss.has_snore),
        snore_count=ss.snore_count or 0,
        snore_total_sec=ss.snore_total_sec or 0,
        advice=ss.advice,
        clips=clips
    )

def _to_session_list_item(ss: SnoreSession) -> SessionListItem:
    return SessionListItem(
        id=ss.id,
        started_at=ss.started_at.isoformat() if ss.started_at else None,
        ended_at=ss.ended_at.isoformat() if ss.ended_at else None,
        has_snore=bool(ss.has_snore),
        snore_count=ss.snore_count or 0,
        snore_total_sec=ss.snore_total_sec or 0,
        advice=ss.advice
    )
@router.get("", response_model=list[SessionListItem])
def list_sessions_by_date(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """
    특정 날짜에 해당 사용자가 보유한 세션 목록을 반환.
    날짜 기준: ended_at(있으면) 또는 created_at 의 '날짜부'가 일치하는 레코드.
    """
    # 날짜 파싱
    try:
        target = datetime.fromisoformat(date).date()  # YYYY-MM-DD
    except Exception:
        raise HTTPException(400, "invalid date format (YYYY-MM-DD)")

    # 후보 조회: 해당 유저의 finalized/open 모두 포함할지? → 보통 finalized만 노출
    q = db.query(SnoreSession).filter(
        SnoreSession.user_id == user.id
    ).all()

    # ended_at 있으면 그 날짜, 없으면 created_at 날짜로 필터
    result = []
    for s in q:
        d = (s.ended_at or s.created_at).date()
        if d == target:
            result.append(_to_session_list_item(s))

    # 최신순 정렬(ended_at/created_at 역순)
    result.sort(key=lambda x: (x.ended_at or x.started_at or ""), reverse=True)
    return result

@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """
    세션 및 관련 클립(오디오 파일 포함)을 완전히 삭제합니다.
    파일이 존재하지 않아도 에러를 발생시키지 않습니다.
    """
    ss = db.get(SnoreSession, session_id)
    if not ss or ss.user_id != user.id:
        raise HTTPException(404, "session not found")

    # 연결된 클립 파일 삭제
    for clip in ss.clips:
        try:
            p = Path(clip.file_path)
            if p.exists():
                p.unlink()  # 파일 삭제
        except Exception as e:
            print(f"[WARN] 파일 삭제 실패: {clip.file_path} ({e})")

    # DB에서 세션 삭제
    db.delete(ss)
    db.commit()
    return {"ok": True, "message": "Session and audio files deleted."}

# 세션 / 클립 삭제 (개인정보 보호용)
@router.delete("/{session_id}/clips/{clip_id}")
def delete_clip(
    session_id: int,
    clip_id: int,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    """
    특정 클립(오디오 파일 1개)만 삭제합니다.
    """
    ss = db.get(SnoreSession, session_id)
    if not ss or ss.user_id != user.id:
        raise HTTPException(404, "session not found")

    clip = next((c for c in ss.clips if c.id == clip_id), None)
    if not clip:
        raise HTTPException(404, "clip not found")

    try:
        p = Path(clip.file_path)
        if p.exists():
            p.unlink()
    except Exception as e:
        print(f"[WARN] 파일 삭제 실패: {clip.file_path} ({e})")

    db.delete(clip)
    db.commit()
    return {"ok": True, "message": "Clip deleted."}

@router.post("/{session_id}/finalize", response_model=SessionRes)
def finalize_session(
    session_id: int,
    body: FinalizeReq,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    ss = db.get(SnoreSession, session_id)
    if not ss or ss.user_id != user.id:
        raise HTTPException(404, "session not found")
    if ss.status != "open":
        raise HTTPException(400, "already finalized")

    if body.started_at: ss.started_at = datetime.fromisoformat(body.started_at)
    if body.ended_at:   ss.ended_at   = datetime.fromisoformat(body.ended_at)

    # 집계 지정값 우선
    if body.snore_count is not None: ss.snore_count = body.snore_count
    if body.snore_total_sec is not None: ss.snore_total_sec = body.snore_total_sec
    ss.has_snore = (ss.snore_count or 0) > 0

    # 수면 시간 자동 계산 (미전달 시)
    if body.sleep_duration is not None:
        ss.sleep_duration = body.sleep_duration
    else:
        if ss.started_at and ss.ended_at:
            delta = ss.ended_at - ss.started_at
            ss.sleep_duration = round(delta.total_seconds() / 3600.0, 1)  # 소수1자리
        else:
            ss.sleep_duration = None

    # 수면 질 자동 추정 (미전달 시 간단 규칙)
    if body.sleep_quality is not None:
        ss.sleep_quality = body.sleep_quality
    else:
        # 매우 간단한 휴리스틱: 총 코골이 시간이 수면 대비 비율 기준
        if ss.sleep_duration and ss.sleep_duration > 0:
            ratio = (ss.snore_total_sec or 0) / (ss.sleep_duration * 3600.0)
        else:
            ratio = (ss.snore_total_sec or 0) / max(1, (ss.snore_total_sec or 1))  # 정보 부족 시 안전 처리

        if (ss.snore_count or 0) == 0:
            ss.sleep_quality = "매우 좋음"
        elif ratio < 0.01:
            ss.sleep_quality = "좋음"
        elif ratio < 0.03:
            ss.sleep_quality = "보통"
        elif ratio < 0.06:
            ss.sleep_quality = "주의"
        else:
            ss.sleep_quality = "오류"  # 코골이 과다/품질 낮음으로 표시(라벨 명은 자유)

    # 피드백(문장)
    ss.advice = body.advice or build_advice(ss.snore_count or 0, ss.snore_total_sec or 0)
    ss.status = "finalized"
    db.commit(); db.refresh(ss)

    return _to_session_res(ss)

# 상세 응답 직렬화에 신규 필드 포함
def _to_session_res(ss: SnoreSession) -> SessionRes:
    clips = [
        ClipRes(
            id=c.id, file_path=c.file_path, start_sec=c.start_sec,
            end_sec=c.end_sec, duration_sec=c.duration_sec, confidence=c.confidence
        ) for c in ss.clips
    ]
    return SessionRes(
        id=ss.id, status=ss.status,
        started_at=ss.started_at.isoformat() if ss.started_at else None,
        ended_at=ss.ended_at.isoformat() if ss.ended_at else None,
        has_snore=bool(ss.has_snore),
        snore_count=ss.snore_count or 0,
        snore_total_sec=ss.snore_total_sec or 0,
        advice=ss.advice,
        sleep_duration=ss.sleep_duration,
        sleep_quality=ss.sleep_quality,
        clips=clips
    )

# 날짜별 목록용 직렬화에도 포함
def _to_session_list_item(ss: SnoreSession) -> SessionListItem:
    return SessionListItem(
        id=ss.id,
        started_at=ss.started_at.isoformat() if ss.started_at else None,
        ended_at=ss.ended_at.isoformat() if ss.ended_at else None,
        has_snore=bool(ss.has_snore),
        snore_count=ss.snore_count or 0,
        snore_total_sec=ss.snore_total_sec or 0,
        advice=ss.advice,
        sleep_duration=ss.sleep_duration,
        sleep_quality=ss.sleep_quality
    )