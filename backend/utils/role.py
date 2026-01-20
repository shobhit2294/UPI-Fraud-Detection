from fastapi import Depends, HTTPException
from utils.jwt import verify_token

def owner_only(payload=Depends(verify_token)):
    if payload.get("role") != "owner":
        raise HTTPException(status_code=403, detail="Owner access only")
    return payload
