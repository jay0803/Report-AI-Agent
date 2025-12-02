"""
Report Export Service

보고서 PDF 생성을 위한 서비스 레이어
Repository → PDF Generator → Bytes 반환
"""
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.domain.report.daily.repository import DailyReportRepository
from app.domain.report.weekly.repository import WeeklyReportRepository
from app.domain.report.monthly.repository import MonthlyReportRepository
from app.domain.report.core.schemas import CanonicalReport

from app.reporting.pdf_generator.daily_report_pdf import DailyReportPDFGenerator
from app.reporting.pdf_generator.weekly_report_pdf import WeeklyReportPDFGenerator
from app.reporting.pdf_generator.monthly_report_pdf import MonthlyReportPDFGenerator


class ReportExportService:
    """보고서 PDF 생성 서비스"""
    
    @staticmethod
    def export_daily_pdf(
        db: Session,
        owner: str,
        report_date: date,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        일일보고서 PDF 생성
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            report_date: 보고서 날짜
            output_filename: 출력 파일명 (None이면 자동 생성)
            
        Returns:
            PDF 바이트 스트림
            
        Raises:
            ValueError: 보고서를 찾을 수 없는 경우
        """
        # DB에서 일일보고서 조회
        daily_report = DailyReportRepository.get_by_owner_and_date(db, owner, report_date)
        
        if not daily_report:
            raise ValueError(f"일일보고서를 찾을 수 없습니다: {owner} - {report_date}")
        
        # CanonicalReport로 변환
        report_json = daily_report.report_json
        report = CanonicalReport(**report_json)
        
        # PDF 생성
        generator = DailyReportPDFGenerator()
        pdf_bytes = generator.generate(report, output_filename)
        
        return pdf_bytes
    
    @staticmethod
    def export_weekly_pdf(
        db: Session,
        owner: str,
        period_start: date,
        period_end: date,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        주간보고서 PDF 생성
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            period_start: 시작일
            period_end: 종료일
            output_filename: 출력 파일명
            
        Returns:
            PDF 바이트 스트림
        """
        # DB에서 주간보고서 조회
        weekly_report = WeeklyReportRepository.get_by_owner_and_period(
            db, owner, period_start, period_end
        )
        
        if not weekly_report:
            raise ValueError(f"주간보고서를 찾을 수 없습니다: {owner} - {period_start}~{period_end}")
        
        # CanonicalReport로 변환
        report_json = weekly_report.report_json
        report = CanonicalReport(**report_json)
        
        # PDF 생성
        generator = WeeklyReportPDFGenerator()
        pdf_bytes = generator.generate(report, output_filename)
        
        return pdf_bytes
    
    @staticmethod
    def export_monthly_pdf(
        db: Session,
        owner: str,
        period_start: date,
        period_end: date,
        output_filename: Optional[str] = None
    ) -> bytes:
        """
        월간보고서 PDF 생성
        
        Args:
            db: 데이터베이스 세션
            owner: 작성자
            period_start: 시작일 (1일)
            period_end: 종료일 (말일)
            output_filename: 출력 파일명
            
        Returns:
            PDF 바이트 스트림
        """
        # DB에서 월간보고서 조회
        monthly_report = MonthlyReportRepository.get_by_owner_and_period(
            db, owner, period_start, period_end
        )
        
        if not monthly_report:
            raise ValueError(f"월간보고서를 찾을 수 없습니다: {owner} - {period_start}~{period_end}")
        
        # CanonicalReport로 변환
        report_json = monthly_report.report_json
        report = CanonicalReport(**report_json)
        
        # PDF 생성
        generator = MonthlyReportPDFGenerator()
        pdf_bytes = generator.generate(report, output_filename)
        
        return pdf_bytes
    

