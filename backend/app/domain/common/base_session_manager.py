"""
Base Session Manager

모든 SessionManager가 상속받는 기본 클래스
- 세션별 Lock으로 fine-grained 동시성 제어
- Atomic 연산 보장
- 성능 최적화 (Java의 ConcurrentHashMap 수준)

Author: 진모
Created: 2025-11-20
"""

from collections import defaultdict
from threading import RLock
from typing import Dict, Optional, Callable, TypeVar, Generic
from datetime import datetime

T = TypeVar('T')


class BaseSessionManager(Generic[T]):
    """
    Thread-safe Session Manager Base Class
    
    특징:
    - 세션별 독립적 Lock (병렬 처리 가능)
    - Double-checked locking 패턴
    - Atomic get-or-create 연산
    - 메모리 효율적
    """
    
    def __init__(self):
        """초기화"""
        self._sessions: Dict[str, T] = {}
        self._session_locks = defaultdict(RLock)  # 세션별 Lock
        self._global_lock = RLock()  # 딕셔너리 수정용
        self._metadata: Dict[str, dict] = {}  # 세션 메타데이터
    
    def _safe_get_or_create(
        self,
        session_id: str,
        factory_func: Callable[[], T]
    ) -> T:
        """
        Atomic한 get-or-create 연산
        
        Double-checked locking 패턴:
        1. 먼저 Lock 없이 체크 (빠른 경로)
        2. 없으면 Lock 획득 후 재확인
        3. 여전히 없으면 생성
        
        Args:
            session_id: 세션 ID
            factory_func: 세션 객체 생성 함수
            
        Returns:
            T: 세션 객체
        """
        # 빠른 경로: Lock 없이 먼저 체크
        if session_id in self._sessions:
            return self._sessions[session_id]
        
        # 세션별 Lock 획득 (다른 세션은 영향 없음)
        with self._session_locks[session_id]:
            # Double-check: Lock 대기 중 다른 스레드가 생성했을 수 있음
            if session_id in self._sessions:
                return self._sessions[session_id]
            
            # 전역 Lock (딕셔너리 수정 시만)
            with self._global_lock:
                if session_id not in self._sessions:
                    # 세션 생성
                    self._sessions[session_id] = factory_func()
                    self._metadata[session_id] = {
                        "created_at": datetime.now().isoformat(),
                        "last_access": datetime.now().isoformat()
                    }
            
            return self._sessions[session_id]
    
    def _safe_get(self, session_id: str) -> Optional[T]:
        """
        안전한 세션 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Optional[T]: 세션 객체 또는 None
        """
        # 읽기는 세션별 Lock만 필요
        with self._session_locks[session_id]:
            # 마지막 접근 시간 업데이트
            if session_id in self._metadata:
                self._metadata[session_id]["last_access"] = datetime.now().isoformat()
            
            return self._sessions.get(session_id)
    
    def _safe_update(
        self,
        session_id: str,
        update_func: Callable[[T], None]
    ) -> bool:
        """
        안전한 세션 업데이트
        
        Args:
            session_id: 세션 ID
            update_func: 업데이트 함수 (session 객체를 인자로 받음)
            
        Returns:
            bool: 성공 여부
        """
        with self._session_locks[session_id]:
            if session_id not in self._sessions:
                return False
            
            update_func(self._sessions[session_id])
            
            # 마지막 접근 시간 업데이트
            if session_id in self._metadata:
                self._metadata[session_id]["last_access"] = datetime.now().isoformat()
            
            return True
    
    def _safe_delete(self, session_id: str) -> bool:
        """
        안전한 세션 삭제
        
        Args:
            session_id: 세션 ID
            
        Returns:
            bool: 삭제 성공 여부
        """
        with self._session_locks[session_id]:
            with self._global_lock:
                deleted = False
                
                if session_id in self._sessions:
                    del self._sessions[session_id]
                    deleted = True
                
                if session_id in self._metadata:
                    del self._metadata[session_id]
                
                # Lock도 정리 (메모리 누수 방지)
                if session_id in self._session_locks:
                    del self._session_locks[session_id]
                
                return deleted
    
    def _safe_exists(self, session_id: str) -> bool:
        """
        세션 존재 여부 확인 (Lock 없이 빠르게)
        
        Args:
            session_id: 세션 ID
            
        Returns:
            bool: 존재 여부
        """
        return session_id in self._sessions
    
    def _safe_list_sessions(self) -> list:
        """
        모든 세션 ID 목록 조회
        
        Returns:
            list: 세션 ID 리스트
        """
        with self._global_lock:
            return list(self._sessions.keys())
    
    def _safe_count(self) -> int:
        """
        세션 개수 조회
        
        Returns:
            int: 세션 개수
        """
        return len(self._sessions)
    
    def _get_metadata(self, session_id: str) -> Optional[dict]:
        """
        세션 메타데이터 조회
        
        Args:
            session_id: 세션 ID
            
        Returns:
            Optional[dict]: 메타데이터 또는 None
        """
        with self._session_locks[session_id]:
            return self._metadata.get(session_id, {}).copy()

