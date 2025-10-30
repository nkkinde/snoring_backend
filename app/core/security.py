from datetime import datetime, timedelta, timezone
import jwt
from passlib.hash import bcrypt
from app.core.config import SECRET_KEY, ACCESS_TOKEN_MIN, REFRESH_TOKEN_DAYS

ALG = "HS256"

def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_password(pw: str, hpw: str) -> bool:
    return bcrypt.verify(pw, hpw)

def create_token(sub: str, minutes: int = ACCESS_TOKEN_MIN, days: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + (timedelta(days=days) if days else timedelta(minutes=minutes))
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALG)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALG])
