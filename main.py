from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from app.router import auth, chat, house



app = FastAPI()

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

