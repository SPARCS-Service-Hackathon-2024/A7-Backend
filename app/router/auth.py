from typing import Annotated

from fastapi import APIRouter, Depends

from app.db.database import get_current_user
from app.schemas.request import Auth
from app.schemas.response import ApiResponse
from app.service.auth import AuthService

router = APIRouter(prefix="/auth")

@router.post("/login", response_model=ApiResponse, tags=["Auth"])
async def get_auth_login(
    auth_data: Auth,
    auth_service: Annotated[AuthService, Depends()]
):
    return ApiResponse(
        data=await auth_service.login(auth_data)
    )

@router.get("/info", response_model=ApiResponse, tags=["Auth"])
async def get_auth_info(
    user: Annotated[get_current_user, Depends()]
):
    user.hashed_password = None
    return ApiResponse(data=user)