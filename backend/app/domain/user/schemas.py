from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """사용자 기본 스키마"""
    email: EmailStr
    name: Optional[str] = None
    profile_image: Optional[str] = None


class UserCreate(UserBase):
    """사용자 생성 스키마"""
    oauth_provider: str
    oauth_id: str


class UserUpdate(BaseModel):
    """사용자 수정 스키마"""
    name: Optional[str] = None
    profile_image: Optional[str] = None


class UserResponse(UserBase):
    """사용자 응답 스키마"""
    id: int
    oauth_provider: str
    created_at: datetime
    last_login_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # SQLAlchemy 모델을 Pydantic 모델로 변환 가능


class UserInDB(UserResponse):
    """DB에 저장된 사용자 (내부 사용)"""
    oauth_id: str
    updated_at: datetime
