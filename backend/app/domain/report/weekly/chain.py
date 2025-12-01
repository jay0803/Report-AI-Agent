"""
주간 보고서 생성 체인
새로운 4청크 구조 기반 RAG 프롬프트 사용
"""
from datetime import date, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
import uuid
import json

from app.domain.report.core.canonical_models import CanonicalReport, CanonicalWeekly
from app.infrastructure.vector_store_advanced import get_vector_store
from app.domain.report.search.retriever import UnifiedRetriever
from app.llm.client import get_llm
from app.core.config import settings
from app.domain.report.core.rag_prompts import WEEKLY_REPORT_RAG_PROMPT


def get_week_range(target_date: date) -> tuple[date, date]:
    """해당 주의 월요일~금요일 날짜 범위 계산"""
    weekday = target_date.weekday()
    monday = target_date - timedelta(days=weekday)
    friday = monday + timedelta(days=4)
    return (monday, friday)


def generate_weekly_report(
    db: Session,
    owner: str,
    target_date: date
) -> CanonicalReport:
    """
    주간 보고서 자동 생성 (새로운 4청크 구조 기반)
    
    Args:
        db: 데이터베이스 세션
        owner: 작성자
        target_date: 기준 날짜 (해당 주의 아무 날짜)
        
    Returns:
        CanonicalReport (weekly)
    """
    # 1. 해당 주의 월~금 날짜 계산
    monday, friday = get_week_range(target_date)
    
    # ISO week number 계산
    iso_calendar = monday.isocalendar()
    week_str = f"{iso_calendar[0]}-W{iso_calendar[1]:02d}"
    
    # 2. 벡터DB에서 주간 데이터 검색 (새로운 4청크 구조)
    import os
    vector_store = get_vector_store()
    collection = vector_store.get_collection()
    embedding_model_type = os.getenv("REPORT_EMBEDDING_MODEL_TYPE", "hf")
    retriever = UnifiedRetriever(
        collection=collection,
        openai_api_key=settings.OPENAI_API_KEY,
        embedding_model_type=embedding_model_type
    )
    
    print(f"[DEBUG] 주간 보고서 데이터 검색: owner={owner}, week={week_str}")
    
    # week 필터로 모든 일일보고서 청크 검색 (5일 × 4청크 = 20개)
    all_chunks = retriever.search_daily(
        query=f"{owner} 주간 업무",
        owner=owner,
        week=week_str,
        n_results=20,  # 정확히 20개
        chunk_types=None  # 모든 청크 타입
    )
    
    print(f"[INFO] 벡터DB 검색 완료: {len(all_chunks)}개 청크 발견")
    
    if len(all_chunks) == 0:
        raise ValueError(f"해당 주({week_str})에 일일보고서 데이터를 찾을 수 없습니다.")
    
    # 3. 검색 결과를 프롬프트 형식으로 변환
    search_results = []
    for chunk in all_chunks:
        search_results.append({
            "text": chunk.text,
            "metadata": chunk.metadata
        })
    
    # 4. LLM 프롬프트 구성
    llm_client = get_llm()
    
    user_prompt = f"""다음은 ChromaDB에서 검색된 일일보고서 청크 데이터입니다:

{json.dumps(search_results, ensure_ascii=False, indent=2)}

위 데이터를 기반으로 주간보고서를 생성해주세요.
week = "{week_str}"인 모든 청크를 분석하여 주간보고서를 작성하세요."""
    
    # 5. LLM 호출
    try:
        response = llm_client.complete_json(
            system_prompt=WEEKLY_REPORT_RAG_PROMPT.format(week_number=week_str),
            user_prompt=user_prompt,
            temperature=0.7
        )
        
        weekly_data = response if isinstance(response, dict) else json.loads(response)
        
    except Exception as e:
        print(f"[ERROR] 주간보고서 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # 6. CanonicalWeekly 생성
    header = {
        "작성일자": f"{monday.isoformat()} ~ {friday.isoformat()}",
        "성명": owner
    }
    
    canonical_weekly = CanonicalWeekly(
        header=header,
        weekly_goals=weekly_data.get("weekly_goals", []),
        weekday_tasks=weekly_data.get("weekday_tasks", {}),
        weekly_highlights=weekly_data.get("weekly_highlights", []),
        notes=weekly_data.get("notes", "")
    )
    
    # 7. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="weekly",
        owner=owner,
        period_start=monday,
        period_end=friday,
        weekly=canonical_weekly
    )
    
    return report
