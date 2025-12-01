"""
Planner 스키마

일정 계획 요청/응답 모델

Author: AI Assistant
Created: 2025-11-18
"""
from typing import List, Optional
from datetime import date
from pydantic import BaseModel, Field


class TaskItem(BaseModel):
    """작업 항목"""
    title: str = Field(..., description="작업 제목")
    description: str = Field("", description="작업 설명")
    priority: str = Field("medium", description="우선순위 (high/medium/low)")
    expected_time: str = Field("", description="예상 소요 시간")
    category: str = Field("", description="카테고리")


class TodayPlanRequest(BaseModel):
    """오늘 일정 생성 요청"""
    owner: str = Field(..., description="작성자/담당자")
    target_date: date = Field(..., description="기준 날짜 (오늘)")


class TodayPlanResponse(BaseModel):
    """오늘 일정 생성 응답"""
    tasks: List[TaskItem] = Field(default_factory=list, description="추천 작업 목록")
    summary: str = Field("", description="전체 요약")
    source_date: Optional[str] = Field(None, description="참고한 전날 날짜")
    owner: str = Field("", description="작성자")

