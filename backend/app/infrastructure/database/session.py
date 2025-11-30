from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# SQLAlchemy 엔진 생성
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,           # 🔥 SQL 쿼리 로깅 비활성화 (너무 번잡함)
    pool_pre_ping=True,   # 연결 유효성 체크
    pool_size=10,         # 커넥션 풀 크기
    max_overflow=20       # 최대 추가 연결 수
)

# 세션 팩토리
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base 클래스 (모든 모델의 부모)
Base = declarative_base()


def get_db():
    """
    데이터베이스 세션 의존성
    
    FastAPI 엔드포인트에서 사용:
    @app.get("/users")
    def get_users(db: Session = Depends(get_db)):
        ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
