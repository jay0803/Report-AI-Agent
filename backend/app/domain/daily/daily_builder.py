"""
Daily Report Builder

FSM 결과를 CanonicalReport로 변환

Author: AI Assistant
Created: 2025-11-18
"""
from typing import List, Dict, Any, Set
from datetime import date
import hashlib
import re
import numpy as np
import openai
from functools import lru_cache

from app.domain.report.canonical_models import (
    CanonicalReport,
    CanonicalDaily,
    DetailTask
)
from app.core.config import settings


@lru_cache(maxsize=1000)
def get_embedding(text: str) -> np.ndarray:
    """
    텍스트의 임베딩 벡터 가져오기 (캐시 적용)
    
    Args:
        text: 임베딩할 텍스트
        
    Returns:
        임베딩 벡터 (numpy array)
    """
    try:
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.embeddings.create(
            model="text-embedding-3-small",  # 빠르고 비용 효율적
            input=text.strip()
        )
        return np.array(response.data[0].embedding)
    except Exception as e:
        print(f"[ERROR] 임베딩 생성 실패: {e}")
        # 실패시 빈 벡터 반환
        return np.zeros(1536)


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    두 벡터의 코사인 유사도 계산
    
    Args:
        vec1: 첫 번째 벡터
        vec2: 두 번째 벡터
        
    Returns:
        코사인 유사도 (0.0 ~ 1.0)
    """
    # 벡터 크기가 0인 경우 처리
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    # 코사인 유사도 계산
    similarity = np.dot(vec1, vec2) / (norm1 * norm2)
    
    # -1 ~ 1 범위를 0 ~ 1로 변환
    return float((similarity + 1) / 2)


def calculate_semantic_similarity(text1: str, text2: str) -> float:
    """
    두 텍스트의 의미적 유사도 계산 (임베딩 기반)
    
    Args:
        text1: 첫 번째 텍스트
        text2: 두 번째 텍스트
        
    Returns:
        의미적 유사도 (0.0 ~ 1.0)
    """
    if not text1.strip() or not text2.strip():
        return 0.0
    
    # 임베딩 생성
    emb1 = get_embedding(text1)
    emb2 = get_embedding(text2)
    
    # 코사인 유사도 계산
    return cosine_similarity(emb1, emb2)


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    두 텍스트의 유사도 계산 (Jaccard similarity) - Fallback용
    
    Args:
        text1: 첫 번째 텍스트
        text2: 두 번째 텍스트
        
    Returns:
        유사도 (0.0 ~ 1.0)
    """
    # 정규화: 소문자, 공백 제거, 특수문자 제거
    def normalize(text: str) -> Set[str]:
        text = text.lower()
        text = re.sub(r'[^\w\s가-힣]', '', text)
        # 2글자 이상의 단어만 추출 (조사 제거)
        words = [w for w in text.split() if len(w) >= 2]
        return set(words)
    
    set1 = normalize(text1)
    set2 = normalize(text2)
    
    if not set1 or not set2:
        return 0.0
    
    intersection = set1 & set2
    union = set1 | set2
    
    return len(intersection) / len(union) if union else 0.0


def find_completed_main_tasks(
    main_tasks: List[Dict[str, Any]],
    time_tasks: List[Dict[str, Any]],
    similarity_threshold: float = 0.75
) -> Set[int]:
    """
    실제 수행된 main_tasks 인덱스 찾기 (임베딩 기반 의미적 유사도)
    
    Args:
        main_tasks: 예정된 업무 목록
        time_tasks: 실제 수행한 업무 목록
        similarity_threshold: 의미적 유사도 임계값 (기본 0.75 = 75%)
        
    Returns:
        실제 수행된 main_task의 인덱스 Set
    """
    completed_indices = set()
    
    print("\n🔍 [업무 매칭 시작] 예정 업무와 실제 업무 비교 (임베딩 기반)")
    print(f"   - 예정 업무: {len(main_tasks)}개")
    print(f"   - 실제 업무: {len(time_tasks)}개")
    print(f"   - 유사도 임계값: {similarity_threshold:.2f} (75%)")
    
    for main_idx, main_task in enumerate(main_tasks):
        main_title = main_task.get("title", "")
        main_desc = main_task.get("description", "")
        
        # main_task의 핵심 텍스트 (title 우선, description 보조)
        main_text = main_title
        if main_desc and main_desc.strip():
            main_text = f"{main_title} {main_desc}"
        
        best_similarity = 0.0
        best_match_title = ""
        
        for time_task in time_tasks:
            time_title = time_task.get("title", "")
            time_desc = time_task.get("description", "")
            
            # time_task의 핵심 텍스트 (title 우선)
            time_text = time_title
            if time_desc and time_desc.strip():
                time_text = f"{time_title} {time_desc}"
            
            # 🔥 임베딩 기반 의미적 유사도 계산
            try:
                semantic_similarity = calculate_semantic_similarity(main_text, time_text)
                
                # 최고 유사도 추적
                if semantic_similarity > best_similarity:
                    best_similarity = semantic_similarity
                    best_match_title = time_title
                
                # 매칭 조건: 의미적 유사도가 임계값(0.75) 이상
                if semantic_similarity >= similarity_threshold:
                    completed_indices.add(main_idx)
                    print(f"   ✅ 매칭 성공: '{main_title}' ↔ '{time_title}'")
                    print(f"      └─ 의미적 유사도: {semantic_similarity:.3f}")
                    break
                    
            except Exception as e:
                print(f"   ⚠️ 유사도 계산 오류: {e}")
                # 오류 발생시 fallback으로 Jaccard 유사도 사용
                fallback_similarity = calculate_text_similarity(main_text, time_text)
                if fallback_similarity >= 0.5:  # fallback threshold
                    completed_indices.add(main_idx)
                    print(f"   ✅ 매칭 (fallback): '{main_title}' ↔ '{time_title}' ({fallback_similarity:.2f})")
                    break
        
        # 매칭 실패시 로그
        if main_idx not in completed_indices:
            print(f"   ❌ 미종결: '{main_title}'")
            if best_match_title:
                print(f"      └─ 가장 유사한 업무: '{best_match_title}' (유사도: {best_similarity:.3f}, 임계값 미달)")
    
    print(f"\n📊 [매칭 결과] 완료된 업무: {len(completed_indices)}/{len(main_tasks)}개")
    print(f"   - 미종결 업무: {len(main_tasks) - len(completed_indices)}개\n")
    
    return completed_indices


def build_daily_report(
    owner: str,
    target_date: date,
    main_tasks: List[Dict[str, Any]],
    time_tasks: List[Dict[str, Any]],
    issues: List[Dict[str, Any]] = None,
    plans: List[Dict[str, Any]] = None
) -> CanonicalReport:
    """
    일일보고서 생성
    
    실무 기준:
    - main_tasks = 아침에 선택한 "예정" 업무
    - time_tasks = FSM에서 입력한 "실제 수행" 업무
    - issues = FSM에서 입력한 "이슈 사항"
    - plans = FSM에서 입력한 "익일 업무 계획"
    - 실제 수행되지 않은 main_tasks → unresolved (미종결 업무)
    
    Args:
        owner: 작성자
        target_date: 날짜
        main_tasks: 금일 진행 업무 (예정, TodayPlan에서 선택)
        time_tasks: 시간대별 세부업무 (실제 수행, FSM 입력)
        issues: 이슈 사항 (FSM 입력, optional)
        plans: 익일 업무 계획 (FSM 입력, optional)
        
    Returns:
        CanonicalReport 객체
    """
    if issues is None:
        issues = []
    if plans is None:
        plans = []
    # report_id 생성 (deterministic)
    report_id = generate_report_id(owner, target_date)
    
    # 🔥 실제 수행된 main_task 인덱스 찾기 (fuzzy matching)
    completed_main_indices = find_completed_main_tasks(main_tasks, time_tasks)
    
    # 🔥 미종결 업무 = main_tasks 중 수행되지 않은 것
    unresolved_tasks = [
        main_tasks[i].get("title", "")
        for i in range(len(main_tasks))
        if i not in completed_main_indices
    ]
    
    # 🔥 특이사항 = FSM 이슈사항 (미종결 업무와 분리!)
    special_notes = []
    for issue in issues:
        description = issue.get("description", "")
        if description and description.strip():
            special_notes.append(description.strip())
    
    # 🔥 plans = 금일 예정 업무 (main_tasks) - 원래 설계대로 유지
    planned_tasks = [task.get("title", "") for task in main_tasks if task.get("title")]
    
    # 🔥 next_day_plans = FSM 익일 업무 계획 (별도로 metadata에 저장)
    next_day_plans = []
    for plan in plans:
        title = plan.get("title", "")
        if title and title.strip():
            next_day_plans.append(title.strip())
    
    # detail_tasks = time_tasks만 (실제 완료 업무)
    detail_tasks = []
    for i, task_dict in enumerate(time_tasks):
        time_range = task_dict.get("time_range", "")
        time_start, time_end = None, None
        
        if "~" in time_range:
            parts = time_range.split("~")
            if len(parts) >= 2:
                time_start = parts[0].strip()
                time_end = parts[1].strip()
        
        task_text = task_dict.get("description", "") or task_dict.get("title", "")
        note = f"카테고리: {task_dict.get('category', '')}"
        
        if task_text:
            detail_tasks.append(DetailTask(
                time_start=time_start,
                time_end=time_end,
                text=task_text,
                note=note
            ))
    
    # summary_tasks = planned_tasks (금일 예정 업무)
    summary_tasks = [task.get("title", "") for task in main_tasks if task.get("title")]
    
    # 로그 출력
    print(f"\n📊 일일보고서 생성 요약:")
    print(f"  - 금일 예정 업무: {len(main_tasks)}개")
    print(f"  - 실제 완료(detail_tasks): {len(detail_tasks)}개")
    print(f"  - 특이사항: {len(special_notes)}개")
    print(f"  - 미종결 업무: {len(unresolved_tasks)}개")
    print(f"  - 익일 계획(next_day_plans): {len(next_day_plans)}개")
    if special_notes:
        print(f"  - 특이사항 내용: {', '.join(special_notes)}")
    if unresolved_tasks:
        print(f"  - 미종결 목록: {', '.join(unresolved_tasks)}")
    
    # 새 Canonical 구조로 생성
    canonical_daily = CanonicalDaily(
        header={
            "작성일자": target_date.isoformat(),
            "성명": owner
        },
        summary_tasks=summary_tasks,
        detail_tasks=detail_tasks,
        pending=unresolved_tasks,
        plans=next_day_plans,
        notes="\n".join(special_notes) if special_notes else ""
    )
    
    return CanonicalReport(
        report_id=report_id,
        report_type="daily",
        owner=owner,
        period_start=target_date,
        period_end=target_date,
        daily=canonical_daily
    )


def generate_report_id(owner: str, target_date: date) -> str:
    """
    보고서 ID 생성 (deterministic)
    
    Args:
        owner: 작성자
        target_date: 날짜
        
    Returns:
        보고서 ID
    """
    key = f"daily_{owner}_{target_date.isoformat()}"
    hash_obj = hashlib.sha256(key.encode('utf-8'))
    return hash_obj.hexdigest()[:32]

