"""
Weekly Report API

주간 보고서 자동 생성 API

Author: AI Assistant
Created: 2025-11-19
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import date
from sqlalchemy.orm import Session
from pathlib import Path
import os

from app.domain.weekly.chain import generate_weekly_report
from app.domain.weekly.repository import WeeklyReportRepository
from app.domain.weekly.schemas import WeeklyReportCreate, WeeklyReportResponse, WeeklyReportListResponse
from app.domain.report.schemas import CanonicalReport
from app.infrastructure.database.session import get_db
from app.reporting.pdf_generator.weekly_report_pdf import WeeklyReportPDFGenerator


router = APIRouter(prefix="/weekly", tags=["weekly_report"])


class WeeklyReportGenerateRequest(BaseModel):
    """주간 보고서 생성 요청"""
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="기준 날짜 (해당 주의 아무 날짜)")


class WeeklyReportGenerateResponse(BaseModel):
    """주간 보고서 생성 응답"""
    success: bool
    message: str
    report: CanonicalReport


@router.post("/generate", response_model=WeeklyReportGenerateResponse)
async def generate_weekly(
    request: WeeklyReportGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    주간 보고서 자동 생성
    
    target_date가 속한 주의 월~금 일일보고서를 집계하여 주간 보고서를 생성하고 DB에 저장합니다.
    """
    try:
        # 1. 주간 보고서 생성
        report = generate_weekly_report(
            db=db,
            owner=request.owner,
            target_date=request.target_date
        )
        
        # 2. DB에 저장
        report_dict = report.model_dump(mode='json')
        report_create = WeeklyReportCreate(
            owner=report.owner,
            period_start=report.period_start,
            period_end=report.period_end,
            report_json=report_dict
        )
        
        db_report, is_created = WeeklyReportRepository.create_or_update(
            db, report_create
        )
        
        action = "생성" if is_created else "업데이트"
        print(f"💾 주간 보고서 저장 완료 ({action}): {report.owner} - {report.period_start}~{report.period_end}")
        
        # 🔥 3. PDF 자동 생성 및 저장
        try:
            # PDF 생성 (파일명만 지정, 경로는 Generator가 처리)
            pdf_filename = f"{report.owner}_{report.period_start}_{report.period_end}_주간보고서.pdf"
            
            pdf_generator = WeeklyReportPDFGenerator()
            pdf_bytes = pdf_generator.generate(report, pdf_filename)
            
            print(f"📄 주간 보고서 PDF 생성 완료: backend/output/report_result/weekly/{pdf_filename}")
        except Exception as pdf_error:
            print(f"⚠️  PDF 생성 실패 (보고서는 저장됨): {str(pdf_error)}")
        
        return WeeklyReportGenerateResponse(
            success=True,
            message=f"주간 보고서가 {action}되었습니다.",
            report=report
        )
    
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주간 보고서 생성 실패: {str(e)}")


@router.get("/list/{owner}", response_model=WeeklyReportListResponse)
async def list_weekly_reports(
    owner: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    작성자의 주간 보고서 목록 조회
    """
    try:
        reports = WeeklyReportRepository.list_by_owner(db, owner, skip, limit)
        total = WeeklyReportRepository.count_by_owner(db, owner)
        
        report_responses = [WeeklyReportResponse(**report.to_dict()) for report in reports]
        
        return WeeklyReportListResponse(
            total=total,
            reports=report_responses
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"목록 조회 실패: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "weekly_report"}

