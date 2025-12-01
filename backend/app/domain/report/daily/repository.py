"""
Daily Report Repository (CRUD)

일일보고서 데이터베이스 CRUD 연산
"""
from datetime import date
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.domain.report.daily.models import DailyReport
from app.domain.report.daily.schemas import DailyReportCreate, DailyReportUpdate


class DailyReportRepository:
    """일일보고서 Repository"""
    
    @staticmethod
    def get_by_owner_and_date(
        db: Session,
        owner: str,
        report_date: date
    ) -> Optional[DailyReport]:
        """
        작성자와 날짜로 보고서 조회
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            report_date: 보고서 날짜
            
        Returns:
            DailyReport 또는 None
        """
        return db.query(DailyReport).filter(
            DailyReport.owner == owner,
            DailyReport.date == report_date
        ).first()
    
    @staticmethod
    def list_by_owner(
        db: Session,
        owner: str,
        skip: int = 0,
        limit: int = 100
    ) -> List[DailyReport]:
        """
        작성자의 모든 보고서 조회 (최신순)
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            skip: 건너뛸 개수
            limit: 최대 개수
            
        Returns:
            DailyReport 리스트
        """
        return db.query(DailyReport).filter(
            DailyReport.owner == owner
        ).order_by(
            DailyReport.date.desc()
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def list_by_owner_and_date_range(
        db: Session,
        owner: str,
        start_date: date,
        end_date: date
    ) -> List[DailyReport]:
        """
        작성자와 날짜 범위로 보고서 조회
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            start_date: 시작 날짜
            end_date: 종료 날짜
            
        Returns:
            DailyReport 리스트 (날짜순 정렬)
        """
        return db.query(DailyReport).filter(
            DailyReport.owner == owner,
            DailyReport.date >= start_date,
            DailyReport.date <= end_date
        ).order_by(
            DailyReport.date.asc()
        ).all()
    
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
        return db.query(DailyReport).filter(
            DailyReport.owner == owner
        ).count()
    
    @staticmethod
    def create(
        db: Session,
        report_create: DailyReportCreate
    ) -> DailyReport:
        """
        보고서 생성
        
        Args:
            db: 데이터베이스 세션
            report_create: 생성 요청 데이터
            
        Returns:
            생성된 DailyReport
            
        Raises:
            IntegrityError: owner + date 중복 시
        """
        db_report = DailyReport(
            owner=report_create.owner,
            date=report_create.report_date,
            report_json=report_create.report_json
        )
        db.add(db_report)
        db.commit()
        db.refresh(db_report)
        return db_report
    
    @staticmethod
    def update(
        db: Session,
        db_report: DailyReport,
        report_update: DailyReportUpdate
    ) -> DailyReport:
        """
        보고서 수정
        
        Args:
            db: 데이터베이스 세션
            db_report: 기존 보고서
            report_update: 수정 데이터
            
        Returns:
            수정된 DailyReport
        """
        db_report.report_json = report_update.report_json
        db.commit()
        db.refresh(db_report)
        return db_report
    
    @staticmethod
    def create_or_update(
        db: Session,
        report_create: DailyReportCreate
    ) -> tuple[DailyReport, bool]:
        """
        보고서 생성 또는 수정 (UPSERT)
        
        owner + date 조합이 이미 존재하면 update,
        없으면 create
        
        Args:
            db: 데이터베이스 세션
            report_create: 보고서 데이터
            
        Returns:
            (DailyReport, is_created: bool)
            is_created = True이면 새로 생성, False이면 업데이트
        """
        # 기존 보고서 조회
        existing = DailyReportRepository.get_by_owner_and_date(
            db,
            report_create.owner,
            report_create.report_date
        )
        
        if existing:
            # 업데이트
            update_data = DailyReportUpdate(report_json=report_create.report_json)
            updated = DailyReportRepository.update(db, existing, update_data)
            return (updated, False)
        else:
            # 생성
            created = DailyReportRepository.create(db, report_create)
            return (created, True)
    
    @staticmethod
    def delete(db: Session, db_report: DailyReport) -> None:
        """
        보고서 삭제
        
        Args:
            db: 데이터베이스 세션
            db_report: 삭제할 보고서
        """
        db.delete(db_report)
        db.commit()

