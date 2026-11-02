from pydantic import BaseModel, Field
from typing import Optional


class TransactionRequest(BaseModel):
    amount: float = Field(gt=0)
    balance: float = Field(gt=0)
    city: str
    device: str
    transaction_type: str

    payee_vpa: str

    # Optional -- if the browser denies/lacks geolocation, we still allow
    # the payment but note that no location signal was available.
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TransactionResponse(BaseModel):
    id: int
    amount: float
    is_fraud: bool
    risk: float
    status: str
    otp_required: bool
    payee_name: Optional[str] = None
    payee_verified: bool
    demo_otp_code: Optional[str] = None  # only populated when config.DEMO_MODE is true


class OtpVerifyRequest(BaseModel):
    code: str


class TransactionEventOut(BaseModel):
    stage: str
    status: str
    actor: str
    message: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True
