from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from pathlib import Path
import sys
from dotenv import load_dotenv

# .env 파일 로드 (backend 폴더 기준)
BACKEND_DIR = Path(__file__).resolve().parent.parent
env_file = BACKEND_DIR / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file)
    print(f"✅ .env 파일 로드 완료: {env_file}")
else:
    print(f"⚠️  .env 파일을 찾을 수 없습니다: {env_file}")

from app.core.config import settings
from app.api.v1 import api_router
from app.infrastructure.database import engine, Base

# 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # Virtual-Assistant 루트

# Tools Router 추가
import sys
from pathlib import Path
tools_path = Path(__file__).resolve().parent.parent.parent / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

try:
    from tools.router import tools_router
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False
    print("⚠️ Tools module not available.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 시작/종료 시 실행되는 함수
    """
    # 시작 시
    print("🚀 Starting Virtual Desk Assistant API...")
    print(f"📊 Database: {settings.DATABASE_URL}")
    
    # 데이터베이스 테이블 생성 (개발용)
    # 프로덕션에서는 Alembic 마이그레이션 사용
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    yield
    
    # 종료 시
    print("👋 Shutting down...")


# FastAPI 앱 생성
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered Multi-Agent Virtual Desktop Assistant",
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API 라우터 등록
app.include_router(api_router, prefix=settings.API_PREFIX)

# Tools 라우터 등록
if TOOLS_AVAILABLE:
    app.include_router(tools_router, prefix="/api/tools", tags=["tools"])


# 정적 파일 경로 설정
FRONTEND_DIR = BASE_DIR / "frontend"
PUBLIC_DIR = BASE_DIR / "public"
RENDERER_DIR = BASE_DIR / "renderer"

# 정적 파일 서빙
app.mount("/public", StaticFiles(directory=str(PUBLIC_DIR)), name="public")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
app.mount("/renderer", StaticFiles(directory=str(RENDERER_DIR)), name="renderer")


# Health Check
@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


@app.get("/")
async def root():
    """루트 엔드포인트 - 로그인 후 시작 페이지"""
    start_page = FRONTEND_DIR / "Start" / "index.html"
    if start_page.exists():
        return FileResponse(start_page)
    else:
        return {
            "message": "Welcome to Virtual Desk Assistant API",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health"
        }


@app.get("/login")
async def login_page():
    """로그인 페이지"""
    login_page = FRONTEND_DIR / "Login" / "index.html"
    if login_page.exists():
        return FileResponse(login_page)
    else:
        return {"error": "Login page not found"}


@app.get("/start")
async def start_page():
    """시작 페이지 (로그인 완료 후)"""
    start_page = FRONTEND_DIR / "Start" / "index.html"
    if start_page.exists():
        return FileResponse(start_page)
    else:
        return {"error": "Start page not found"}


@app.get("/main")
async def main_page():
    """메인 페이지 - 캐릭터 화면 (일렉트론용)"""
    main_page = BASE_DIR / "index.html"
    if main_page.exists():
        return FileResponse(main_page)
    else:
        return {"error": "Main page not found"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
