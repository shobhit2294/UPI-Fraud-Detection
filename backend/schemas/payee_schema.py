from pydantic import BaseModel


class PayeeVerifyRequest(BaseModel):
    vpa: str


class PayeeVerifyResponse(BaseModel):
    vpa: str
    found: bool
    account_holder_name: str | None = None
    bank: str | None = None
    is_verified: bool
    is_dummy: bool
    warning: str | None = None
