from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),  # backend/.env 경로 명시
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # 정의되지 않은 환경 변수 무시
    )
    
    # Database
    DATABASE_URL: str
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # OAuth - Google
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    
    # OAuth - Kakao
    KAKAO_CLIENT_ID: str
    KAKAO_CLIENT_SECRET: str
    KAKAO_REDIRECT_URI: str
    
    # OAuth - Naver
    NAVER_CLIENT_ID: str
    NAVER_CLIENT_SECRET: str
    NAVER_REDIRECT_URI: str
    
    # OpenAI
    OPENAI_API_KEY: str
    
    # LangSmith (Optional)
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "virtual-assistant-rag"
    LANGSMITH_TRACING: str = "false"
    
    # ChromaDB
    CHROMA_PERSIST_DIRECTORY: str = "./internal_docs/chroma"
    CHROMA_COLLECTION_NAME: str = "company_manuals"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Slack
    SLACK_BOT_TOKEN: str = ""
    SLACK_SIGNING_SECRET: str = ""
    
    # Application
    APP_NAME: str = "Virtual Desk Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    API_PREFIX: str = "/api/v1"
    
    # Embedding
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSION: int = 3072
    
    # LLM
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000
    
    # File Upload
    MAX_UPLOAD_SIZE_MB: int = 10
    UPLOAD_DIR: str = "./internal_docs/uploads"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "./logs/app.log"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """CORS origins를 리스트로 반환"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# 싱글톤 설정 인스턴스
settings = Settings()
