from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.core.security import decode_token
from app.db.models import User

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(authorization: str = Header(None), db: Session = Depends(get_db)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        sub = int(decode_token(token)["sub"])
    except Exception:
        raise HTTPException(401, "Invalid token")
    user = db.get(User, sub)
    if not user:
        raise HTTPException(401, "User not found")
    return user
