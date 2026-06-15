"""
POST   /api/auth/login   — authenticate, get JWT token
POST   /api/auth/logout  — client-side token discard (no-op server side)
GET    /api/auth/me      — current user info
"""

from fastapi import APIRouter, Depends, HTTPException, status
from app.auth import (
    LoginRequest,
    TokenResponse,
    UserOut,
    create_access_token,
    get_current_user,
    get_user_by_username,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    user = get_user_by_username(body.username)
    if user is None or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    token = create_access_token({"sub": str(user["id"]), "role": user["role"]})
    return TokenResponse(
        access_token=token,
        user=UserOut(**user),
    )


@router.post("/logout")
async def logout(current_user: UserOut = Depends(get_current_user)):
    """
    Logout is client-side (discard the token).
    No server-side token invalidation in this version.
    """
    return {"status": "ok", "message": "Token discarded — log out on client side"}


@router.get("/me", response_model=UserOut)
async def me(current_user: UserOut = Depends(get_current_user)):
    return current_user
