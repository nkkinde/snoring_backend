from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.db.models import User
from app.db.session import Base, engine
from app.core.security import hash_password, verify_password, create_token
from app.schemas.auth import RegisterReq, LoginReq, TokenRes
from app.api.deps import get_db
from app.core.security import decode_token

router = APIRouter(prefix="/auth", tags=["auth"])
Base.metadata.create_all(bind=engine)

@router.post("/register")
def register(body: RegisterReq, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == body.email).first()
    if exists:
        raise HTTPException(400, "Email already registered")
    u = User(email=body.email, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"ok": True, "user_id": u.id}

@router.post("/login", response_model=TokenRes)
def login(body: LoginReq, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(401, "Invalid credentials")
    return TokenRes(
        access_token=create_token(str(u.id)),
        refresh_token=create_token(str(u.id), days=7)
    )

@router.post("/refresh", response_model=TokenRes)
def refresh_token(
    refresh_token: str = Body(..., embed=True),
):
    """
    refresh_token으로 새 access_token을 발급합니다.
    refresh_token이 만료되었거나 유효하지 않으면 401 반환.
    """
    try:
        payload = decode_token(refresh_token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid refresh token")
    except Exception:
        raise HTTPException(401, "Invalid or expired refresh token")

    new_access = create_token(user_id)
    new_refresh = create_token(user_id, days=7)  # 새 refresh 토큰도 함께 갱신
    return TokenRes(access_token=new_access, refresh_token=new_refresh)