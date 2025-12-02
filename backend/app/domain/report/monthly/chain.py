"""
월간 보고서 생성 체인
새로운 4청크 구조 기반 RAG 프롬프트 사용
"""
from datetime import date
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import uuid
import json
from calendar import monthrange

from app.domain.report.core.canonical_models import CanonicalReport, CanonicalMonthly
from app.domain.report.weekly.repository import WeeklyReportRepository
from app.domain.report.daily.repository import DailyReportRepository
from app.infrastructure.vector_store_report import get_report_vector_store
from app.domain.report.search.retriever import UnifiedRetriever
from app.llm.client import get_llm
from app.core.config import settings
from app.domain.report.core.rag_prompts import MONTHLY_REPORT_RAG_PROMPT


def get_month_range(target_date: date) -> tuple[date, date]:
    """
    target_date가 속한 달의 1일~말일 날짜 범위를 계산
    
    Args:
        target_date: 기준 날짜
        
    Returns:
        (first_day, last_day) 튜플
    """
    first_day = target_date.replace(day=1)
    last_day_num = monthrange(target_date.year, target_date.month)[1]
    last_day = target_date.replace(day=last_day_num)
    return (first_day, last_day)


def generate_monthly_report(
    db: Session,
    owner: str,
    target_date: date,
    kpi_data: Optional[Dict[str, Any]] = None
) -> CanonicalReport:
    """
    월간 보고서 자동 생성 (새로운 4청크 구조 기반)
    
    Args:
        db: 데이터베이스 세션
        owner: 작성자
        target_date: 기준 날짜 (해당 월의 아무 날짜)
        kpi_data: PostgreSQL에서 조회한 월간 KPI 숫자 JSON (선택)
        
    Returns:
        CanonicalReport (monthly)
    """
    # 1. 해당 월의 1일~말일 날짜 계산
    first_day, last_day = get_month_range(target_date)
    month_str = target_date.strftime("%Y-%m")
    
    # 2. DB에서 해당 월의 모든 주간보고서 조회
    weekly_reports = WeeklyReportRepository.list_by_owner_and_period_range(
        db=db,
        owner=owner,
        period_start=first_day,
        period_end=last_day
    )
    
    print(f"[INFO] 주간보고서 {len(weekly_reports)}개 발견: {first_day}~{last_day}")
    
    # 3. 벡터DB에서 해당 월의 일일보고서 청크 검색
    import os
    vector_store = get_report_vector_store()
    collection = vector_store.get_collection()
    embedding_model_type = os.getenv("REPORT_EMBEDDING_MODEL_TYPE", "hf")
    retriever = UnifiedRetriever(
        collection=collection,
        openai_api_key=settings.OPENAI_API_KEY,
        embedding_model_type=embedding_model_type
    )
    
    # 해당 월의 모든 일일보고서 청크 검색
    daily_chunks = retriever.search_daily(
        query=f"{owner} 월간 업무",
        owner=owner,
        period_start=first_day.isoformat(),
        period_end=last_day.isoformat(),
        n_results=500,  # 충분한 데이터 수집
        chunk_types=None  # 모든 청크 타입
    )
    
    print(f"[INFO] 일일보고서 청크 {len(daily_chunks)}개 발견: {first_day}~{last_day}")
    
    # 4. 주간보고서 JSON 변환
    weekly_reports_json = []
    for weekly_report in weekly_reports:
        if weekly_report.report_json:
            weekly_reports_json.append(weekly_report.report_json.get("weekly", {}))
    
    # 5. 일일보고서 청크 변환
    daily_chunks_data = []
    for chunk in daily_chunks:
        daily_chunks_data.append({
            "text": chunk.text,
            "metadata": chunk.metadata
        })
    
    # 6. LLM 프롬프트 구성
    llm_client = get_llm()
    
    user_prompt = f"""다음은 해당 월({month_str})의 데이터입니다:

### 주간보고서 JSON (4개):
{json.dumps(weekly_reports_json, ensure_ascii=False, indent=2)}

### 일일보고서 청크:
{json.dumps(daily_chunks_data, ensure_ascii=False, indent=2)}

### 월간 KPI 숫자 JSON:
{json.dumps(kpi_data or {}, ensure_ascii=False, indent=2)}

위 데이터를 기반으로 월간보고서를 생성해주세요."""
    
    # 7. LLM 호출
    try:
        response = llm_client.complete_json(
            system_prompt=MONTHLY_REPORT_RAG_PROMPT,
            user_prompt=user_prompt,
            temperature=0.7
        )
        
        monthly_data = response if isinstance(response, dict) else json.loads(response)
        
    except Exception as e:
        print(f"[ERROR] 월간보고서 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # 8. CanonicalMonthly 생성
    header = {
        "월": f"{target_date.year}년 {target_date.month}월",
        "작성일자": last_day.isoformat(),
        "성명": owner
    }
    
    canonical_monthly = CanonicalMonthly(
        header=header,
        weekly_summaries=monthly_data.get("weekly_summaries", {}),
        next_month_plan=monthly_data.get("next_month_plan", "")
    )
    
    # 9. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="monthly",
        owner=owner,
        period_start=first_day,
        period_end=last_day,
        monthly=canonical_monthly
    )
    
    return report
