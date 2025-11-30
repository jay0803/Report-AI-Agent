"""
메모리 관리자

대화 히스토리를 MD 파일로 저장하고 요약을 관리합니다.
- 16번째 대화부터 오래된 대화를 MD 파일에 백업
- 요약본을 별도 파일로 저장
"""

import os
from pathlib import Path
from typing import List, Optional
from datetime import datetime


class MemoryManager:
    """
    메모리 관리자
    
    세션별로 대화 히스토리와 요약을 파일로 관리합니다.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Args:
            data_dir: 데이터 저장 디렉토리 (기본: chatbot/data/sessions)
        """
        if data_dir is None:
            current_dir = Path(__file__).parent
            data_dir = current_dir / "data" / "sessions"
        
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_dir(self, session_id: str) -> Path:
        """세션 디렉토리 경로 반환"""
        session_dir = self.data_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir
    
    def _get_history_file(self, session_id: str) -> Path:
        """히스토리 파일 경로 반환"""
        return self._get_session_dir(session_id) / "history.md"
    
    def _get_summary_file(self, session_id: str) -> Path:
        """요약 파일 경로 반환"""
        return self._get_session_dir(session_id) / "summary.md"
    
    def append_message(self, session_id: str, message: dict):
        """
        메시지를 히스토리 파일에 추가
        
        Args:
            session_id: 세션 ID
            message: 메시지 딕셔너리 {"role": "user/assistant", "content": "...", "timestamp": "..."}
        """
        history_file = self._get_history_file(session_id)
        
        # 파일이 없으면 헤더 작성
        if not history_file.exists():
            with open(history_file, 'w', encoding='utf-8') as f:
                f.write(f"# 대화 히스토리\n\n")
                f.write(f"**세션 ID:** `{session_id}`\n\n")
                f.write(f"**생성 시간:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
        
        # 메시지 추가
        role_icon = "👤" if message["role"] == "user" else "🤖"
        role_name = "사용자" if message["role"] == "user" else "AI 비서"
        
        with open(history_file, 'a', encoding='utf-8') as f:
            f.write(f"## {role_icon} {role_name}\n\n")
            f.write(f"**시간:** {message.get('timestamp', 'N/A')}\n\n")
            f.write(f"{message['content']}\n\n")
            f.write("---\n\n")
    
    def get_all_messages(self, session_id: str) -> str:
        """
        세션의 전체 대화 히스토리 읽기
        
        Args:
            session_id: 세션 ID
            
        Returns:
            str: MD 형식의 전체 대화 내용
        """
        history_file = self._get_history_file(session_id)
        
        if not history_file.exists():
            return ""
        
        with open(history_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def save_summary(self, session_id: str, summary: str):
        """
        요약을 파일로 저장
        
        Args:
            session_id: 세션 ID
            summary: 요약 내용 (Markdown)
        """
        summary_file = self._get_summary_file(session_id)
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"# 대화 요약\n\n")
            f.write(f"**세션 ID:** `{session_id}`\n\n")
            f.write(f"**업데이트:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")
            f.write(summary)
    
    def get_summary(self, session_id: str) -> str:
        """
        요약 파일 읽기
        
        Args:
            session_id: 세션 ID
            
        Returns:
            str: 요약 내용 (없으면 빈 문자열)
        """
        summary_file = self._get_summary_file(session_id)
        
        if not summary_file.exists():
            return ""
        
        with open(summary_file, 'r', encoding='utf-8') as f:
            return f.read()
    
    def delete_session(self, session_id: str):
        """
        세션 파일 삭제
        
        Args:
            session_id: 세션 ID
        """
        session_dir = self._get_session_dir(session_id)
        
        # 파일 삭제
        for file in session_dir.glob("*"):
            file.unlink()
        
        # 디렉토리 삭제
        try:
            session_dir.rmdir()
        except:
            pass
    
    def session_exists(self, session_id: str) -> bool:
        """
        세션 파일이 존재하는지 확인
        
        Args:
            session_id: 세션 ID
            
        Returns:
            bool: 존재 여부
        """
        return self._get_history_file(session_id).exists()

