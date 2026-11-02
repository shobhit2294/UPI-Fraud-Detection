from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.db import get_db
from middleware.auth import get_current_user
from models.transaction import Payee
from schemas.payee_schema import PayeeVerifyRequest, PayeeVerifyResponse

router = APIRouter(prefix="/payees", tags=["Payees"])


@router.post("/verify", response_model=PayeeVerifyResponse)
def verify_payee(
    data: PayeeVerifyRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Look up a payee VPA before letting the user pay -- this is the
    "who am I actually sending money to" check real UPI apps do via
    NPCI's mapper service. Here it's backed by a small demo directory
    (see database/seed.py) rather than a real bank network.
    """
    payee = db.query(Payee).filter(Payee.vpa == data.vpa.strip().lower()).first()

    if not payee:
        return PayeeVerifyResponse(
            vpa=data.vpa,
            found=False,
            account_holder_name=None,
            bank=None,
            is_verified=False,
            is_dummy=True,
            warning="This VPA isn't in our verified directory. Proceed only if you "
                    "recognize the recipient -- unverified payees are a common fraud pattern.",
        )

    warning = None
    if payee.is_dummy:
        warning = "This account is flagged as a known dummy/suspicious account. Do not proceed."

    return PayeeVerifyResponse(
        vpa=payee.vpa,
        found=True,
        account_holder_name=payee.account_holder_name,
        bank=payee.bank,
        is_verified=payee.is_verified,
        is_dummy=payee.is_dummy,
        warning=warning,
    )
