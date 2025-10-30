from pydantic import BaseModel, EmailStr

class RegisterReq(BaseModel):
    email: EmailStr
    password: str

class LoginReq(BaseModel):
    email: EmailStr
    password: str

class TokenRes(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
