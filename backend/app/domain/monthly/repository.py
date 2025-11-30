"""
Monthly Report Repository (CRUD)

월간보고서 데이터베이스 CRUD 연산
"""
from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.monthly.models import MonthlyReport
from app.domain.monthly.schemas import MonthlyReportCreate, MonthlyReportUpdate


class MonthlyReportRepository:
    """월간보고서 Repository"""
    
    @staticmethod
    def get_by_owner_and_period(
        db: Session,
        owner: str,
        period_start: date,
        period_end: date
    ) -> Optional[MonthlyReport]:
        """
        작성자와 기간으로 보고서 조회
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            period_start: 시작일
            period_end: 종료일
            
        Returns:
            MonthlyReport 또는 None
        """
        return db.query(MonthlyReport).filter(
            MonthlyReport.owner == owner,
            MonthlyReport.period_start == period_start,
            MonthlyReport.period_end == period_end
        ).first()
    
    @staticmethod
    def list_by_owner(
        db: Session,
        owner: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[MonthlyReport]:
        """
        작성자의 모든 보고서 조회 (최신순)
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            skip: 건너뛸 개수
            limit: 최대 개수
            
        Returns:
            MonthlyReport 리스트
        """
        return db.query(MonthlyReport).filter(
            MonthlyReport.owner == owner
        ).order_by(
            MonthlyReport.period_start.desc()
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def count_by_owner(db: Session, owner: str) -> int:
        """
        작성자의 보고서 개수
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            
        Returns:
            보고서 개수
        """
        return db.query(MonthlyReport).filter(
            MonthlyReport.owner == owner
        ).count()
    
    @staticmethod
    def create(
        db: Session,
        report_create: MonthlyReportCreate
    ) -> MonthlyReport:
        """
        보고서 생성
        
        Args:
            db: 데이터베이스 세션
            report_create: 생성 요청 데이터
            
        Returns:
            생성된 MonthlyReport
        """
        db_report = MonthlyReport(
            owner=report_create.owner,
            period_start=report_create.period_start,
            period_end=report_create.period_end,
            report_json=report_create.report_json
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report
    
    @staticmethod
    def update(
        db: Session,
        db_report: MonthlyReport,
        report_update: MonthlyReportUpdate
    ) -> MonthlyReport:
        """
        보고서 수정
        
        Args:
            db: 데이터베이스 세션
            db_report: 기존 보고서
            report_update: 수정 데이터
            
        Returns:
            수정된 MonthlyReport
        """
        db_report.report_json = report_update.report_json
        db.commit()
        db.refresh(db_report)
        return db_report
    
    @staticmethod
    def create_or_update(
        db: Session,
        report_create: MonthlyReportCreate
    ) -> tuple[MonthlyReport, bool]:
        """
        보고서 생성 또는 수정 (UPSERT)
        
        Args:
            db: 데이터베이스 세션
            report_create: 보고서 데이터
            
        Returns:
            (MonthlyReport, is_created: bool)
        """
        existing = MonthlyReportRepository.get_by_owner_and_period(
            db,
            report_create.owner,
            report_create.period_start,
            report_create.period_end
        )
        
        if existing:
            update_data = MonthlyReportUpdate(report_json=report_create.report_json)
            updated = MonthlyReportRepository.update(db, existing, update_data)
            return (updated, False)
        else:
            created = MonthlyReportRepository.create(db, report_create)
            return (created, True)
    
    @staticmethod
    def delete(db: Session, db_report: MonthlyReport) -> None:
        """
        보고서 삭제
        
        Args:
            db: 데이터베이스 세션
            db_report: 삭제할 보고서
        """
        db.delete(db_report)
        db.commit()

