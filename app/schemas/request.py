from pydantic import BaseModel


class Auth(BaseModel):
    nickname: str
    password: str

class Chat(BaseModel):
    person_count: str
    period: str
    identity: str
    car: str
    child: str
    significant: str

class House(BaseModel):
    house_info: dict
