"""
Weekly Report Chain

주간 보고서 자동 생성 체인
target_date 기준으로 해당 주의 월~금 일일보고서를 조회하여 주간 보고서를 자동 생성
"""
from datetime import date, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
import uuid
import re

from app.domain.report.canonical_models import CanonicalReport
# 하위 호환성을 위해 TaskItem, KPIItem은 임시로 유지 (나중에 제거 예정)
try:
    from app.domain.report.schemas import TaskItem, KPIItem
except ImportError:
    # 임시 호환성 클래스
    from typing import Optional
    from pydantic import BaseModel, Field
    class TaskItem(BaseModel):
        task_id: Optional[str] = None
        title: str = ""
        description: str = ""
        time_start: Optional[str] = None
        time_end: Optional[str] = None
        status: Optional[str] = None
        note: str = ""
    class KPIItem(BaseModel):
        kpi_name: str = ""
        value: str = ""
        unit: Optional[str] = None
        category: Optional[str] = None
        note: str = ""
from app.domain.daily.repository import DailyReportRepository
from app.domain.daily.models import DailyReport
from app.infrastructure.vector_store_advanced import get_vector_store
from app.domain.search.retriever import UnifiedRetriever
from app.llm.client import get_llm
from app.core.config import settings


def get_week_range(target_date: date) -> tuple[date, date]:
    """
    target_date가 속한 주의 월요일~금요일 날짜 범위를 계산
    
    Args:
        target_date: 기준 날짜
        
    Returns:
        (monday, friday) 튜플
    """
    # 해당 주의 월요일 찾기 (weekday: 0=월, 6=일)
    weekday = target_date.weekday()
    monday = target_date - timedelta(days=weekday)
    friday = monday + timedelta(days=4)
    return (monday, friday)


def aggregate_daily_reports(daily_reports: List[DailyReport]) -> dict:
    """
    여러 일일보고서를 집계하여 주간 보고서 데이터를 생성
    
    Args:
        daily_reports: 일일보고서 리스트
        
    Returns:
        집계된 데이터 dict {tasks, plans, issues}
    """
    all_tasks = []
    all_plans = []
    all_issues = []
    
    for daily_report in daily_reports:
        report_json = daily_report.report_json
        
        # tasks 수집
        if "tasks" in report_json:
            all_tasks.extend(report_json["tasks"])
        
        # plans 수집
        if "plans" in report_json:
            all_plans.extend(report_json["plans"])
        
        # issues 수집
        if "issues" in report_json:
            all_issues.extend(report_json["issues"])
    
    return {
        "tasks": all_tasks,
        "plans": all_plans,
        "issues": all_issues
    }


def calculate_completion_rate(tasks: List[dict]) -> float:
    """
    완료율 계산: 완료된 task / 전체 task
    
    Args:
        tasks: TaskItem dict 리스트
        
    Returns:
        완료율 (0.0 ~ 1.0)
    """
    if not tasks:
        return 0.0
    
    completed = sum(1 for task in tasks if task.get("status") == "완료")
    return completed / len(tasks)


def filter_person_names(text: str) -> bool:
    """
    사람 이름이 포함된 텍스트인지 확인
    
    Args:
        text: 확인할 텍스트
        
    Returns:
        True: 사람 이름이 포함됨, False: 포함되지 않음
    """
    # 한국 성씨 패턴 (김, 박, 최, 이 등)
    person_name_pattern = r'\b(김|박|최|이)[가-힣]{1,3}\b'
    return bool(re.search(person_name_pattern, text))


def generate_weekly_important_tasks(
    owner: str,
    period_start: date,
    period_end: date,
    tasks: List[TaskItem],
    llm_client=None
) -> List[str]:
    """
    벡터DB에서 주간 데이터를 검색하여 주간 중요 업무 3개 생성
    
    우선순위 기준:
    1) 매출 또는 유지율에 직접 영향
    2) 고객 리스크 관리 (고객 요청 처리 등)
    3) 규제·법적 준수 필요 업무
    4) 고객 요청 처리 등 민원 가능성 높은 업무
    5) 여러 고객에게 반복적으로 영향
    6) 지연 시 리스크 큰 업무(마감 등)
    
    Args:
        owner: 작성자
        period_start: 시작 날짜 (월요일)
        period_end: 종료 날짜 (금요일)
        tasks: 주간 보고서의 모든 TaskItem 리스트 (요일별 세부 업무)
        llm_client: LLM 클라이언트 (None이면 생성)
        
    Returns:
        주간 중요 업무 리스트 (최대 3개, 큰 카테고리 형태)
    """
    try:
        # 1. 벡터DB에서 주간 데이터 검색
        vector_store = get_vector_store()
        collection = vector_store.get_collection()
        retriever = UnifiedRetriever(
            collection=collection,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        print(f"[DEBUG] 주간 중요 업무 검색 시작: owner={owner}, period={period_start}~{period_end}")
        
        # 주간 범위의 일일보고서 데이터 검색 (task 타입만)
        all_results = retriever.search_daily(
            query=f"{owner} 주간 중요 업무",
            owner=owner,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            n_results=50,  # 충분한 데이터 수집
            chunk_types=["detail_chunk"]  # detail_chunk 타입만 검색
        )
        
        # 날짜 필터로 검색 결과가 없으면, 날짜 필터 없이 검색 (최근 데이터 사용)
        if not all_results:
            print(f"[WARNING] 해당 기간 데이터를 찾을 수 없음: {owner}, {period_start}~{period_end}")
            print(f"[INFO] 날짜 필터 없이 최근 데이터로 검색 시도...")
            all_results = retriever.search_daily(
                query=f"{owner} 주간 중요 업무",
                owner=owner,
                n_results=50,
                chunk_types=["detail_chunk"]
            )
            if not all_results:
                print(f"[WARNING] 데이터를 찾을 수 없음: {owner}")
                # 벡터DB 데이터가 없으면 tasks 파라미터만 사용
                all_results = []
        
        print(f"[INFO] 벡터DB 검색 완료: {len(all_results)}개 청크 발견")
        
        # 2. 사람 이름이 포함된 업무 제외
        filtered_texts = []
        for result in all_results:
            text = result.text
            if not filter_person_names(text):
                filtered_texts.append(text)
        
        print(f"[INFO] 사람 이름 필터링 후: {len(filtered_texts)}개 청크")
        
        # 3. tasks 파라미터에서도 텍스트 추출
        task_texts = []
        for task in tasks:
            task_str = task.title
            if task.description:
                task_str += f": {task.description}"
            task_texts.append(task_str)
        
        # 4. 벡터DB 데이터와 tasks 파라미터 데이터 결합
        combined_texts = filtered_texts.copy()
        combined_texts.extend(task_texts)
        
        if not combined_texts:
            print(f"[WARNING] 주간 중요 업무 생성: 데이터가 비어있음")
            return []
        
        print(f"[INFO] 총 {len(combined_texts)}개 업무 항목 수집 (벡터DB: {len(filtered_texts)}개, tasks: {len(task_texts)}개)")
        
        # 5. LLM 클라이언트 생성
        if llm_client is None:
            llm_client = get_llm()
        
        system_prompt = """너는 주간 중요 업무를 선정하는 AI입니다.

주어진 주간 보고서의 요일별 세부 업무 항목들을 분석하여, 다음 우선순위 기준에 따라 중요한 업무 3개를 큰 카테고리 형태로 요약하세요.

우선순위 기준 (높은 순서대로):
1) 매출 또는 유지율에 직접 영향 (중요 업무 등)
2) 고객 리스크 관리 (고객 요청 처리, 위험 관리 등)
3) 규제·법적 준수 필요 업무 (법규 준수, 서류 제출, 마감 등)
4) 고객 요청 처리 등 민원 가능성 높은 업무 (고객 대응, 민원 처리)
5) 여러 고객에게 반복적으로 영향 (대량 처리, 일괄 업무)
6) 지연 시 리스크 큰 업무 (마감일, 제출 기한 등)

규칙:
1. 반드시 3개의 중요 업무를 생성
2. 각 업무는 큰 카테고리 형태로 요약 (예: "고객 리스크 관리 및 고객 요청 처리", "중요 업무 및 매출 확대", "규제 준수 및 마감 업무")
3. 구체적인 고객 이름이나 개별 업무가 아닌, 전체적인 업무 카테고리로 작성
4. 위 우선순위 기준에 가장 잘 맞는 업무들을 선정
5. 유사한 업무들은 하나의 카테고리로 묶어서 요약
6. 주간 보고서의 요일별 세부업무 중 위 기준 충족 항목을 묶어서 3개의 큰 카테고리 형태로 요약
7. 특정 보험 상품명이나 도메인 특정 단어를 사용하지 말고, 실제 데이터에서 나타난 업무 내용을 기반으로만 요약하세요

반드시 다음 JSON 형식으로만 응답:
{
  "important_tasks": [
    "중요 업무 1 (큰 카테고리)",
    "중요 업무 2 (큰 카테고리)",
    "중요 업무 3 (큰 카테고리)"
  ]
}"""

        # 상위 100개만 사용 (너무 많으면 토큰 초과)
        sample_tasks = combined_texts[:100]
        user_prompt = f"""다음은 {owner}의 {period_start}~{period_end} 주간 보고서의 요일별 세부 업무 항목들입니다:

{chr(10).join([f"- {task[:200]}" for task in sample_tasks])}

위 업무 항목들을 분석하여, 우선순위 기준에 따라 중요한 업무 3개를 큰 카테고리 형태로 요약해주세요."""

        llm_response = llm_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=500
        )
        
        important_tasks = llm_response.get("important_tasks", [])
        
        # 최대 3개로 제한 및 빈 문자열 제거
        important_tasks = [t.strip() for t in important_tasks if t and t.strip()][:3]
        
        print(f"📌 주간 중요 업무 생성 완료: {len(important_tasks)}개")
        for idx, task in enumerate(important_tasks, 1):
            print(f"   {idx}. {task}")
        
        return important_tasks
        
    except Exception as e:
        print(f"[ERROR] 주간 중요 업무 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_daily_tasks_summary(
    owner: str,
    target_date: date,
    llm_client=None
) -> List[str]:
    """
    특정 날짜의 일일보고서 데이터를 가져와서 의미 기반으로 유사한 업무를 묶어
    대표 업무 3개로 요약
    
    Args:
        owner: 작성자
        target_date: 대상 날짜 (YYYY-MM-DD)
        llm_client: LLM 클라이언트 (None이면 생성)
        
    Returns:
        요약된 업무 리스트 (최대 3개)
    """
    try:
        # 1. 벡터DB에서 해당 날짜의 일일보고서 데이터 검색
        vector_store = get_vector_store()
        collection = vector_store.get_collection()
        retriever = UnifiedRetriever(
            collection=collection,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        print(f"[DEBUG] 요일별 업무 검색 시작: owner={owner}, date={target_date}")
        
        # 해당 날짜의 task 타입 데이터 검색
        task_results = retriever.search_daily(
            query=f"{owner} {target_date.isoformat()} 업무",
            owner=owner,
            single_date=target_date.isoformat(),
            n_results=50,  # 충분한 데이터 수집
            chunk_types=["detail_chunk"]
        )
        
        # 날짜 필터로 검색 결과가 없으면, 날짜 필터 없이 검색
        if not task_results:
            print(f"[WARNING] 해당 날짜 task 데이터를 찾을 수 없음: {owner}, {target_date}")
            task_results = retriever.search_daily(
                query=f"{owner} 업무",
                owner=owner,
                n_results=30,
                chunk_types=["detail_chunk"]
            )
        
        if not task_results:
            print(f"[WARNING] 데이터를 찾을 수 없음: {owner}")
            return []
        
        print(f"[INFO] 벡터DB 검색 완료: {len(task_results)}개 청크 발견")
        
        # 2. 사람 이름이 포함된 업무 제외 및 시간 정보 제거
        filtered_texts = []
        for result in task_results:
            text = result.text
            
            # 사람 이름 필터링
            if filter_person_names(text):
                continue
            
            # 시간 정보 제거 (정규식 사용)
            # "10:00~11:00", "13:00~14:00" 같은 패턴 제거
            # HH:MM~HH:MM 패턴 제거
            text = re.sub(r'\d{1,2}:\d{2}~\d{1,2}:\d{2}', '', text)
            # HH:MM - HH:MM 패턴 제거
            text = re.sub(r'\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}', '', text)
            # 단독 시간 패턴 제거 (예: "10:00", "13:00")
            text = re.sub(r'\b\d{1,2}:\d{2}\b', '', text)
            # "time_slot" 같은 메타데이터 키워드 제거
            text = re.sub(r'time_slot|시간대|시간|시각|타임슬롯', '', text, flags=re.IGNORECASE)
            
            # 공백 정리
            text = ' '.join(text.split())
            
            if text.strip():  # 빈 텍스트가 아니면 추가
                filtered_texts.append(text)
        
        if not filtered_texts:
            print(f"[WARNING] 필터링 후 데이터가 없음")
            return []
        
        print(f"[INFO] 사람 이름 및 시간 정보 필터링 후: {len(filtered_texts)}개 청크")
        
        # 3. LLM으로 의미 기반 유사 업무 묶기 및 요약
        if llm_client is None:
            llm_client = get_llm()
        
        system_prompt = """너는 일일 업무를 요약하는 AI입니다.

주어진 하루의 세부 업무 항목들을 분석하여, 의미 기반으로 유사한 업무를 묶어서 대표 업무 3개로 요약하세요.

요약 규칙:
1. 의미적으로 유사한 업무들을 하나로 묶어서 요약 (예: "고객 상담", "문서 처리", "자료 정리" 등)
2. 반드시 3개의 대표 업무를 생성
3. 각 업무는 구체적이고 명확하게 작성
4. 사람 이름이나 개인정보는 제외 (이미 필터링됨)
5. 시간, 시간대, 시각, 타임슬롯 관련 어떤 정보도 생성하지 않는다. 요약은 업무 내용(텍스트)만 기반으로 한다.
6. 유사한 업무가 많으면 가장 중요한 업무를 대표로 선정
7. 요약 결과에 시간 관련 표현이 포함되면 안 된다.
8. 특정 보험 상품명이나 도메인 특정 단어를 사용하지 말고, 실제 데이터에서 나타난 업무 내용을 기반으로만 요약하세요

반드시 다음 JSON 형식으로만 응답:
{
  "daily_tasks": [
    "대표 업무 1 (유사 업무들을 묶어서 요약)",
    "대표 업무 2 (유사 업무들을 묶어서 요약)",
    "대표 업무 3 (유사 업무들을 묶어서 요약)"
  ]
}"""

        # 상위 30개만 사용 (너무 많으면 토큰 초과)
        sample_tasks = filtered_texts[:30]
        user_prompt = f"""다음은 {owner}의 {target_date.isoformat()} 일일보고서의 세부 업무 항목들입니다:

{chr(10).join([f"- {task[:200]}" for task in sample_tasks])}

위 업무 항목들을 의미 기반으로 유사한 업무를 묶어서 대표 업무 3개로 요약해주세요. 시간 정보는 절대 포함하지 마세요."""

        llm_response = llm_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=500
        )
        
        daily_tasks = llm_response.get("daily_tasks", [])
        
        # 최대 3개로 제한 및 빈 문자열 제거
        daily_tasks = [t.strip() for t in daily_tasks if t and t.strip()][:3]
        
        # 최종 검증: 시간 정보가 포함되어 있으면 제거
        cleaned_tasks = []
        for task in daily_tasks:
            # 시간 패턴이 포함되어 있는지 확인
            if re.search(r'\d{1,2}:\d{2}', task):
                # 시간 패턴 제거
                cleaned_task = re.sub(r'\d{1,2}:\d{2}~\d{1,2}:\d{2}', '', task)
                cleaned_task = re.sub(r'\d{1,2}:\d{2}\s*-\s*\d{1,2}:\d{2}', '', cleaned_task)
                cleaned_task = re.sub(r'\b\d{1,2}:\d{2}\b', '', cleaned_task)
                cleaned_task = ' '.join(cleaned_task.split())
                if cleaned_task.strip():
                    cleaned_tasks.append(cleaned_task.strip())
            else:
                cleaned_tasks.append(task)
        
        daily_tasks = cleaned_tasks[:3]
        
        print(f"📅 {target_date.isoformat()} 요약 완료: {len(daily_tasks)}개")
        for idx, task in enumerate(daily_tasks, 1):
            print(f"   {idx}. {task}")
        
        return daily_tasks
        
    except Exception as e:
        print(f"[ERROR] 요일별 업무 요약 실패: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_weekly_daily_tasks(
    owner: str,
    period_start: date,
    period_end: date,
    llm_client=None
) -> Dict[str, List[str]]:
    """
    주간의 각 요일별로 일일보고서 데이터를 가져와서 대표 업무 3개로 요약
    
    Args:
        owner: 작성자
        period_start: 시작 날짜 (월요일)
        period_end: 종료 날짜 (금요일)
        llm_client: LLM 클라이언트 (None이면 생성)
        
    Returns:
        요일별 업무 딕셔너리 {요일명: [업무1, 업무2, 업무3]}
    """
    # 요일 이름 매핑
    weekday_names = ["월요일", "화요일", "수요일", "목요일", "금요일"]
    
    # 주간 날짜 리스트 생성
    week_dates = []
    current = period_start
    while current <= period_end:
        week_dates.append(current)
        current += timedelta(days=1)
    
    # LLM 클라이언트 생성
    if llm_client is None:
        llm_client = get_llm()
    
    # 각 요일별로 업무 요약
    daily_tasks_by_day = {}
    for idx, target_date in enumerate(week_dates):
        if idx < len(weekday_names):
            weekday_name = weekday_names[idx]
            print(f"\n[DEBUG] {weekday_name} ({target_date.isoformat()}) 업무 요약 시작...")
            
            daily_tasks = generate_daily_tasks_summary(
                owner=owner,
                target_date=target_date,
                llm_client=llm_client
            )
            
            # 데이터가 없으면 빈 리스트 저장 (보고서 생성은 계속 진행)
            if not daily_tasks:
                print(f"[WARNING] {weekday_name} 데이터가 없어 빈 리스트로 저장")
            
            daily_tasks_by_day[weekday_name] = daily_tasks
    
    return daily_tasks_by_day


def generate_weekly_goals(
    owner: str,
    period_start: date,
    period_end: date,
    llm_client=None
) -> List[str]:
    """
    벡터DB에서 주간 데이터를 검색하여 주간 업무 목표 3개 생성
    
    Args:
        owner: 작성자
        period_start: 시작 날짜 (월요일)
        period_end: 종료 날짜 (금요일)
        llm_client: LLM 클라이언트 (None이면 생성)
        
    Returns:
        주간 업무 목표 리스트 (최대 3개)
    """
    try:
        # 1. 벡터DB에서 주간 데이터 검색
        vector_store = get_vector_store()
        collection = vector_store.get_collection()
        retriever = UnifiedRetriever(
            collection=collection,
            openai_api_key=settings.OPENAI_API_KEY
        )
        
        # 디버깅: 먼저 필터 없이 검색해서 데이터가 있는지 확인
        print(f"[DEBUG] 주간 목표 검색 시작: owner={owner}, period={period_start}~{period_end}")
        
        # 필터 없이 전체 검색 (데이터 존재 확인)
        try:
            # 컬렉션에서 직접 샘플 데이터 가져오기 (get 사용)
            sample_data = collection.get(limit=5)
            print(f"[DEBUG] 컬렉션 샘플 데이터 ({len(sample_data.get('ids', []))}개):")
            if sample_data.get('metadatas'):
                for i, meta in enumerate(sample_data['metadatas'][:3]):
                    print(f"  [{i+1}] owner={meta.get('owner', 'N/A')}, doc_type={meta.get('doc_type', 'N/A')}, chunk_type={meta.get('chunk_type', 'N/A')}, date={meta.get('date', 'N/A')}, period_start={meta.get('period_start', 'N/A')}")
        except Exception as e:
            print(f"[DEBUG] 샘플 데이터 조회 실패: {e}")
        
        # 필터 없이 전체 검색 (데이터 존재 확인)
        try:
            # 필터 없이 검색
            all_data = retriever.search_all(
                query=f"{owner} 업무",
                n_results=10
            )
            print(f"[DEBUG] 필터 없이 전체 검색 결과: {len(all_data)}개")
            if all_data:
                print(f"[DEBUG] 샘플 메타데이터: {all_data[0].metadata}")
        except Exception as e:
            print(f"[DEBUG] 전체 검색 실패: {e}")
        
        # 필터 없이 owner만으로 검색 (데이터 존재 확인)
        test_results = retriever.search_daily(
            query=f"{owner} 업무",
            owner=owner,
            n_results=10,
            chunk_types=["detail_chunk", "plan_chunk"]
        )
        print(f"[DEBUG] owner 필터 검색 결과: {len(test_results)}개")
        if test_results:
            print(f"[DEBUG] 샘플 메타데이터: {test_results[0].metadata}")
        
        # 주간 범위의 일일보고서 데이터 검색 (period_start와 period_end를 사용하여 한 번에 검색)
        all_results = retriever.search_daily(
            query=f"{owner} 주간 업무 계획 목표",
            owner=owner,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            n_results=50,  # 충분한 데이터 수집
            chunk_types=["detail_chunk", "plan_chunk"]
        )
        
        # 날짜 필터로 검색 결과가 없으면, 날짜 필터 없이 검색 (최근 데이터 사용)
        if not all_results:
            print(f"[WARNING] 해당 기간 데이터를 찾을 수 없음: {owner}, {period_start}~{period_end}")
            print(f"[INFO] 날짜 필터 없이 최근 데이터로 검색 시도...")
            all_results = retriever.search_daily(
                query=f"{owner} 주간 업무 계획 목표",
                owner=owner,
                n_results=50,  # 충분한 데이터 수집
                chunk_types=["detail_chunk", "plan_chunk"]
            )
            if all_results:
                print(f"[INFO] 날짜 필터 없이 {len(all_results)}개 청크 발견 (최근 데이터 사용)")
            else:
                print(f"[WARNING] 데이터를 찾을 수 없음: {owner}")
                return []
        
        print(f"[INFO] 벡터DB 검색 완료: {len(all_results)}개 청크 발견")
        
        # 2. 사람 이름이 포함된 업무 제외
        filtered_texts = []
        for result in all_results:
            text = result.text
            if not filter_person_names(text):
                filtered_texts.append(text)
        
        if not filtered_texts:
            print(f"[WARNING] 필터링 후 데이터가 없음")
            return []
        
        print(f"[INFO] 사람 이름 필터링 후: {len(filtered_texts)}개 청크")
        
        # 3. 해당 주간의 모든 일일보고서에서 task, issue, plan 데이터 수집
        # DB에서 일일보고서 조회하여 실제 데이터 가져오기
        from app.domain.daily.repository import DailyReportRepository
        from app.infrastructure.database.session import SessionLocal
        
        db = SessionLocal()
        try:
            daily_reports = DailyReportRepository.list_by_owner_and_date_range(
                db=db,
                owner=owner,
                start_date=period_start,
                end_date=period_end
            )
            
            # 일일보고서에서 task, issue, plan 추출
            all_tasks = []
            all_issues = []
            all_plans = []
            
            for daily_report in daily_reports:
                report_json = daily_report.report_json
                
                # tasks 수집
                if "tasks" in report_json:
                    for task in report_json["tasks"]:
                        task_text = task.get("title", "")
                        if task.get("description"):
                            task_text += f": {task.get('description')}"
                        all_tasks.append(task_text)
                
                # issues 수집 (미종결 업무)
                if "issues" in report_json:
                    all_issues.extend(report_json["issues"])
                
                # plans 수집 (익일 계획)
                if "plans" in report_json:
                    all_plans.extend(report_json["plans"])
            
            # VectorDB 검색 결과와 DB 데이터 결합
            combined_texts = filtered_texts.copy()
            combined_texts.extend(all_tasks)
            combined_texts.extend(all_issues)
            combined_texts.extend(all_plans)
            
            print(f"[INFO] DB에서 수집한 데이터: task {len(all_tasks)}개, issue {len(all_issues)}개, plan {len(all_plans)}개")
            
        except Exception as e:
            print(f"[WARNING] DB 데이터 수집 실패: {e}")
            combined_texts = filtered_texts
        finally:
            db.close()
        
        # 4. LLM으로 주간 업무 목표 3개 생성 (새로운 기준 적용)
        if llm_client is None:
            llm_client = get_llm()
        
        system_prompt = """너는 주간 업무 목표를 생성하는 AI입니다.

주어진 한 주간의 일일보고서 데이터(시간별 세부 업무, 미종결 업무, 계획)를 분석하여, 다음 기준에 따라 주간 업무 목표 3개를 생성하세요.

선정 기준 (우선순위 순):
1) 이번 주 일일보고서 세부 업무에서 반복적으로 등장한 테마
2) 미종결 업무 중 다음 주로 반드시 이월되는 항목
3) 고객 리스크 증가(고객 요청 처리, 민원 가능성 등)
4) 매출/유지율에 직접 영향을 주는 진행 중 과제
5) 다음 주 특정 일정/시즌에 의해 필수로 필요한 업무

규칙:
1. 반드시 3개의 목표를 생성
2. 위 기준을 충족하는 요소를 묶어서 목표 형태로 요약
3. 구체적이고 실행 가능한 목표로 작성
4. 사람 이름이 포함된 업무는 제외 (이미 필터링됨)
5. 주간 단위의 큰 계획으로 요약하되, 구체적인 실행 내용 포함
6. 특정 보험 상품명이나 도메인 특정 단어를 사용하지 말고, 실제 데이터에서 나타난 업무 내용을 기반으로만 목표를 생성하세요

반드시 다음 JSON 형식으로만 응답:
{
  "goals": [
    "목표 1 (기준에 맞는 구체적 내용)",
    "목표 2 (기준에 맞는 구체적 내용)",
    "목표 3 (기준에 맞는 구체적 내용)"
  ]
}"""

        # 충분한 데이터 사용 (최대 100개)
        sample_texts = combined_texts[:100]
        user_prompt = f"""다음은 {owner}의 {period_start}~{period_end} 주간 일일보고서 데이터입니다:

=== 시간별 세부 업무 ===
{chr(10).join([f"- {text[:200]}" for text in sample_texts if any(keyword in text for keyword in ['업무', '상담', '처리', '작업'])])}

=== 미종결 업무 ===
{chr(10).join([f"- {text[:200]}" for text in sample_texts if '미종결' in text or '이슈' in text or '미완료' in text])}

=== 계획 ===
{chr(10).join([f"- {text[:200]}" for text in sample_texts if '계획' in text or '예정' in text])}

위 데이터를 분석하여, 제시된 5가지 기준에 따라 주간 업무 목표 3개를 생성해주세요."""

        llm_response = llm_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=500
        )
        
        goals = llm_response.get("goals", [])
        
        # 최대 3개로 제한 및 빈 문자열 제거
        goals = [g.strip() for g in goals if g and g.strip()][:3]
        
        return goals
        
    except Exception as e:
        print(f"[ERROR] 주간 업무 목표 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return []


def generate_weekly_report(
    db: Session,
    owner: str,
    target_date: date
) -> CanonicalReport:
    """
    주간 보고서 자동 생성
    
    Args:
        db: 데이터베이스 세션
        owner: 작성자
        target_date: 기준 날짜 (해당 주의 아무 날짜)
        
    Returns:
        CanonicalReport (weekly)
        
    Raises:
        ValueError: 해당 기간에 일일보고서가 없는 경우
    """
    # 1. 해당 주의 월~금 날짜 계산
    monday, friday = get_week_range(target_date)
    
    # 2. 벡터DB에서 주간 데이터 검색
    vector_store = get_vector_store()
    collection = vector_store.get_collection()
    retriever = UnifiedRetriever(
        collection=collection,
        openai_api_key=settings.OPENAI_API_KEY
    )
    
    print(f"[DEBUG] 주간 보고서 데이터 검색: owner={owner}, period={monday}~{friday}")
    
    # 2-1. 요일별 세부 업무 (task 타입) 검색
    task_results = retriever.search_daily(
        query=f"{owner} 주간 업무",
        owner=owner,
        period_start=monday.isoformat(),
        period_end=friday.isoformat(),
        n_results=200,  # 충분한 데이터 수집
        chunk_types=["detail_chunk"]
    )
    
    # 날짜 필터로 검색 결과가 없으면, 날짜 필터 없이 검색
    if not task_results:
        print(f"[WARNING] 해당 기간 task 데이터를 찾을 수 없음: {owner}, {monday}~{friday}")
        print(f"[INFO] 날짜 필터 없이 최근 데이터로 검색 시도...")
        task_results = retriever.search_daily(
            query=f"{owner} 주간 업무",
            owner=owner,
            n_results=200,
            chunk_types=["detail_chunk"]
        )
    
    print(f"[INFO] 벡터DB task 검색 완료: {len(task_results)}개 청크 발견")
    
    # 2-2. 특이사항 (issue 타입) 검색
    issue_results = retriever.search_daily(
        query=f"{owner} 주간 특이사항 이슈",
        owner=owner,
        period_start=monday.isoformat(),
        period_end=friday.isoformat(),
        n_results=100,
        chunk_types=["pending_chunk"]
    )
    
    if not issue_results:
        issue_results = retriever.search_daily(
            query=f"{owner} 주간 특이사항 이슈",
            owner=owner,
            n_results=100,
            chunk_types=["pending_chunk"]
        )
    
    print(f"[INFO] 벡터DB issue 검색 완료: {len(issue_results)}개 청크 발견")
    
    # 2-3. 계획 (plan 타입) 검색
    plan_results = retriever.search_daily(
        query=f"{owner} 주간 계획",
        owner=owner,
        period_start=monday.isoformat(),
        period_end=friday.isoformat(),
        n_results=100,
        chunk_types=["plan_chunk"]
    )
    
    if not plan_results:
        plan_results = retriever.search_daily(
            query=f"{owner} 주간 계획",
            owner=owner,
            n_results=100,
            chunk_types=["plan_chunk"]
        )
    
    print(f"[INFO] 벡터DB plan 검색 완료: {len(plan_results)}개 청크 발견")
    
    # 3. 벡터DB 검색 결과를 TaskItem, Issue, Plan으로 변환
    # task_results에서 TaskItem 생성
    tasks = []
    seen_task_ids = set()
    for result in task_results:
        # 메타데이터에서 task 정보 추출
        metadata = result.metadata
        task_id = metadata.get("task_id", f"task_{len(tasks)}")
        
        # 중복 제거 (같은 task_id는 한 번만)
        if task_id in seen_task_ids:
            continue
        seen_task_ids.add(task_id)
        
        # TaskItem 생성
        try:
            # time_slot 파싱 (예: "09:00~10:00" -> time_start="09:00", time_end="10:00")
            time_slot = metadata.get("time_slot", "")
            time_start, time_end = None, None
            if time_slot and "~" in time_slot:
                parts = time_slot.split("~")
                if len(parts) == 2:
                    time_start = parts[0].strip()
                    time_end = parts[1].strip()
            
            task_item = TaskItem(
                task_id=task_id,
                title=result.text[:100] if len(result.text) > 100 else result.text,
                description=result.text,
                time_start=time_start,
                time_end=time_end,
                status=metadata.get("status", "완료")
            )
            tasks.append(task_item)
        except Exception as e:
            print(f"[WARNING] TaskItem 변환 실패: {e}, text={result.text[:50]}")
            continue
    
    # issue_results에서 Issue 생성
    issues = []
    seen_issue_ids = set()
    for result in issue_results:
        issue_id = result.chunk_id
        if issue_id in seen_issue_ids:
            continue
        seen_issue_ids.add(issue_id)
        issues.append(result.text)
    
    # plan_results에서 Plan 생성
    plans = []
    seen_plan_ids = set()
    for result in plan_results:
        plan_id = result.chunk_id
        if plan_id in seen_plan_ids:
            continue
        seen_plan_ids.add(plan_id)
        plans.append(result.text)
    
    print(f"[INFO] 벡터DB 데이터 변환 완료: tasks={len(tasks)}개, issues={len(issues)}개, plans={len(plans)}개")
    
    if not tasks:
        raise ValueError(f"해당 기간({monday}~{friday})에 벡터DB에서 업무 데이터를 찾을 수 없습니다.")
    
    # 4. 완료율 계산
    task_dicts = [{"status": task.status} for task in tasks]
    completion_rate = calculate_completion_rate(task_dicts)
    
    # 6. LLM 클라이언트 생성
    llm_client = get_llm()
    
    # 7. 요일별 세부 업무 생성 (새로 추가)
    print(f"\n{'='*80}")
    print(f"📅 요일별 세부 업무 생성 시작")
    print(f"{'='*80}")
    daily_tasks_by_day = generate_weekly_daily_tasks(
        owner=owner,
        period_start=monday,
        period_end=friday,
        llm_client=llm_client
    )
    print(f"✅ 요일별 세부 업무 생성 완료")
    
    # 모든 요일에 데이터가 없으면 보고서 생성 중단
    all_empty = all(not tasks_list for tasks_list in daily_tasks_by_day.values())
    if all_empty:
        raise ValueError(
            f"해당 기간({monday}~{friday})에 요일별 세부 업무 데이터를 찾을 수 없습니다. "
            "ChromaDB에서 task 데이터가 존재하지 않아 보고서를 생성할 수 없습니다."
        )
    
    for weekday, tasks_list in daily_tasks_by_day.items():
        print(f"   {weekday}: {len(tasks_list)}개")
    
    # 8. 주간 업무 목표 생성 (벡터DB 기반)
    weekly_goals = generate_weekly_goals(
        owner=owner,
        period_start=monday,
        period_end=friday,
        llm_client=llm_client
    )
    
    print(f"📋 주간 업무 목표 생성 완료: {len(weekly_goals)}개")
    for idx, goal in enumerate(weekly_goals, 1):
        print(f"   {idx}. {goal}")
    
    # 9. 주간 중요 업무 생성 (벡터DB 기반)
    important_tasks = generate_weekly_important_tasks(
        owner=owner,
        period_start=monday,
        period_end=friday,
        tasks=tasks,
        llm_client=llm_client
    )
    
    # 10. CanonicalReport 생성
    report = CanonicalReport(
        report_id=str(uuid.uuid4()),
        report_type="weekly",
        owner=owner,
        period_start=monday,
        period_end=friday,
        tasks=tasks,
        issues=issues,
        plans=plans,
        metadata={
            "source": "weekly_chain",
            "task_count": len(tasks),
            "issue_count": len(issues),
            "plan_count": len(plans),
            "completion_rate": round(completion_rate, 2),
            "week_dates": [monday.isoformat(), friday.isoformat()],
            "weekly_goals": weekly_goals,  # 주간 업무 목표
            "important_tasks": important_tasks,  # 주간 중요 업무
            "daily_tasks_by_day": daily_tasks_by_day  # 요일별 세부 업무 (새로 추가)
        }
    )
    
    return report

