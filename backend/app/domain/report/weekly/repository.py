"""
Weekly Report Repository (CRUD)

주간보고서 데이터베이스 CRUD 연산
"""
from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session

from app.domain.report.weekly.models import WeeklyReport
from app.domain.report.weekly.schemas import WeeklyReportCreate, WeeklyReportUpdate


class WeeklyReportRepository:
    """주간보고서 Repository"""
    
    @staticmethod
    def get_by_owner_and_period(
        db: Session,
        owner: str,
        period_start: date,
        period_end: date
    ) -> Optional[WeeklyReport]:
        """
        작성자와 기간으로 보고서 조회
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            period_start: 시작일
            period_end: 종료일
            
        Returns:
            WeeklyReport 또는 None
        """
        return db.query(WeeklyReport).filter(
            WeeklyReport.owner == owner,
            WeeklyReport.period_start == period_start,
            WeeklyReport.period_end == period_end
        ).first()
    
    @staticmethod
    def list_by_owner(
        db: Session,
        owner: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[WeeklyReport]:
        """
        작성자의 모든 보고서 조회 (최신순)
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            skip: 건너뛸 개수
            limit: 최대 개수
            
        Returns:
            WeeklyReport 리스트
        """
        return db.query(WeeklyReport).filter(
            WeeklyReport.owner == owner
        ).order_by(
            WeeklyReport.period_start.desc()
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
        return db.query(WeeklyReport).filter(
            WeeklyReport.owner == owner
        ).count()
    
    @staticmethod
    def list_by_owner_and_period_range(
        db: Session,
        owner: str,
        period_start: date,
        period_end: date
    ) -> List[WeeklyReport]:
        """
        작성자와 기간 범위로 주간보고서 조회
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            period_start: 시작일
            period_end: 종료일
            
        Returns:
            WeeklyReport 리스트 (기간순 정렬)
        """
        return db.query(WeeklyReport).filter(
            WeeklyReport.owner == owner,
            WeeklyReport.period_start >= period_start,
            WeeklyReport.period_end <= period_end
        ).order_by(
            WeeklyReport.period_start.asc()
        ).all()
    
    @staticmethod
    def create(
        db: Session,
        report_create: WeeklyReportCreate
    ) -> WeeklyReport:
        """
        보고서 생성
        
        Args:
            db: 데이터베이스 세션
            report_create: 생성 요청 데이터
            
        Returns:
            생성된 WeeklyReport
        """
        db_report = WeeklyReport(
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
        db_report: WeeklyReport,
        report_update: WeeklyReportUpdate
    ) -> WeeklyReport:
        """
        보고서 수정
        
        Args:
            db: 데이터베이스 세션
            db_report: 기존 보고서
            report_update: 수정 데이터
            
        Returns:
            수정된 WeeklyReport
        """
        db_report.report_json = report_update.report_json
        db.commit()
        db.refresh(db_report)
        return db_report
    
    @staticmethod
    def create_or_update(
        db: Session,
        report_create: WeeklyReportCreate
    ) -> tuple[WeeklyReport, bool]:
        """
        보고서 생성 또는 수정 (UPSERT)
        
        Args:
            db: 데이터베이스 세션
            report_create: 보고서 데이터
            
        Returns:
            (WeeklyReport, is_created: bool)
        """
        existing = WeeklyReportRepository.get_by_owner_and_period(
            db,
            report_create.owner,
            report_create.period_start,
            report_create.period_end
        )
        
        if existing:
            update_data = WeeklyReportUpdate(report_json=report_create.report_json)
            updated = WeeklyReportRepository.update(db, existing, update_data)
            return (updated, False)
        else:
            created = WeeklyReportRepository.create(db, report_create)
            return (created, True)
    
    @staticmethod
    def delete(db: Session, db_report: WeeklyReport) -> None:
        """
        보고서 삭제
        
        Args:
            db: 데이터베이스 세션
            db_report: 삭제할 보고서
        """
        db.delete(db_report)
        db.commit()

