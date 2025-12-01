"""
Session Manager

FSM 세션 관리 (메모리 기반)

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Dict, Optional
import uuid
from app.domain.report.daily.fsm_state import DailyFSMContext


class SessionManager:
    """FSM 세션 관리자 (메모리 기반)"""
    
    def __init__(self):
        """초기화"""
        self._sessions: Dict[str, DailyFSMContext] = {}
    
    def create_session(self, context: DailyFSMContext) -> str:
        """
        세션 생성
        
        Args:
            context: FSM 컨텍스트
            
        Returns:
            세션 ID
        """
        session_id = str(uuid.uuid4())
        context.session_id = session_id
        self._sessions[session_id] = context
        return session_id
    
    def get_session(self, session_id: str) -> Optional[DailyFSMContext]:
        """
        세션 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            FSM 컨텍스트 또는 None
        """
        return self._sessions.get(session_id)
    
    def update_session(self, session_id: str, context: DailyFSMContext):
        """
        세션 업데이트
        
        Args:
            session_id: 세션 ID
            context: 업데이트할 컨텍스트
        """
        self._sessions[session_id] = context
    
    def delete_session(self, session_id: str):
        """
        세션 삭제
        
        Args:
            session_id: 세션 ID
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    def list_sessions(self) -> Dict[str, DailyFSMContext]:
        """모든 세션 조회"""
        return self._sessions.copy()


# 싱글톤 인스턴스
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """SessionManager 싱글톤 반환"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager

