"""
모든 SQLAlchemy 모델을 import하는 파일
Alembic이 자동으로 마이그레이션을 생성할 수 있도록 함
"""

from app.infrastructure.database.session import Base

# 여기에 모든 모델을 import
from app.domain.user.models import User
from app.domain.report.daily.models import DailyReport

__all__ = ["Base", "User", "DailyReport"]
