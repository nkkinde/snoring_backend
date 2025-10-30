import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./snore.db")
ACCESS_TOKEN_MIN = int(os.getenv("ACCESS_TOKEN_MIN", "60"))
REFRESH_TOKEN_DAYS = int(os.getenv("REFRESH_TOKEN_DAYS", "7"))
