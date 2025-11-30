"""
토큰 관리 유틸리티
OAuth 토큰 로드 및 자동 갱신 처리 (DB 연동)
"""

import os
import time
from typing import Optional, Dict, Any
import httpx


class TokenManager:
    """OAuth 토큰 관리 클래스"""
    
    def __init__(self):
        self.token_cache = {}
    
    async def load_token(self, user_id: str, service: str) -> Optional[Dict[str, Any]]:
        """
        사용자의 OAuth 토큰을 DB에서 로드
        
        Args:
            user_id: 사용자 ID (문자열)
            service: 서비스 이름 (google, slack, notion 등)
        
        Returns:
            토큰 정보 딕셔너리 또는 None
        """
        from app.infrastructure.database.session import SessionLocal
        from app.domain.user.token_models import UserToken
        
        cache_key = f"{user_id}:{service}"
        
        # 캐시에서 먼저 확인
        if cache_key in self.token_cache:
            token_data = self.token_cache[cache_key]
            
            # 토큰이 만료되지 않았으면 반환
            if token_data.get("expires_at", 0) > time.time():
                return token_data
            
            # 만료되었으면 갱신 시도
            refreshed = await self._refresh_token(user_id, service, token_data)
            if refreshed:
                return refreshed
        
        # DB에서 로드
        db = SessionLocal()
        try:
            user_id_int = int(user_id)
            token_record = db.query(UserToken).filter(
                UserToken.user_id == user_id_int,
                UserToken.service == service
            ).first()
            
            if not token_record:
                return None
            
            token_data = {
                "access_token": token_record.access_token,
                "refresh_token": token_record.refresh_token,
                "expires_at": token_record.expires_at or 0,
                "token_type": token_record.token_type or "Bearer",
            }
            
            # 캐시에 저장
            self.token_cache[cache_key] = token_data
            
            # 만료 확인
            if token_data.get("expires_at", 0) > 0 and token_data["expires_at"] < time.time():
                # 만료되었으면 갱신 시도
                refreshed = await self._refresh_token(user_id, service, token_data)
                if refreshed:
                    return refreshed
            
            return token_data
        
        except Exception as e:
            print(f"토큰 로드 실패: {str(e)}")
            return None
        finally:
            db.close()
    
    async def _refresh_token(
        self, 
        user_id: str, 
        service: str, 
        token_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        만료된 토큰을 refresh_token으로 갱신
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름
            token_data: 기존 토큰 데이터
        
        Returns:
            갱신된 토큰 정보 또는 None
        """
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            return None
        
        try:
            if service == "google":
                # Google OAuth 토큰 갱신
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                            "refresh_token": refresh_token,
                            "grant_type": "refresh_token",
                        }
                    )
                    
                    if response.status_code == 200:
                        new_token = response.json()
                        new_token_data = {
                            "access_token": new_token["access_token"],
                            "refresh_token": refresh_token,  # refresh_token은 유지
                            "expires_at": time.time() + new_token.get("expires_in", 3600),
                            "token_type": new_token.get("token_type", "Bearer"),
                        }
                        
                        # 캐시 및 DB 업데이트
                        cache_key = f"{user_id}:{service}"
                        self.token_cache[cache_key] = new_token_data
                        
                        # DB에 저장
                        await self.save_token(user_id, service, new_token_data)
                        
                        return new_token_data
            
            elif service == "slack":
                # Slack은 토큰이 만료되지 않음 (revoke만 가능)
                return token_data
            
            elif service == "notion":
                # Notion도 토큰이 만료되지 않음
                return token_data
        
        except Exception as e:
            print(f"토큰 갱신 실패: {service} - {str(e)}")
            return None
        
        return None
    
    async def save_token(
        self, 
        user_id: str, 
        service: str, 
        token_data: Dict[str, Any]
    ) -> bool:
        """
        토큰을 DB에 저장 (캐시도 업데이트)
        
        Args:
            user_id: 사용자 ID
            service: 서비스 이름
            token_data: 토큰 데이터
        
        Returns:
            성공 여부
        """
        from app.infrastructure.database.session import SessionLocal
        from app.domain.user.token_models import UserToken
        
        try:
            cache_key = f"{user_id}:{service}"
            self.token_cache[cache_key] = token_data
            
            # DB에 저장
            db = SessionLocal()
            try:
                user_id_int = int(user_id)
                
                # 기존 토큰 확인
                existing_token = db.query(UserToken).filter(
                    UserToken.user_id == user_id_int,
                    UserToken.service == service
                ).first()
                
                if existing_token:
                    # 업데이트
                    existing_token.access_token = token_data.get("access_token")
                    existing_token.refresh_token = token_data.get("refresh_token")
                    existing_token.token_type = token_data.get("token_type", "Bearer")
                    existing_token.expires_at = token_data.get("expires_at")
                else:
                    # 새로 생성
                    new_token = UserToken(
                        user_id=user_id_int,
                        service=service,
                        access_token=token_data.get("access_token"),
                        refresh_token=token_data.get("refresh_token"),
                        token_type=token_data.get("token_type", "Bearer"),
                        expires_at=token_data.get("expires_at")
                    )
                    db.add(new_token)
                
                db.commit()
                return True
            
            finally:
                db.close()
        
        except Exception as e:
            print(f"토큰 저장 실패: {str(e)}")
            return False


# 싱글톤 인스턴스
_token_manager = TokenManager()


async def load_token(user_id: str, service: str) -> Optional[Dict[str, Any]]:
    """토큰 로드 헬퍼 함수"""
    return await _token_manager.load_token(user_id, service)


async def save_token(user_id: str, service: str, token_data: Dict[str, Any]) -> bool:
    """토큰 저장 헬퍼 함수"""
    return await _token_manager.save_token(user_id, service, token_data)

