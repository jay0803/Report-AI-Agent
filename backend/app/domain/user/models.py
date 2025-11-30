from sqlalchemy import Column, String, DateTime, Enum as SQLEnum, Integer
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base
import enum


class OAuthProvider(enum.Enum):
    """OAuth 제공자"""
    GOOGLE = "google"
    KAKAO = "kakao"
    NAVER = "naver"


class User(Base):
    """사용자 모델"""
    
    __tablename__ = "users"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False, comment="이메일")
    name = Column(String(100), nullable=True, comment="사용자 이름")
    profile_image = Column(String(500), nullable=True, comment="프로필 이미지 URL")
    
    # OAuth 관련
    oauth_provider = Column(SQLEnum(OAuthProvider), nullable=False, comment="OAuth 제공자")
    oauth_id = Column(String(255), nullable=False, comment="OAuth 제공자의 사용자 ID")
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    last_login_at = Column(DateTime(timezone=True), nullable=True, comment="마지막 로그인 일시")
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, provider={self.oauth_provider.value})>"
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "profile_image": self.profile_image,
            "oauth_provider": self.oauth_provider.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None
        }
