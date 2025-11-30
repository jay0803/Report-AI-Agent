"""
OAuth Token 저장 모델
외부 서비스(Google, Slack, Notion) OAuth 토큰 관리
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from app.infrastructure.database.session import Base


class UserToken(Base):
    """사용자 OAuth 토큰 모델"""
    
    __tablename__ = "user_tokens"
    
    # 기본 필드
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="사용자 ID")
    service = Column(String(50), nullable=False, index=True, comment="서비스명 (google, slack, notion)")
    
    # 토큰 정보
    access_token = Column(Text, nullable=False, comment="Access Token")
    refresh_token = Column(Text, nullable=True, comment="Refresh Token")
    token_type = Column(String(50), default="Bearer", comment="토큰 타입")
    expires_at = Column(Integer, nullable=True, comment="만료 시간 (Unix timestamp)")
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="생성일시")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="수정일시")
    
    def __repr__(self):
        return f"<UserToken(user_id={self.user_id}, service={self.service})>"
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "service": self.service,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

