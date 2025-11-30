from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import create_access_token, create_refresh_token, verify_token
from app.domain.auth.schemas import Token, OAuthUserInfo, OAuthCallbackResponse
from app.domain.user.schemas import UserResponse


class AuthService:
    """인증 서비스"""
    
    def __init__(self, db: Session):
        # UserService를 여기서 import (circular import 방지)
        from app.domain.user.service import UserService
        
        self.db = db
        self.user_service = UserService(db)
    
    def create_tokens(self, user_id: int, email: str) -> Token:
        """
        Access Token과 Refresh Token 생성
        
        Args:
            user_id: 사용자 ID
            email: 사용자 이메일
        
        Returns:
            Token 객체
        """
        # JWT 표준: sub는 문자열이어야 함
        access_token = create_access_token({"sub": str(user_id), "email": email})
        refresh_token = create_refresh_token({"sub": str(user_id)})
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer"
        )
    
    def oauth_login(self, oauth_info: OAuthUserInfo) -> OAuthCallbackResponse:
        """
        OAuth 로그인 처리
        
        Args:
            oauth_info: OAuth 제공자로부터 받은 사용자 정보
        
        Returns:
            토큰 + 사용자 정보
        """
        # 사용자 조회 또는 생성
        user = self.user_service.get_or_create_oauth_user(oauth_info)
        
        # 토큰 생성
        tokens = self.create_tokens(user.id, user.email)
        
        return OAuthCallbackResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
            user=UserResponse.model_validate(user)
        )
    
    def refresh_access_token(self, refresh_token: str) -> Token:
        """
        Refresh Token으로 새 Access Token 발급
        
        Args:
            refresh_token: Refresh Token
        
        Returns:
            새 Token 객체
        
        Raises:
            HTTPException: 토큰이 유효하지 않을 경우
        """
        # Refresh Token 검증
        payload = verify_token(refresh_token, token_type="refresh")
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        user_id = payload.get("sub")
        
        # 사용자 확인
        # sub가 문자열로 저장되므로 int로 변환
        try:
            user_id_int = int(user_id)
        except (ValueError, TypeError):
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject"
            )

        user = self.user_service.get_user_by_id(user_id_int)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # 새 토큰 생성
        return self.create_tokens(user.id, user.email)
    
    def get_current_user_id(self, token: str) -> int:
        """
        Access Token에서 사용자 ID 추출
        
        Args:
            token: Access Token
        
        Returns:
            사용자 ID
        
        Raises:
            HTTPException: 토큰이 유효하지 않을 경우
        """
        payload = verify_token(token, token_type="access")
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        try:
            return int(user_id)
        except (ValueError, TypeError):
             raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject"
            )
