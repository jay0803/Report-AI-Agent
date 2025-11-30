from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode
import time

from app.infrastructure.database import get_db
from app.domain.auth.service import AuthService
from app.domain.auth.schemas import OAuthCallbackResponse, RefreshTokenRequest, Token
from app.infrastructure.oauth import google_oauth, kakao_oauth, naver_oauth
from app.core.config import settings

# Tools OAuth 토큰 저장
import sys
from pathlib import Path
tools_path = Path(__file__).resolve().parent.parent.parent.parent.parent / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

try:
    from tools.token_manager import save_token
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False

router = APIRouter()


# ========================================
# Google OAuth
# ========================================

@router.get("/google/login")
async def google_login():
    """
    Google OAuth 로그인 URL 반환
    
    프론트엔드에서 이 URL로 리다이렉트
    """
    authorization_url = google_oauth.get_authorization_url()
    return {"authorization_url": authorization_url}


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Google Authorization Code"),
    db: Session = Depends(get_db)
):
    """
    Google OAuth 콜백
    
    Google 로그인 후 리다이렉트되는 엔드포인트
    로그인 성공 시 토큰을 쿠키에 저장하고 /start로 리다이렉트
    """
    print(f"\n{'='*60}")
    print(f"🔵 Google OAuth 콜백 시작")
    print(f"{'='*60}")
    print(f"   Authorization Code 받음: {code[:20]}...")
    
    try:
        # Access Token 받기
        print(f"   1️⃣ Google에 Access Token 요청 중...")
        token_data = await google_oauth.get_access_token(code)
        print(f"   ✅ Access Token 받음")
        access_token = token_data["access_token"]
        
        # 사용자 정보 가져오기
        print(f"   2️⃣ Google에 사용자 정보 요청 중...")
        user_info = await google_oauth.get_user_info(access_token)
        print(f"   ✅ 사용자 정보 받음: {user_info.email}")
        
        # 로그인 처리 (사용자 조회/생성 + JWT 발급)
        print(f"   3️⃣ 데이터베이스에서 사용자 조회/생성 중...")
        auth_service = AuthService(db)
        result = auth_service.oauth_login(user_info)
        print(f"   ✅ 사용자 처리 완료: {result.user.email}")
        
        # OAuth 토큰 저장 (Tools 사용을 위해)
        if TOOLS_AVAILABLE:
            try:
                await save_token(
                    user_id=str(result.user.id),
                    service="google",
                    token_data={
                        "access_token": token_data.get("access_token"),
                        "refresh_token": token_data.get("refresh_token"),
                        "token_type": token_data.get("token_type", "Bearer"),
                        "expires_at": int(time.time()) + token_data.get("expires_in", 3600)
                    }
                )
                print(f"✅ Google OAuth 토큰 저장 완료 (user_id: {result.user.id})")
            except Exception as e:
                print(f"⚠️ OAuth 토큰 저장 실패: {e}")
        
        # 쿠키에 토큰 저장하고 /start로 리다이렉트
        print(f"\n{'='*60}")
        print(f"🍪 Google OAuth 콜백 - 쿠키 설정 시작")
        print(f"{'='*60}")
        print(f"   - DEBUG 모드: {settings.DEBUG}")
        
        # 개발 환경(localhost)에서는 Secure=False, SameSite=Lax로 설정해야 쿠키가 전송됨
        secure_cookie = not settings.DEBUG
        samesite_policy = "Lax" if settings.DEBUG else "None"
        
        print(f"   - Secure 설정: {secure_cookie}")
        print(f"   - SameSite 설정: {samesite_policy}")
        print(f"   - 사용자: {result.user.email} (ID: {result.user.id})")
        print(f"   - Access Token 길이: {len(result.access_token)}")
        print(f"   - Refresh Token 길이: {len(result.refresh_token)}")
        
        response = RedirectResponse(url="/start", status_code=302)
        
        # Access Token 쿠키 (HttpOnly)
        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
            domain=None
        )
        print(f"   ✅ access_token 쿠키 설정 완료")
        
        # Refresh Token 쿠키 (HttpOnly)
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
            domain=None
        )
        print(f"   ✅ refresh_token 쿠키 설정 완료")
        
        # 사용자 정보는 일반 쿠키로 (프론트엔드에서 읽을 수 있도록)
        import json
        from urllib.parse import quote
        user_data = {
            "id": result.user.id,  # ID 추가
            "email": result.user.email,
            "name": result.user.name or ""
        }
        # 한글 등 유니코드 문자를 위해 URL 인코딩
        user_json = json.dumps(user_data, ensure_ascii=False)
        user_encoded = quote(user_json)
        
        response.set_cookie(
            key="user",
            value=user_encoded,
            httponly=False,  # JavaScript에서 읽을 수 있도록
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
            domain=None
        )
        print(f"   ✅ user 쿠키 설정 완료 (URL 인코딩, ID 포함)")
        
        # 로그인 상태 확인용 쿠키 (HttpOnly=false)
        response.set_cookie(
            key="logged_in",
            value="true",
            httponly=False,  # JavaScript에서 읽을 수 있도록
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
            domain=None
        )
        print(f"   ✅ logged_in 쿠키 설정 완료")
        print(f"\n🔄 /start로 리다이렉트")
        print(f"   Set-Cookie 헤더:")
        for key, value in response.headers.items():
            if key.lower() == 'set-cookie':
                print(f"      {key}: {value[:100]}...")
        print(f"{'='*60}\n")
        
        return response
    
    except Exception as e:
        # 에러 발생 시 로그인 페이지로 리다이렉트 (에러 메시지 포함)
        print(f"\n{'='*60}")
        print(f"❌ Google OAuth 콜백 에러 발생!")
        print(f"{'='*60}")
        print(f"에러 타입: {type(e).__name__}")
        print(f"에러 메시지: {str(e)}")
        import traceback
        print(f"상세 스택:")
        traceback.print_exc()
        print(f"{'='*60}\n")
        
        error_params = {'error': str(e)}
        redirect_url = f"/login?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url)


# ========================================
# Kakao OAuth
# ========================================

@router.get("/kakao/login")
async def kakao_login():
    """Kakao OAuth 로그인 URL 반환"""
    authorization_url = kakao_oauth.get_authorization_url()
    return {"authorization_url": authorization_url}


@router.get("/kakao/callback")
async def kakao_callback(
    code: str = Query(..., description="Kakao Authorization Code"),
    db: Session = Depends(get_db)
):
    """Kakao OAuth 콜백"""
    try:
        # Access Token 받기
        token_data = await kakao_oauth.get_access_token(code)
        access_token = token_data["access_token"]
        
        # 사용자 정보 가져오기
        user_info = await kakao_oauth.get_user_info(access_token)
        
        # 로그인 처리
        auth_service = AuthService(db)
        result = auth_service.oauth_login(user_info)
        
        # 쿠키 설정 준비
        secure_cookie = not settings.DEBUG
        samesite_policy = "Lax" if settings.DEBUG else "None"
        
        # 쿠키에 토큰 저장하고 /start로 리다이렉트
        response = RedirectResponse(url="/start", status_code=302)
        
        # Access Token 쿠키
        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
            domain=None
        )
        
        # Refresh Token 쿠키
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
            domain=None
        )
        
        # 사용자 정보 쿠키
        import json
        from urllib.parse import quote
        user_data = {
            "id": result.user.id,
            "email": result.user.email,
            "name": result.user.name or ""
        }
        # 한글 등 유니코드 문자를 위해 URL 인코딩
        user_json = json.dumps(user_data, ensure_ascii=False)
        user_encoded = quote(user_json)
        
        response.set_cookie(
            key="user",
            value=user_encoded,
            httponly=False,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
            domain=None
        )
        
        # 로그인 상태 확인용 쿠키
        response.set_cookie(
            key="logged_in",
            value="true",
            httponly=False,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
            domain=None
        )
        
        print(f"✅ Kakao 로그인 성공 - 쿠키 설정 완료: {result.user.email}")
        
        return response
    
    except Exception as e:
        print(f"\n❌ Kakao OAuth 콜백 에러: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_params = {'error': str(e)}
        redirect_url = f"/login?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url)


# ========================================
# Naver OAuth
# ========================================

@router.get("/naver/login")
async def naver_login():
    """Naver OAuth 로그인 URL 반환"""
    authorization_url = naver_oauth.get_authorization_url()
    return {"authorization_url": authorization_url}


@router.get("/naver/callback")
async def naver_callback(
    code: str = Query(..., description="Naver Authorization Code"),
    state: str = Query(..., description="CSRF State"),
    db: Session = Depends(get_db)
):
    """Naver OAuth 콜백"""
    try:
        # Access Token 받기
        token_data = await naver_oauth.get_access_token(code, state)
        access_token = token_data["access_token"]
        
        # 사용자 정보 가져오기
        user_info = await naver_oauth.get_user_info(access_token)
        
        # 로그인 처리
        auth_service = AuthService(db)
        result = auth_service.oauth_login(user_info)
        
        # 쿠키 설정 준비
        secure_cookie = not settings.DEBUG
        samesite_policy = "Lax" if settings.DEBUG else "None"
        
        # 쿠키에 토큰 저장하고 /start로 리다이렉트
        response = RedirectResponse(url="/start", status_code=302)
        
        # Access Token 쿠키
        response.set_cookie(
            key="access_token",
            value=result.access_token,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
            domain=None
        )
        
        # Refresh Token 쿠키
        response.set_cookie(
            key="refresh_token",
            value=result.refresh_token,
            httponly=True,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
            domain=None
        )
        
        # 사용자 정보 쿠키
        import json
        from urllib.parse import quote
        user_data = {
            "id": result.user.id,
            "email": result.user.email,
            "name": result.user.name or ""
        }
        # 한글 등 유니코드 문자를 위해 URL 인코딩
        user_json = json.dumps(user_data, ensure_ascii=False)
        user_encoded = quote(user_json)
        
        response.set_cookie(
            key="user",
            value=user_encoded,
            httponly=False,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            path="/",
            domain=None
        )
        
        # 로그인 상태 확인용 쿠키
        response.set_cookie(
            key="logged_in",
            value="true",
            httponly=False,
            secure=secure_cookie,
            samesite=samesite_policy,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            path="/",
            domain=None
        )
        
        print(f"✅ Naver 로그인 성공 - 쿠키 설정 완료: {result.user.email}")
        
        return response
    
    except Exception as e:
        print(f"\n❌ Naver OAuth 콜백 에러: {type(e).__name__} - {str(e)}")
        import traceback
        traceback.print_exc()
        
        error_params = {'error': str(e)}
        redirect_url = f"/login?{urlencode(error_params)}"
        return RedirectResponse(url=redirect_url)


# ========================================
# Token Refresh
# ========================================

@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Refresh Token으로 새 Access Token 발급
    """
    auth_service = AuthService(db)
    return auth_service.refresh_access_token(request.refresh_token)
