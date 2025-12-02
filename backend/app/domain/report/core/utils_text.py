"""
텍스트 유틸리티 함수
고객명, 시간 추출 등
"""
import re
from typing import List, Optional


def extract_customer_names(text: str) -> List[str]:
    """
    텍스트에서 고객명 추출
    
    예시:
        "라유하 고객 상담 자료 정리" → ["라유하"]
        "노지유 고객 보장안 구성" → ["노지유"]
        "문세아 고객 리포트 작성" → ["문세아"]
        "박시엘 고객 상담 언제 했었지?" → ["박시엘"] (상담 제외)
    
    Args:
        text: 추출할 텍스트
        
    Returns:
        고객명 리스트
    """
    # 제외할 일반 단어 목록 (고객명이 아닌 단어)
    excluded_words = {
        "상담", "상담한", "상담했", "상담할", "상담하",  # 동사 형태
        "보장", "리포트", "자료", "정리", "구성", "작성", "분석", 
        "업무", "일정", "계획", "예정", "대기", "요청", "문의", "처리",
        "고객", "최근", "언제", "했었", "했지", "했어", "했는", "했던",
        "뽑아줘", "뽑아", "날짜", "다", "전부", "모두", "모든",  # 질문/요청 단어
        "알려줘", "알려", "찾아줘", "찾아"
    }
    
    # 패턴 1: "이름 고객" 형식 (가장 정확)
    pattern1 = r'([가-힣]{2,4})\s*고객'
    matches1 = re.findall(pattern1, text)
    
    # 패턴 2: "고객 이름" 형식
    pattern2 = r'고객\s*([가-힣]{2,4})'
    matches2 = re.findall(pattern2, text)
    
    # 패턴 3: "이름님", "이름씨" 형식
    pattern3 = r'([가-힣]{2,4})(?:님|씨)'
    matches3 = re.findall(pattern3, text)
    
    # 패턴 4: "이름에게", "이름와", "이름과" 형식
    pattern4 = r'([가-힣]{2,4})(?:에게|와|과)'
    matches4 = re.findall(pattern4, text)
    
    # 모든 매치 합치기
    all_matches = matches1 + matches2 + matches3 + matches4
    
    # 중복 제거 및 필터링
    unique_names = []
    for name in all_matches:
        # 2-4자 이름만 허용
        if 2 <= len(name) <= 4:
            # 제외 단어 목록에 없는 경우만 추가
            if name not in excluded_words:
                unique_names.append(name)
    
    # 중복 제거
    unique_names = list(set(unique_names))
    
    return unique_names


def extract_time_range(text: str) -> Optional[str]:
    """
    텍스트에서 시간 범위 추출
    
    예시:
        "09:00 - 10:00 라유하 고객 상담" → "09:00-10:00"
        "10:00~11:00 노지유 고객 보장안" → "10:00-11:00"
    
    Args:
        text: 추출할 텍스트
        
    Returns:
        시간 범위 문자열 (HH:MM-HH:MM) 또는 None
    """
    # 다양한 시간 형식 패턴
    patterns = [
        r'(\d{2}:\d{2})\s*[-~]\s*(\d{2}:\d{2})',  # "09:00 - 10:00" 또는 "09:00~10:00"
        r'(\d{2}:\d{2})\s*-\s*(\d{2}:\d{2})',     # "09:00-10:00"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            start_time = match.group(1)
            end_time = match.group(2)
            return f"{start_time}-{end_time}"
    
    return None


def extract_single_time(text: str) -> Optional[str]:
    """
    텍스트에서 단일 시간 추출
    
    Args:
        text: 추출할 텍스트
        
    Returns:
        시간 문자열 (HH:MM) 또는 None
    """
    pattern = r'\b(\d{2}:\d{2})\b'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


def is_pending_related(text: str) -> bool:
    """
    텍스트가 미종결 관련인지 판단
    
    Args:
        text: 판단할 텍스트
        
    Returns:
        미종결 관련 여부
    """
    pending_keywords = ["미종결", "대기", "보류", "추후", "예정", "자료요청", "자료대기"]
    return any(keyword in text for keyword in pending_keywords)


def is_summary_related(text: str) -> bool:
    """
    텍스트가 요약 관련인지 판단
    
    Args:
        text: 판단할 텍스트
        
    Returns:
        요약 관련 여부
    """
    summary_keywords = ["요약", "전체", "통계", "종합", "금일 진행", "주간 중요"]
    return any(keyword in text for keyword in summary_keywords)


def classify_task_category(text: str) -> List[str]:
    """
    텍스트에서 작업 카테고리 분류
    
    Args:
        text: 분류할 텍스트
        
    Returns:
        카테고리 리스트
    """
    text_lower = text.lower()
    categories = []
    
    if any(word in text_lower for word in ["상담", "리드", "문진", "신규"]):
        categories.append("new_lead")
    
    if any(word in text_lower for word in ["갱신", "유지", "특약변경", "주소변경", "재계약"]):
        categories.append("maintenance")
    
    if any(word in text_lower for word in ["보장분석", "포트폴리오", "리포트", "분석"]):
        categories.append("reporting")
    
    if any(word in text_lower for word in ["자료요청", "자료대기", "추가요청", "대기"]):
        categories.append("pending")
    
    if any(word in text_lower for word in ["입원", "수술", "청구", "사고", "보상"]):
        categories.append("claim")
    
    return categories if categories else ["general"]

