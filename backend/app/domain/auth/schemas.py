from pydantic import BaseModel
from typing import Optional
from app.domain.user.schemas import UserResponse


class Token(BaseModel):
    """토큰 응답 스키마"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """토큰 페이로드"""
    sub: int  # user_id
    email: str
    exp: Optional[int] = None


class OAuthCallbackResponse(BaseModel):
    """OAuth 콜백 응답"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """Refresh Token 요청"""
    refresh_token: str


class OAuthUserInfo(BaseModel):
    """OAuth 제공자로부터 받은 사용자 정보"""
    email: str
    name: Optional[str] = None
    profile_image: Optional[str] = None
    oauth_id: str
    oauth_provider: str
