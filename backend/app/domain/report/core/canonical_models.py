"""
새로운 Canonical 보고서 모델 구조
원본 구조를 보존하며 RAG 검색 품질 극대화
"""
from typing import List, Optional, Dict, Any, Literal
from datetime import date
from pydantic import BaseModel, Field


# ========================================
# Daily Report Canonical
# ========================================
class DetailTask(BaseModel):
    """세부 업무 항목"""
    time_start: Optional[str] = Field(default=None, description="시작 시간 (HH:MM)")
    time_end: Optional[str] = Field(default=None, description="종료 시간 (HH:MM)")
    text: str = Field(..., description="업무 내용")
    note: str = Field(default="", description="비고")


class CanonicalDaily(BaseModel):
    """일일 보고서 Canonical 구조"""
    header: Dict[str, str] = Field(..., description="상단 정보 (작성일자, 성명)")
    summary_tasks: List[str] = Field(default_factory=list, description="금일 진행 업무 요약")
    detail_tasks: List[DetailTask] = Field(default_factory=list, description="세부 업무 목록")
    pending: List[str] = Field(default_factory=list, description="미종결 업무")
    plans: List[str] = Field(default_factory=list, description="익일 계획")
    notes: str = Field(default="", description="특이사항")


# ========================================
# Weekly Report Canonical
# ========================================
class CanonicalWeekly(BaseModel):
    """주간 보고서 Canonical 구조"""
    header: Dict[str, str] = Field(..., description="상단 정보 (작성일자, 성명)")
    weekly_goals: List[str] = Field(default_factory=list, description="주간 업무 목표")
    weekday_tasks: Dict[str, List[str]] = Field(default_factory=dict, description="요일별 세부 업무")
    weekly_highlights: List[str] = Field(default_factory=list, description="주간 중요 업무")
    notes: str = Field(default="", description="특이사항")


# ========================================
# Monthly Report Canonical
# ========================================
class CanonicalMonthly(BaseModel):
    """월간 보고서 Canonical 구조"""
    header: Dict[str, str] = Field(..., description="상단 정보 (월, 작성일자, 성명)")
    weekly_summaries: Dict[str, List[str]] = Field(default_factory=dict, description="주차별 세부 업무")
    next_month_plan: str = Field(default="", description="익월 계획")


# ========================================
# Unified Canonical Report
# ========================================
class CanonicalReport(BaseModel):
    """통합 Canonical 보고서 스키마"""
    report_id: str = Field(..., description="보고서 ID")
    report_type: Literal["daily", "weekly", "monthly"] = Field(..., description="보고서 타입")
    owner: str = Field(default="", description="작성자")
    period_start: Optional[date] = Field(default=None, description="시작 일자")
    period_end: Optional[date] = Field(default=None, description="종료 일자")
    
    # 타입별 Canonical 데이터 (하나만 존재)
    daily: Optional[CanonicalDaily] = Field(default=None, description="일일 보고서 데이터")
    weekly: Optional[CanonicalWeekly] = Field(default=None, description="주간 보고서 데이터")
    monthly: Optional[CanonicalMonthly] = Field(default=None, description="월간 보고서 데이터")

