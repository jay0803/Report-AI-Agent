"""
Weekly Report Pydantic 스키마
"""
from datetime import date, datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID


class WeeklyReportCreate(BaseModel):
    """주간보고서 생성 요청"""
    owner: str = Field(..., description="작성자")
    period_start: date = Field(..., description="시작일")
    period_end: date = Field(..., description="종료일")
    report_json: Dict[str, Any] = Field(..., description="CanonicalReport JSON")


class WeeklyReportUpdate(BaseModel):
    """주간보고서 수정 요청"""
    report_json: Dict[str, Any] = Field(..., description="CanonicalReport JSON")


class WeeklyReportResponse(BaseModel):
    """주간보고서 응답"""
    id: UUID = Field(..., description="보고서 ID")
    owner: str = Field(..., description="작성자")
    period_start: date = Field(..., description="시작일")
    period_end: date = Field(..., description="종료일")
    report_json: Dict[str, Any] = Field(..., description="CanonicalReport JSON")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")
    
    class Config:
        from_attributes = True


class WeeklyReportListResponse(BaseModel):
    """주간보고서 목록 응답"""
    total: int = Field(..., description="전체 보고서 수")
    reports: list[WeeklyReportResponse] = Field(..., description="보고서 목록")

