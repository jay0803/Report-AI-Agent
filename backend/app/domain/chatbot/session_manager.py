"""
세션 관리자

채팅 세션별 대화 히스토리를 관리합니다.
- deque를 사용한 효율적인 메모리 관리
- 세션별 독립적 Lock (병렬 처리 가능)
- Atomic 연산 보장
- 최대 15개 메시지 유지 (오래된 것부터 자동 삭제)
"""

from collections import deque
from typing import List, Optional
import uuid
from datetime import datetime
from pathlib import Path

# Import 경로 처리 (FastAPI vs 직접 실행)
try:
    from app.domain.common.base_session_manager import BaseSessionManager
except ImportError:
    import sys
    project_root = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(project_root))
    from app.domain.common.base_session_manager import BaseSessionManager


class SessionData:
    """세션 데이터 (대화 히스토리)"""
    
    def __init__(self, max_history: int = 15, user_id: int = None):
        self.messages = deque(maxlen=max_history)
        self.message_count = 0
        self.user_id = user_id


class SessionManager(BaseSessionManager[SessionData]):
    """
    채팅 세션 관리자
    
    각 세션별로 대화 히스토리를 유지하며,
    최대 15개의 메시지만 보관합니다 (FIFO).
    세션별 독립적 Lock으로 동시성 처리.
    """
    
    _instance = None
    _init_lock = None
    
    def __new__(cls, *args, **kwargs):
        """싱글톤 패턴"""
        from threading import Lock
        
        if cls._init_lock is None:
            cls._init_lock = Lock()
        
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, max_history: int = 15):
        """
        Args:
            max_history: 세션당 최대 메시지 개수 (기본 15개)
        """
        if not hasattr(self, '_initialized'):
            super().__init__()
            self.max_history = max_history
            self._initialized = True
    
    def create_session(self, user_id: int = None) -> str:
        """
        새로운 채팅 세션 생성
        
        Args:
            user_id: 사용자 ID (선택)
        
        Returns:
            str: 생성된 세션 ID (UUID)
        """
        session_id = str(uuid.uuid4())
        
        # Atomic get-or-create
        self._safe_get_or_create(
            session_id,
            lambda: SessionData(self.max_history, user_id)
        )
        
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str):
        """
        세션에 메시지 추가 (Thread-safe)
        
        Args:
            session_id: 세션 ID
            role: "user" 또는 "assistant"
            content: 메시지 내용
        """
        def _add_message(session_data: SessionData):
            session_data.messages.append({
                "role": role,
                "content": content,
                "timestamp": datetime.now().isoformat()
            })
            session_data.message_count += 1
        
        # 세션이 없으면 생성하고 메시지 추가
        session_data = self._safe_get_or_create(
            session_id,
            lambda: SessionData(self.max_history)
        )
        
        # 세션별 Lock으로 안전하게 업데이트
        self._safe_update(session_id, _add_message)
    
    def get_history(self, session_id: str) -> List[dict]:
        """
        세션의 대화 히스토리 가져오기
        
        Args:
            session_id: 세션 ID
            
        Returns:
            List[dict]: 대화 히스토리 (최대 15개)
        """
        session_data = self._safe_get(session_id)
        
        if session_data is None:
            return []
        
        return list(session_data.messages)
    
    def get_history_for_llm(self, session_id: str) -> List[dict]:
        """
        LLM API 호출용 히스토리 (role, content만)
        
        Args:
            session_id: 세션 ID
            
        Returns:
            List[dict]: [{"role": "user", "content": "..."}, ...]
        """
        history = self.get_history(session_id)
        return [
            {"role": msg["role"], "content": msg["content"]}
            for msg in history
        ]
    
    def get_session_info(self, session_id: str) -> Optional[dict]:
        """
        세션 메타데이터 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            dict: 세션 정보 (생성 시간, 마지막 활동, 메시지 수, user_id)
        """
        # BaseSessionManager의 메타데이터 조회
        base_metadata = self._get_metadata(session_id)
        
        if not base_metadata:
            return None
        
        # 세션 데이터 조회
        session_data = self._safe_get(session_id)
        
        if session_data is None:
            return None
        
        # 통합 정보 반환
        return {
            "created_at": base_metadata.get("created_at"),
            "last_activity": base_metadata.get("last_access"),
            "message_count": session_data.message_count,
            "current_message_count": len(session_data.messages),
            "user_id": session_data.user_id
        }
    
    def delete_session(self, session_id: str):
        """
        세션 삭제 (Thread-safe)
        
        Args:
            session_id: 세션 ID
        """
        self._safe_delete(session_id)
    
    def list_sessions(self) -> List[str]:
        """
        모든 세션 ID 목록 조회
        
        Returns:
            List[str]: 세션 ID 목록
        """
        return self._safe_list_sessions()
    
    def clear_all_sessions(self):
        """모든 세션 삭제 (테스트용)"""
        session_ids = self.list_sessions()
        for session_id in session_ids:
            self.delete_session(session_id)
    
    def session_exists(self, session_id: str) -> bool:
        """
        세션 존재 여부 확인
        
        Args:
            session_id: 세션 ID
            
        Returns:
            bool: 존재 여부
        """
        return self._safe_exists(session_id)
