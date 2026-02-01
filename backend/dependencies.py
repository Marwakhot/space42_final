"""
FastAPI dependencies for authentication and authorization.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth_utils import decode_token

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Validate JWT token and return current user info.
    Returns dict with: sub (user_id), user_type, email
    """
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": payload.get("sub"),
        "user_type": payload.get("user_type"),
        "email": payload.get("email")
    }


async def require_candidate(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user is a candidate."""
    if current_user["user_type"] != "candidate":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Candidate access required"
        )
    return current_user


async def require_hr(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user is HR personnel."""
    if current_user["user_type"] != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR access required"
        )
    return current_user


async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user is an admin."""
    if current_user["user_type"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
