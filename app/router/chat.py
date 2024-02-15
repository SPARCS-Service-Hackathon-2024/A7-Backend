from typing import Annotated
from fastapi import APIRouter, Depends
from app.schemas.request import Chat
from app.schemas.response import ApiResponse
from app.service.chat import ChatService

router = APIRouter(prefix="/chat")

@router.post("/chat", response_model=ApiResponse, tags=["Chat"])
async def post_chat(
    chat_data: Chat,
    chat_service: Annotated[ChatService, Depends()]
):
    return ApiResponse(
        data=await chat_service.chat(chat_data)
    )