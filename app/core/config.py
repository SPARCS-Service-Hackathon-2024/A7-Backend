from pydantic import BaseSettings

class Settings(BaseSettings):
    SERVER_TYPE: str
    ROOT_PATH: str
    DB_URL: str
    REDIS_URL: str
    HOUSE_REC_URL: str

    class Config:
        env_file = ".env"


settings = Settings()