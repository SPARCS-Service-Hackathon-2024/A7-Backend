from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.database import get_db, get_current_user
from app.db.models import User
from app.schemas.request import Chat


class ChatService:
    def __init__(self, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        self.db = db
        self.user = user

    async def chat(self, chat_data: Chat):
        # print(chat_data.person_count)
        # print(chat_data.period)
        # print(chat_data.identity)
        # print(chat_data.car)
        # print(chat_data.child)
        # print(chat_data.significant)

        return chat_data