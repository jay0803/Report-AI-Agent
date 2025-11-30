from typing import Optional
import httpx

from app.core.config import settings
from app.domain.auth.schemas import OAuthUserInfo


class NaverOAuthClient:
    """Naver OAuth 클라이언트"""
    
    AUTHORIZE_URL = "https://nid.naver.com/oauth2.0/authorize"
    TOKEN_URL = "https://nid.naver.com/oauth2.0/token"
    USER_INFO_URL = "https://openapi.naver.com/v1/nid/me"
    
    def __init__(self):
        self.client_id = settings.NAVER_CLIENT_ID
        self.client_secret = settings.NAVER_CLIENT_SECRET
        self.redirect_uri = settings.NAVER_REDIRECT_URI
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Naver OAuth 로그인 URL 생성
        
        Returns:
            Naver 로그인 페이지 URL
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state or "random_state"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTHORIZE_URL}?{query_string}"
    
    async def get_access_token(self, code: str, state: str) -> dict:
        """
        Authorization Code로 Access Token 받기
        
        Args:
            code: Naver에서 받은 Authorization Code
            state: CSRF 방지용 state 값
        
        Returns:
            토큰 정보 dict
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                params={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "state": state
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Access Token으로 사용자 정보 가져오기
        
        Args:
            access_token: Naver Access Token
        
        Returns:
            OAuthUserInfo 객체
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.USER_INFO_URL,
                headers={"Authorization": f"Bearer {access_token}"}
            )
            response.raise_for_status()
            data = response.json()
            
            response_data = data.get("response", {})
            
            return OAuthUserInfo(
                email=response_data.get("email"),
                name=response_data.get("name") or response_data.get("nickname"),
                profile_image=response_data.get("profile_image"),
                oauth_id=response_data.get("id"),
                oauth_provider="naver"
            )


# 싱글톤 인스턴스
naver_oauth = NaverOAuthClient()
