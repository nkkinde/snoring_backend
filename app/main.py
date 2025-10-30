# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes_auth import router as auth_router
from app.api.routes_sessions import router as sessions_router
from app.api.routes_calendar import router as calendar_router
from app.db.session import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Snore Detection Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 중 전체 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(auth_router)
app.include_router(sessions_router)
app.include_router(calendar_router)

@app.get("/")
def health():
    return {"ok": True}
