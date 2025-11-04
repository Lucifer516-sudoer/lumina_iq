from fastapi import APIRouter
from models.auth import LoginRequest, LoginResponse
from services.auth_service import auth_service

router = APIRouter(prefix="/api/auth", tags=["authentication"])

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    return await auth_service.login(request.username, request.password)

@router.post("/logout")
async def logout():
    return {"message": "Logged out successfully"}

@router.get("/verify")
async def verify_auth():
    # Simple verification endpoint - always returns success if reached
    return {"valid": True, "message": "Session is valid"}
