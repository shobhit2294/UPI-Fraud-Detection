from pydantic import BaseModel
from pydantic import Field


class LoginRequest(BaseModel):
    phone: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str


class RequestOtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)


class RequestOtpResponse(BaseModel):
    message: str
    expires_in_seconds: int
    demo_otp: str | None = None


class VerifyOtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=20)
    otp: str = Field(min_length=6, max_length=6)
