from typing import Optional
from sqlalchemy.orm import Session

from app.domain.user.repository import UserRepository
from app.domain.user.models import User
from app.domain.user.schemas import UserCreate, UserUpdate, UserResponse
from app.domain.auth.schemas import OAuthUserInfo


class UserService:
    """사용자 서비스 - 비즈니스 로직"""
    
    def __init__(self, db: Session):
        self.repository = UserRepository(db)
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """사용자 조회 (ID)"""
        return self.repository.get_by_id(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """사용자 조회 (이메일)"""
        return self.repository.get_by_email(email)
    
    def get_or_create_oauth_user(self, oauth_info: OAuthUserInfo) -> User:
        """
        OAuth 사용자 조회 또는 생성
        
        로그인 시 사용:
        - 같은 OAuth Provider + OAuth ID로 기존 사용자가 있으면 업데이트
        - 같은 이메일로 다른 OAuth Provider 계정이 있으면 기존 계정 업데이트 (연동)
        - 신규 사용자면 생성
        """
        # 1. 같은 OAuth Provider + OAuth ID로 조회
        user = self.repository.get_by_oauth(
            oauth_info.oauth_provider,
            oauth_info.oauth_id
        )
        
        if user:
            # 기존 사용자 - 마지막 로그인 업데이트
            self.repository.update_last_login(user.id)
            return user
        
        # 2. 같은 이메일로 다른 OAuth 계정이 있는지 확인
        existing_user = self.repository.get_by_email(oauth_info.email)
        
        if existing_user:
            # 같은 이메일의 기존 계정 발견
            # -> 새로운 OAuth Provider 정보로 업데이트 (계정 연동)
            user_update = UserUpdate(
                name=oauth_info.name,
                profile_image=oauth_info.profile_image,
                oauth_provider=oauth_info.oauth_provider,
                oauth_id=oauth_info.oauth_id
            )
            updated_user = self.repository.update(existing_user.id, user_update)
            self.repository.update_last_login(existing_user.id)
            return updated_user
        
        # 3. 신규 사용자 생성
        user_create = UserCreate(
            email=oauth_info.email,
            name=oauth_info.name,
            profile_image=oauth_info.profile_image,
            oauth_provider=oauth_info.oauth_provider,
            oauth_id=oauth_info.oauth_id
        )
        
        return self.repository.create(user_create)
    
    def update_user(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """사용자 정보 수정"""
        return self.repository.update(user_id, user_data)
    
    def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        return self.repository.delete(user_id)
