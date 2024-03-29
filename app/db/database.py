import json

import jwt
from fastapi import HTTPException, status, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.db.models import get_Base, User
import aioredis
from fastapi.security.api_key import APIKeyHeader
api_key_header_auth = APIKeyHeader(name="Authorization", auto_error=False)


DB_URL = f'mysql+pymysql://root:0000@{settings.DB_URL}/sarabwayu'
engine = create_engine(DB_URL, pool_recycle=3600)

Base = get_Base()
def get_Base():
    return Base

# Base.metadata.drop_all(bind=engine) # 테이블 변경 사항 있을 시 주석 제거
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
def get_SessionLocal():
    return SessionLocal

async def get_redis_client() -> aioredis.Redis:
    redis = aioredis.from_url(f"redis://{settings.REDIS_URL}:6379/0", encoding="utf-8", decode_responses=True)
    try:
        yield redis
    finally:
        await redis.close()

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
def save_db(data, db):
    try:
        db.add(data)
        db.commit()
        db.refresh(data)
        return data
    except:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="데이터베이스에 오류가 발생했습니다."
        )


async def user_to_json(user):
    return json.dumps(
        {
            "id": user.id,
            "nickname": user.nickname,
            "phone": user.phone,
            "is_deleted": user.is_deleted,
        }
    )


async def get_current_user(
    api_key: str = Depends(api_key_header_auth),
    db: Session = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis_client)
) -> User:

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = api_key.replace("Bearer ", "")
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, "sarabwayu", algorithms=["HS256"])
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )



    nickname: str = payload.get("sub")
    user_info = await redis.get(f"user:{nickname}")
    if user_info:
        return User(**json.loads(user_info))

    user = db.query(User).filter(User.nickname == nickname).first()

    await redis.set(f"user:{nickname}", await user_to_json(user), ex=3600)

    return user