"""
Daily FSM 상태 정의

LangGraph 기반 일일보고서 입력 FSM의 상태 및 컨텍스트

Author: AI Assistant
Created: 2025-11-18
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import date
from pydantic import BaseModel, Field


class DailyState(str, Enum):
    """FSM 상태"""
    WAIT_START = "wait_start"
    ASK_TIME_RANGE = "ask_time_range"
    RECEIVE_ANSWER = "receive_answer"
    PARSE_TASK = "parse_task"
    NEXT_TIME_RANGE = "next_time_range"
    ASK_ISSUES = "ask_issues"
    RECEIVE_ISSUES = "receive_issues"
    ASK_PLANS = "ask_plans"
    RECEIVE_PLANS = "receive_plans"
    FINISHED = "finished"


class DailyFSMContext(BaseModel):
    """
    FSM 실행 컨텍스트
    
    FSM이 시간대별 세부업무만 입력받고,
    금일 진행 업무는 외부에서 주입받음
    """
    owner: str = Field(..., description="작성자")
    target_date: date = Field(..., description="보고서 날짜")
    time_ranges: List[str] = Field(default_factory=list, description="시간대 목록")
    current_index: int = Field(0, description="현재 시간대 인덱스")
    
    # 금일 진행 업무 (외부 주입, FSM에서 건드리지 않음)
    today_main_tasks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="금일 진행 업무 (TodayPlan에서 선택된 것)"
    )
    
    # FSM이 수집하는 시간대별 세부업무
    time_tasks: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="시간대별 세부업무 (FSM이 생성)"
    )
    
    # FSM이 수집하는 이슈사항
    issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="이슈 사항 (FSM이 생성)"
    )
    
    # FSM이 수집하는 익일 업무 계획
    plans: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="익일 업무 계획 (FSM이 생성)"
    )
    
    # 상태 관리
    current_state: DailyState = Field(
        default=DailyState.WAIT_START,
        description="현재 상태"
    )
    current_question: str = Field("", description="현재 질문")
    last_answer: str = Field("", description="마지막 답변")
    finished: bool = Field(False, description="완료 여부")
    
    # 메타데이터
    session_id: Optional[str] = Field(None, description="세션 ID")
    
    class Config:
        use_enum_values = True

