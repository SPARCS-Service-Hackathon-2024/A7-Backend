from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.router import auth, chat, house


app = FastAPI(
    root_path=settings.ROOT_PATH,
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(house.router)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)