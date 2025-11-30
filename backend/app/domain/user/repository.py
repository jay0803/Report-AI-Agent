from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from app.domain.user.models import User, OAuthProvider
from app.domain.user.schemas import UserCreate, UserUpdate


class UserRepository:
    """사용자 Repository"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """ID로 사용자 조회"""
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        """이메일로 사용자 조회"""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_by_oauth(self, oauth_provider: str, oauth_id: str) -> Optional[User]:
        """OAuth 정보로 사용자 조회"""
        return self.db.query(User).filter(
            and_(
                User.oauth_provider == OAuthProvider(oauth_provider),
                User.oauth_id == oauth_id
            )
        ).first()
    
    def create(self, user_data: UserCreate) -> User:
        """사용자 생성"""
        user = User(
            email=user_data.email,
            name=user_data.name,
            profile_image=user_data.profile_image,
            oauth_provider=OAuthProvider(user_data.oauth_provider),
            oauth_id=user_data.oauth_id,
            last_login_at=datetime.utcnow()
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update(self, user_id: int, user_data: UserUpdate) -> Optional[User]:
        """사용자 정보 수정"""
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def update_last_login(self, user_id: int) -> Optional[User]:
        """마지막 로그인 시간 업데이트"""
        user = self.get_by_id(user_id)
        if not user:
            return None
        
        user.last_login_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete(self, user_id: int) -> bool:
        """사용자 삭제"""
        user = self.get_by_id(user_id)
        if not user:
            return False
        
        self.db.delete(user)
        self.db.commit()
        return True
    
    def exists_by_email(self, email: str) -> bool:
        """이메일로 사용자 존재 여부 확인"""
        return self.db.query(User).filter(User.email == email).count() > 0
