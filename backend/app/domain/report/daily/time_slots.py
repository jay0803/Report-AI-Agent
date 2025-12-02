"""
시간대 생성기

일일보고서 작성을 위한 시간대 슬롯 생성

Author: AI Assistant  
Created: 2025-11-18
"""
from typing import List
from datetime import datetime, timedelta


def generate_time_slots(
    start: str = "09:00",
    end: str = "18:00",
    interval: int = 60
) -> List[str]:
    """
    시간대 슬롯 생성
    
    Args:
        start: 시작 시간 (HH:MM)
        end: 종료 시간 (HH:MM)
        interval: 간격 (분)
        
    Returns:
        시간대 문자열 리스트 ["09:00~10:00", "10:00~11:00", ...]
        
    Example:
        >>> generate_time_slots("09:00", "18:00", 60)
        ['09:00~10:00', '10:00~11:00', ..., '17:00~18:00']
    """
    # 시작/종료 시간 파싱
    start_time = datetime.strptime(start, "%H:%M")
    end_time = datetime.strptime(end, "%H:%M")
    
    slots = []
    current = start_time
    
    while current < end_time:
        next_time = current + timedelta(minutes=interval)
        
        # 시간대 문자열 생성
        slot = f"{current.strftime('%H:%M')}~{next_time.strftime('%H:%M')}"
        slots.append(slot)
        
        current = next_time
    
    return slots


def parse_time_range(time_range: str) -> tuple:
    """
    시간대 문자열 파싱
    
    Args:
        time_range: "09:00~10:00" 형식
        
    Returns:
        (start_time, end_time) 튜플
    """
    start_str, end_str = time_range.split("~")
    return start_str.strip(), end_str.strip()

