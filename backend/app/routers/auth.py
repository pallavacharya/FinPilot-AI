from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.auth_utils import create_access_token

router = APIRouter()

# Demo user store — replace with a real DB + hashed passwords (passlib/bcrypt) before production.
DEMO_USERS = {
    "owner@aaravretail.com": {"password": "demo1234", "role": "owner", "name": "Priya Nair"},
    "analyst@aaravretail.com": {"password": "demo1234", "role": "analyst", "name": "Dev Menon"},
}

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/login")
def login(payload: LoginRequest):
    user = DEMO_USERS.get(payload.email)
    if not user or user["password"] != payload.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": payload.email, "role": user["role"]})
    return {"access_token": token, "token_type": "bearer", "role": user["role"], "name": user["name"]}
