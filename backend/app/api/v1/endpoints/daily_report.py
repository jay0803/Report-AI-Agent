"""
Daily Report API 엔드포인트

일일보고서 운영 DB 저장/조회 API
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import date
from typing import Dict, Any

from app.infrastructure.database.session import get_db
from app.domain.daily.repository import DailyReportRepository
from app.domain.daily.schemas import (
    DailyReportCreate,
    DailyReportResponse,
    DailyReportListResponse
)
from app.domain.report.schemas import CanonicalReport


router = APIRouter(prefix="/daily-report", tags=["daily-report"])


@router.post("", response_model=DailyReportResponse, status_code=201)
async def save_daily_report(
    report: CanonicalReport,
    db: Session = Depends(get_db)
):
    """
    일일보고서 저장 (생성 또는 업데이트)
    
    - owner + date 조합이 이미 존재하면 업데이트
    - 없으면 새로 생성
    
    Args:
        report: CanonicalReport (전체 JSON)
        db: 데이터베이스 세션
        
    Returns:
        저장된 DailyReportResponse
    """
    try:
        # CanonicalReport를 dict로 변환
        report_dict = report.model_dump(mode='json')
        
        # owner와 date 추출
        owner = report.owner
        report_date = report.period_start  # daily는 period_start == period_end
        
        if not owner:
            raise HTTPException(
                status_code=400,
                detail="owner 필드가 필요합니다."
            )
        
        if not report_date:
            raise HTTPException(
                status_code=400,
                detail="period_start 필드가 필요합니다."
            )
        
        # 생성 요청 데이터 준비
        report_create = DailyReportCreate(
            owner=owner,
            date=report_date,
            report_json=report_dict
        )
        
        # UPSERT 실행
        db_report, is_created = DailyReportRepository.create_or_update(
            db, report_create
        )
        
        action = "생성" if is_created else "업데이트"
        print(f"✅ 일일보고서 {action}: {owner} - {report_date}")
        
        return DailyReportResponse.model_validate(db_report)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 일일보고서 저장 실패: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"일일보고서 저장 실패: {str(e)}"
        )


@router.get("/{owner}/{date}", response_model=DailyReportResponse)
async def get_daily_report(
    owner: str,
    date: date,
    db: Session = Depends(get_db)
):
    """
    일일보고서 조회 (owner + date)
    
    Args:
        owner: 작성자
        date: 보고서 날짜 (YYYY-MM-DD)
        db: 데이터베이스 세션
        
    Returns:
        DailyReportResponse
    """
    db_report = DailyReportRepository.get_by_owner_and_date(
        db, owner, date
    )
    
    if not db_report:
        raise HTTPException(
            status_code=404,
            detail=f"{owner}의 {date} 일일보고서를 찾을 수 없습니다."
        )
    
    return DailyReportResponse.model_validate(db_report)


@router.get("/list/{owner}", response_model=DailyReportListResponse)
async def list_daily_reports(
    owner: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    작성자의 일일보고서 목록 조회 (최신순)
    
    Args:
        owner: 작성자
        skip: 건너뛸 개수 (페이징)
        limit: 최대 개수 (기본 100)
        db: 데이터베이스 세션
        
    Returns:
        DailyReportListResponse
    """
    reports = DailyReportRepository.list_by_owner(
        db, owner, skip=skip, limit=limit
    )
    total = DailyReportRepository.count_by_owner(db, owner)
    
    return DailyReportListResponse(
        total=total,
        reports=[DailyReportResponse.model_validate(r) for r in reports]
    )


@router.delete("/{owner}/{date}", status_code=204)
async def delete_daily_report(
    owner: str,
    date: date,
    db: Session = Depends(get_db)
):
    """
    일일보고서 삭제
    
    Args:
        owner: 작성자
        date: 보고서 날짜
        db: 데이터베이스 세션
    """
    db_report = DailyReportRepository.get_by_owner_and_date(
        db, owner, date
    )
    
    if not db_report:
        raise HTTPException(
            status_code=404,
            detail=f"{owner}의 {date} 일일보고서를 찾을 수 없습니다."
        )
    
    DailyReportRepository.delete(db, db_report)
    print(f"🗑️  일일보고서 삭제: {owner} - {date}")
    
    return None


@router.get("/health")
async def health_check():
    """Health check"""
    return {"status": "ok", "service": "daily-report"}

