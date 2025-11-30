"""
Daily Report 모델

PostgreSQL에 일일보고서를 저장하는 운영 DB 모델
"""
from sqlalchemy import Column, String, Date, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid

from app.infrastructure.database.session import Base


class DailyReport(Base):
    """일일보고서 모델"""
    
    __tablename__ = "daily_reports"
    
    # 기본 필드
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="보고서 ID"
    )
    owner = Column(
        String(100), 
        nullable=False, 
        index=True,
        comment="작성자"
    )
    date = Column(
        Date, 
        nullable=False, 
        index=True,
        comment="보고서 날짜 (YYYY-MM-DD)"
    )
    report_json = Column(
        JSONB, 
        nullable=False,
        comment="CanonicalReport JSON"
    )
    
    # 타임스탬프
    created_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(),
        comment="생성일시"
    )
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now(),
        comment="수정일시"
    )
    
    # UNIQUE 제약조건: owner + date 조합은 유일해야 함
    __table_args__ = (
        UniqueConstraint('owner', 'date', name='uq_daily_report_owner_date'),
    )
    
    def __repr__(self):
        return f"<DailyReport(id={self.id}, owner={self.owner}, date={self.date})>"
    
    def to_dict(self):
        """딕셔너리로 변환"""
        return {
            "id": str(self.id),
            "owner": self.owner,
            "date": self.date.isoformat() if self.date else None,
            "report_json": self.report_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

