"""
Step-up OTP helper for high-risk transactions.

There's no SMS gateway in this demo, so the generated code is only ever
returned in the API response, and only when config.DEMO_MODE is true --
clearly labeled as a demo code. Never do this with a real OTP: real OTPs
must only ever go to the user's registered device via SMS/push, never be
echoed back in an API response.
"""

import hashlib
import random
import string
from datetime import datetime, timedelta

OTP_LENGTH = 6
OTP_VALID_MINUTES = 5


def generate_otp() -> tuple[str, str, datetime]:
    code = "".join(random.choices(string.digits, k=OTP_LENGTH))
    code_hash = hashlib.sha256(code.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(minutes=OTP_VALID_MINUTES)
    return code, code_hash, expires_at


def verify_otp(submitted_code: str, code_hash: str) -> bool:
    return hashlib.sha256(submitted_code.encode()).hexdigest() == code_hash
