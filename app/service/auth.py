import aioredis
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db, get_redis_client, save_db
from app.db.models import User
import jwt
import datetime
from passlib.context import CryptContext

from app.schemas.request import Auth
from app.schemas.response import JwtToken

secret_key = 'sarabwayu'
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:

    def __init__(self, db: Session = Depends(get_db), redis: aioredis.Redis = Depends(get_redis_client)):
        self.db = db
        self.redis = redis
    async def create_token(self, nickname: str):
        # 페이로드 설정
        payload = {
            'sub': nickname,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1)
        }
        # JWT 토큰 생성
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return token

    async def login(self, auth_data: Auth):
        # 회원가입이 돼 있으면 토큰 반환

        hahsed_password = pwd_context.hash(auth_data.password)
        user = self.db.query(User).filter(
            User.nickname == auth_data.nickname,
        ).first()

        if user:
            if not pwd_context.verify(auth_data.password, user.hashed_password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="이미 사용중인 닉네임이거나 비밀번호가 틀렸습니다.",
                )
            token = await self.create_token(auth_data.nickname)
            is_signup = False

        # 회원가입이 안 돼 있으면 db에 저장하고 토큰 반환
        else:
            user = User(
                hashed_password=hahsed_password,
                nickname=auth_data.nickname
            )
            save_db(user, self.db)
            token = await self.create_token(auth_data.nickname)
            is_signup = True

        return JwtToken(
            nickname=user.nickname,
            is_signup=is_signup,
            access_token=token,
        )