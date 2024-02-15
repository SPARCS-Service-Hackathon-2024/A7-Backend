import jwt
from fastapi import HTTPException, status, Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.models import get_Base, User
import aioredis
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.api_key import APIKeyHeader
API_KEY_NAME = "Authorization"
api_key_header_auth = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

DB_URL = f'mysql+pymysql://root:0000@localhost/sarabwayu'
engine = create_engine(DB_URL, pool_recycle=3600)

Base = get_Base()
def get_Base():
    return Base

# Base.metadata.drop_all(bind=engine) # 테이블 변경 사항 있을 시 주석 제거
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
def get_SessionLocal():
    return SessionLocal

# async def get_redis_client() -> aioredis.Redis:
#     redis = aioredis.from_url(f"redis://localhost:6379/0", encoding="utf-8", decode_responses=True)
#     try:
#         yield redis
#     finally:
#         await redis.close()

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

async def get_current_user(
    api_key: str = Depends(api_key_header_auth),
    db: Session = Depends(get_db),
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

    payload = jwt.decode(token, "sarabwayu", algorithms=["HS256"])
    nickname: str = payload.get("sub")
    user = db.query(User).filter(User.nickname == nickname).first()

    return user