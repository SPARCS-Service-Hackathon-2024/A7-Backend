from typing import Optional, Any

from pydantic import BaseModel

class ApiResponse(BaseModel):
    success: bool = True
    status_code: Optional[int] = 2000
    message: Optional[str] = "요청이 성공적으로 처리되었습니다."
    data: Optional[Any] = None


class JwtToken(BaseModel):
    is_signup: bool
    nickname: str
    access_token: str