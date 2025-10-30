from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from collections import defaultdict

from app.api.deps import get_db, get_current_user
from app.db.models import SnoreSession

router = APIRouter(prefix="/calendar", tags=["calendar"])

@router.get("/summary")
def calendar_summary(
    date_from: str = Query(..., alias="from"),
    date_to: str = Query(..., alias="to"),
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    try:
        df = datetime.fromisoformat(date_from).date()
        dt = datetime.fromisoformat(date_to).date()
    except:
        raise HTTPException(400, "invalid date format (YYYY-MM-DD)")

    daily = defaultdict(lambda: {"count":0, "total_sec":0})
    sessions = db.query(SnoreSession)\
                 .filter(SnoreSession.user_id==user.id, SnoreSession.status=="finalized")\
                 .all()
    for s in sessions:
        d = (s.ended_at or s.created_at).date()
        if df <= d <= dt:
            daily[d]["count"] += s.snore_count or 0
            daily[d]["total_sec"] += s.snore_total_sec or 0

    out = []
    for d in sorted(daily.keys()):
        agg = daily[d]
        out.append({
            "date": d.isoformat(),
            "snore": agg["count"] > 0,
            "count": agg["count"],
            "total_sec": agg["total_sec"]
        })
    return out
