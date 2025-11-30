from typing import Optional
import httpx

from app.core.config import settings
from app.domain.auth.schemas import OAuthUserInfo


class KakaoOAuthClient:
    """Kakao OAuth 클라이언트"""
    
    AUTHORIZE_URL = "https://kauth.kakao.com/oauth/authorize"
    TOKEN_URL = "https://kauth.kakao.com/oauth/token"
    USER_INFO_URL = "https://kapi.kakao.com/v2/user/me"
    
    def __init__(self):
        self.client_id = settings.KAKAO_CLIENT_ID
        self.client_secret = settings.KAKAO_CLIENT_SECRET
        self.redirect_uri = settings.KAKAO_REDIRECT_URI
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Kakao OAuth 로그인 URL 생성
        
        Returns:
            Kakao 로그인 페이지 URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "profile_nickname,profile_image,account_email"
        }
        
        if state:
            params["state"] = state
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTHORIZE_URL}?{query_string}"
    
    async def get_access_token(self, code: str) -> dict:
        """
        Authorization Code로 Access Token 받기
        
        Args:
            code: Kakao에서 받은 Authorization Code
        
        Returns:
            토큰 정보 dict
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            return response.json()
    
    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """
        Access Token으로 사용자 정보 가져오기
        
        Args:
            access_token: Kakao Access Token
        
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
            
            kakao_account = data.get("kakao_account", {})
            profile = kakao_account.get("profile", {})
            
            return OAuthUserInfo(
                email=kakao_account.get("email"),
                name=profile.get("nickname"),
                profile_image=profile.get("profile_image_url"),
                oauth_id=str(data["id"]),
                oauth_provider="kakao"
            )


# 싱글톤 인스턴스
kakao_oauth = KakaoOAuthClient()
