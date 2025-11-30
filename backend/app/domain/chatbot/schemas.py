"""
채팅봇 스키마

Pydantic 모델 정의 (추후 FastAPI 연동 시 사용)
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str = Field(..., description="user 또는 assistant")
    content: str = Field(..., description="메시지 내용")
    timestamp: Optional[str] = Field(None, description="메시지 생성 시간")


class ChatRequest(BaseModel):
    """채팅 요청"""
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="사용자 입력 메시지")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="LLM temperature")


class ChatResponse(BaseModel):
    """채팅 응답"""
    session_id: str = Field(..., description="세션 ID")
    message: str = Field(..., description="AI 응답 메시지")
    timestamp: str = Field(..., description="응답 생성 시간")


class SessionInfo(BaseModel):
    """세션 정보"""
    session_id: str = Field(..., description="세션 ID")
    created_at: str = Field(..., description="세션 생성 시간")
    last_activity: str = Field(..., description="마지막 활동 시간")
    message_count: int = Field(..., description="총 메시지 수")
    current_message_count: int = Field(..., description="현재 유지 중인 메시지 수")


class SessionCreateResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str = Field(..., description="생성된 세션 ID")
    created_at: str = Field(..., description="생성 시간")

