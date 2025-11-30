"""
Chatbot API Endpoints

채팅봇 기능을 제공하는 FastAPI 엔드포인트
- 세션 생성/삭제
- 메시지 전송 및 응답
- 대화 히스토리 조회
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.domain.chatbot.service import ChatService
from app.domain.auth.dependencies import get_current_user, get_current_user_optional
from app.domain.user.models import User

router = APIRouter()

# ChatService 싱글톤 인스턴스 (lazy initialization)
_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    """ChatService 싱글톤 인스턴스 반환 (lazy initialization)"""
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
        print("✅ Chatbot ChatService 초기화 완료")
    return _chat_service


class SessionResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str
    message: str


class MessageRequest(BaseModel):
    """메시지 전송 요청"""
    session_id: str
    message: str


class MessageResponse(BaseModel):
    """메시지 전송 응답"""
    session_id: str
    user_message: str
    assistant_message: str
    timestamp: str


class HistoryResponse(BaseModel):
    """히스토리 조회 응답"""
    session_id: str
    messages: List[dict]
    total_count: int


@router.post("/session", response_model=SessionResponse)
async def create_session(
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    새로운 채팅 세션 생성
    
    Args:
        current_user: 현재 로그인한 사용자 (선택, 쿠키에서 자동 추출)
    
    Returns:
        SessionResponse: 생성된 세션 ID
    """
    try:
        # 로그인한 사용자면 user_id 사용, 아니면 None (게스트)
        user_id = current_user.id if current_user else None
        
        if user_id:
            print(f"✅ 세션 생성 - 로그인 사용자: {current_user.email} (ID: {user_id})")
        else:
            print(f"✅ 세션 생성 - 게스트 사용자")
        
        session_id = get_chat_service().create_session(user_id=user_id)
        return SessionResponse(
            session_id=session_id,
            message="세션이 생성되었습니다."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")


@router.post("/message", response_model=MessageResponse)
async def send_message(
    request: MessageRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    메시지 전송 및 AI 응답 받기
    
    Args:
        request: 세션 ID와 사용자 메시지
        current_user: 현재 로그인한 사용자 (선택, 쿠키에서 자동 추출)
        
    Returns:
        MessageResponse: 사용자 메시지와 AI 응답
    """
    try:
        # 세션 존재 확인
        chat_service = get_chat_service()
        if not chat_service.session_manager.session_exists(request.session_id):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 로그인한 사용자면 user_id 사용, 아니면 None (게스트)
        user_id = current_user.id if current_user else None
        
        if user_id:
            print(f"💬 메시지 전송 - 로그인 사용자: {current_user.email} (ID: {user_id})")
        else:
            print(f"💬 메시지 전송 - 게스트 사용자")
        
        # AI 응답 생성 (user_id 전달)
        assistant_message = await chat_service.process_message(
            session_id=request.session_id,
            user_message=request.message,
            user_id=user_id
        )
        
        return MessageResponse(
            session_id=request.session_id,
            user_message=request.message,
            assistant_message=assistant_message,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"메시지 처리 실패: {str(e)}")


@router.get("/history/{session_id}", response_model=HistoryResponse)
async def get_history(session_id: str):
    """
    대화 히스토리 조회
    
    Args:
        session_id: 세션 ID
        
    Returns:
        HistoryResponse: 대화 히스토리 (최대 15개)
    """
    try:
        # 세션 존재 확인
        chat_service = get_chat_service()
        if not chat_service.session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 히스토리 조회
        history = chat_service.session_manager.get_history(session_id)
        
        return HistoryResponse(
            session_id=session_id,
            messages=history,
            total_count=len(history)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"히스토리 조회 실패: {str(e)}")


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """
    세션 삭제
    
    Args:
        session_id: 삭제할 세션 ID
        
    Returns:
        dict: 삭제 완료 메시지
    """
    try:
        # 세션 존재 확인
        chat_service = get_chat_service()
        if not chat_service.session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 세션 삭제
        chat_service.session_manager.delete_session(session_id)
        
        return {"message": "세션이 삭제되었습니다.", "session_id": session_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")


@router.get("/session/{session_id}/info")
async def get_session_info(session_id: str):
    """
    세션 정보 조회 (메타데이터)
    
    Args:
        session_id: 세션 ID
        
    Returns:
        dict: 세션 정보 (생성 시간, 마지막 활동, 메시지 수)
    """
    try:
        # 세션 존재 확인
        chat_service = get_chat_service()
        if not chat_service.session_manager.session_exists(session_id):
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
        
        # 세션 정보 조회
        info = chat_service.session_manager.get_session_info(session_id)
        
        if info is None:
            raise HTTPException(status_code=404, detail="세션 정보를 찾을 수 없습니다.")
        
        return info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 정보 조회 실패: {str(e)}")

