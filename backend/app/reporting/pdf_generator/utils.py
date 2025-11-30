"""
PDF Generator Utility Functions

좌표 변환, 텍스트 포맷팅 등 공통 유틸리티
"""
from datetime import date, datetime
from typing import Optional


def format_date(d: Optional[date], format_str: str = "%Y-%m-%d") -> str:
    """
    날짜를 문자열로 포맷
    
    Args:
        d: date 객체
        format_str: 포맷 문자열
        
    Returns:
        포맷된 날짜 문자열
    """
    if d is None:
        return ""
    
    if isinstance(d, str):
        # 이미 문자열이면 그대로 반환
        return d
    
    return d.strftime(format_str)


def format_korean_date(d: Optional[date]) -> str:
    """
    날짜를 한글 형식으로 포맷
    
    Args:
        d: date 객체
        
    Returns:
        "2025년 1월 20일" 형식 문자열
    """
    if d is None:
        return ""
    
    if isinstance(d, str):
        # "YYYY-MM-DD" 문자열을 date로 변환
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            return d
    
    return f"{d.year}년 {d.month}월 {d.day}일"


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    텍스트를 최대 길이로 자르기
    
    Args:
        text: 원본 텍스트
        max_length: 최대 길이
        suffix: 잘렸을 때 붙일 접미사
        
    Returns:
        잘린 텍스트
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def wrap_text(text: str, max_width: int = 40) -> list:
    """
    텍스트를 최대 너비로 줄바꿈
    
    Args:
        text: 원본 텍스트
        max_width: 한 줄 최대 문자 수
        
    Returns:
        줄바꿈된 텍스트 리스트
    """
    if len(text) <= max_width:
        return [text]
    
    lines = []
    current_line = ""
    
    for char in text:
        if len(current_line) >= max_width:
            lines.append(current_line)
            current_line = char
        else:
            current_line += char
    
    if current_line:
        lines.append(current_line)
    
    return lines


def get_priority_text(priority: str) -> str:
    """
    우선순위를 한글로 변환
    
    Args:
        priority: "high", "medium", "low"
        
    Returns:
        "높음", "보통", "낮음"
    """
    mapping = {
        "high": "높음",
        "medium": "보통",
        "low": "낮음"
    }
    return mapping.get(priority, "보통")


def get_status_text(status: str) -> str:
    """
    상태를 한글로 변환
    
    Args:
        status: "완료", "진행중", "대기" 등
        
    Returns:
        한글 상태
    """
    mapping = {
        "completed": "완료",
        "in_progress": "진행중",
        "pending": "대기",
        "완료": "완료",
        "진행중": "진행중"
    }
    return mapping.get(status, status)


# PDF 좌표 상수 (A4 기준, points)
class PDFCoordinates:
    """PDF 좌표 상수 모음"""
    
    # A4 크기
    PAGE_WIDTH = 595.27
    PAGE_HEIGHT = 841.89
    
    # 여백
    MARGIN_LEFT = 50
    MARGIN_RIGHT = 50
    MARGIN_TOP = 50
    MARGIN_BOTTOM = 50
    
    # 컨텐츠 영역
    CONTENT_WIDTH = PAGE_WIDTH - MARGIN_LEFT - MARGIN_RIGHT
    CONTENT_HEIGHT = PAGE_HEIGHT - MARGIN_TOP - MARGIN_BOTTOM
    
    @classmethod
    def from_top(cls, y: float) -> float:
        """상단 기준 Y 좌표를 PDF 좌표로 변환"""
        return cls.PAGE_HEIGHT - y
    
    @classmethod
    def from_bottom(cls, y: float) -> float:
        """하단 기준 Y 좌표 (그대로 반환)"""
        return y

