"""
Main Tasks Store

금일 진행 업무(main_tasks) 임시 저장소

Author: AI Assistant
Created: 2025-11-19
"""
from typing import Dict, List, Any, Optional
from datetime import date
from pydantic import BaseModel


class MainTasksData(BaseModel):
    """금일 진행 업무 저장 데이터"""
    owner: str
    target_date: date
    main_tasks: List[Dict[str, Any]]


class MainTasksStore:
    """
    금일 진행 업무 저장소 (메모리 기반)
    
    사용자가 TodayPlan Chain에서 선택한 업무를 저장하고,
    /daily/start 호출 시 자동으로 불러오는 용도
    """
    
    def __init__(self):
        """초기화"""
        # key: f"{owner}_{date}", value: MainTasksData
        self._store: Dict[str, MainTasksData] = {}
    
    def save(
        self,
        owner: str,
        target_date: date,
        main_tasks: List[Dict[str, Any]],
        append: bool = False  # 🔥 append 모드 추가
    ) -> None:
        """
        금일 진행 업무 저장
        
        Args:
            owner: 작성자
            target_date: 대상 날짜
            main_tasks: 선택된 업무 리스트
            append: True면 기존 업무에 추가, False면 덮어쓰기
        """
        key = self._make_key(owner, target_date)
        
        if append and key in self._store:
            # 🔥 기존 업무에 추가
            existing_tasks = self._store[key].main_tasks
            combined_tasks = existing_tasks + main_tasks
            data = MainTasksData(
                owner=owner,
                target_date=target_date,
                main_tasks=combined_tasks
            )
            self._store[key] = data
            print(f"[MainTasksStore] 추가 완료: {key}, {len(main_tasks)}개 추가 (총 {len(combined_tasks)}개)")
        else:
            # 기존 방식: 덮어쓰기
            data = MainTasksData(
                owner=owner,
                target_date=target_date,
                main_tasks=main_tasks
            )
            self._store[key] = data
            print(f"[MainTasksStore] 저장 완료: {key}, {len(main_tasks)}개 업무")
    
    def get(
        self,
        owner: str,
        target_date: date
    ) -> Optional[List[Dict[str, Any]]]:
        """
        금일 진행 업무 조회
        
        Args:
            owner: 작성자
            target_date: 대상 날짜
            
        Returns:
            저장된 main_tasks 또는 None
        """
        key = self._make_key(owner, target_date)
        data = self._store.get(key)
        
        if data:
            print(f"[MainTasksStore] 조회 성공: {key}, {len(data.main_tasks)}개 업무")
            return data.main_tasks
        else:
            print(f"[MainTasksStore] 조회 실패: {key} (데이터 없음)")
            return None
    
    def delete(
        self,
        owner: str,
        target_date: date
    ) -> bool:
        """
        금일 진행 업무 삭제
        
        Args:
            owner: 작성자
            target_date: 대상 날짜
            
        Returns:
            삭제 성공 여부
        """
        key = self._make_key(owner, target_date)
        if key in self._store:
            del self._store[key]
            print(f"[MainTasksStore] 삭제 완료: {key}")
            return True
        else:
            print(f"[MainTasksStore] 삭제 실패: {key} (데이터 없음)")
            return False
    
    def list_all(self) -> Dict[str, MainTasksData]:
        """모든 저장된 데이터 조회 (디버깅용)"""
        return self._store.copy()
    
    def _make_key(self, owner: str, target_date: date) -> str:
        """저장소 키 생성"""
        return f"{owner}_{target_date.isoformat()}"


# 싱글톤 인스턴스
_main_tasks_store: Optional[MainTasksStore] = None


def get_main_tasks_store() -> MainTasksStore:
    """MainTasksStore 싱글톤 반환"""
    global _main_tasks_store
    if _main_tasks_store is None:
        _main_tasks_store = MainTasksStore()
    return _main_tasks_store

