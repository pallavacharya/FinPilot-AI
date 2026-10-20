import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

_DEFAULT_SECRET = "dev-only-insecure-secret"
SECRET_KEY = os.getenv("JWT_SECRET", _DEFAULT_SECRET)
if SECRET_KEY == _DEFAULT_SECRET:
    print("WARNING: JWT_SECRET is not set - using an insecure dev default. Set it in .env before deploying.")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# role -> which resources it can touch (used by routers below)
ROLE_PERMISSIONS = {
    "owner": {"forecast:read", "fraud:read", "fraud:upload", "fraud:approve", "documents:read", "agent:approve", "settings:manage"},
    "analyst": {"forecast:read", "fraud:read", "fraud:upload", "documents:read", "agent:approve"},
    "viewer": {"forecast:read", "documents:read"},
}

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: Optional[str] = payload.get("sub")
        role: Optional[str] = payload.get("role")
        if user_id is None or role is None:
            raise credentials_exception
        return {"user_id": user_id, "role": role}
    except JWTError:
        raise credentials_exception

def require_permission(permission: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        allowed = ROLE_PERMISSIONS.get(user["role"], set())
        if permission not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user['role']}' lacks permission '{permission}'",
            )
        return user
    return checker
