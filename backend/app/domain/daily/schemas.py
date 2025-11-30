"""
Daily Report Pydantic 스키마
"""
from datetime import date, datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from uuid import UUID


class DailyReportCreate(BaseModel):
    """일일보고서 생성 요청"""
    owner: str = Field(..., description="작성자")
    report_date: date = Field(..., description="보고서 날짜")
    report_json: Dict[str, Any] = Field(..., description="CanonicalReport JSON")


class DailyReportUpdate(BaseModel):
    """일일보고서 수정 요청"""
    report_json: Dict[str, Any] = Field(..., description="CanonicalReport JSON")


class DailyReportResponse(BaseModel):
    """일일보고서 응답"""
    id: UUID = Field(..., description="보고서 ID")
    owner: str = Field(..., description="작성자")
    report_date: date = Field(..., alias="date", description="보고서 날짜")
    report_json: Dict[str, Any] = Field(..., description="CanonicalReport JSON")
    created_at: datetime = Field(..., description="생성일시")
    updated_at: datetime = Field(..., description="수정일시")
    
    class Config:
        from_attributes = True  # SQLAlchemy 모델을 Pydantic으로 변환 허용
        populate_by_name = True  # alias와 필드명 모두 허용


class DailyReportListResponse(BaseModel):
    """일일보고서 목록 응답"""
    total: int = Field(..., description="전체 보고서 수")
    reports: list[DailyReportResponse] = Field(..., description="보고서 목록")

