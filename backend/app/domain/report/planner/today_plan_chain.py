"""
Today Plan Chain

LangChain 기반 오늘의 일정 플래닝 체인

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Optional, List
from datetime import date

from app.llm.client import LLMClient
from app.domain.report.planner.tools import YesterdayReportTool
from app.domain.report.search.retriever import UnifiedRetriever, UnifiedSearchResult
from app.domain.report.planner.schemas import (
    TodayPlanRequest,
    TodayPlanResponse,
    TaskItem
)


class TodayPlanGenerator:
    """오늘의 일정 플래닝 생성기"""
    
    SYSTEM_PROMPT = """너는 AI 업무 플래너이다.

**우선순위 순서**:
1. **전날 작성한 익일 업무 계획(next_day_plan) - 최우선** (절대 빼먹으면 안 됨!)
2. **미종결 업무(unresolved)** (2순위)
3. **최근 5일 업무 패턴(similar_tasks)에서 미완료된 업무** (3순위)

규칙:
1. **최소 3개 이상의 업무를 반드시 생성** (매우 중요!)
2. **익일 업무 계획이 최우선**: 전날 작성한 익일 업무 계획을 반드시 포함 (절대 빼먹으면 안 됨!)
3. **미종결 업무**: 전날 미종결 업무가 있으면 2순위로 포함
4. **미완료 업무만 플래닝**: 최근 5일간 있었던 미종결 업무 중 다음날에 완료된 업무는 제외되어 제공되므로, 제공된 업무만 분석
5. **반복 업무 우선 플래닝**: 최근 5일간 여러 번 등장한 업무 유형/고객/카테고리
6. **긴급도가 높은 업무 우선**: 
   - 고객 상담 관련 업무 (특히 진행 중인 고객)
   - 계약/보장 관련 업무
   - 마감이 임박한 업무
7. **우선순위가 높은 카테고리**: "고객 상담" > "계약 처리" > "내부 업무" > 기타
8. **오늘 배치 가능한 업무**: 구체적이고 실행 가능한 업무만 플래닝
9. 최근 업무 패턴이 부족할 때만 일반적인 업무 추가:
   - 고객 연락 및 상담
   - 기존 고객 관리 및 계약 검토
   - 신규 고객 발굴 및 상담 준비
   - 상품 정보 학습 및 업데이트 확인
   - 보고서 작성 및 문서 정리
10. 우선순위: high(긴급/중요), medium(보통), low(여유)
11. 예상 시간: "30분", "1시간", "2시간" 등
12. 카테고리: "고객 상담", "계약 처리", "문서 작업", "학습", "네트워킹", "기획", "기타" 등

**중요**: 
- **익일 업무 계획이 최우선**이며, 반드시 포함해야 함 (절대 빼먹으면 안 됨!)
- 제공된 최근 5일 업무 패턴은 이미 완료 여부가 필터링되어 있음 (다음날 완료된 업무는 제외됨)
- 미완료, 반복, 긴급도, 우선순위 카테고리, 배치 가능성을 기준으로 플래닝
- 일반적인 업무보다 구체적이고 개인화된 업무를 우선 플래닝

반드시 다음 JSON 형식으로만 응답:
{
  "tasks": [
    {
      "title": "작업 제목",
      "description": "작업 설명",
      "priority": "high|medium|low",
      "expected_time": "예상 시간",
      "category": "카테고리"
    }
  ],
  "summary": "오늘 일정 전체 요약 (1-2문장)"
}

중요: tasks 배열에는 최소 3개 이상의 작업이 포함되어야 한다.
"""
    
    def __init__(
        self,
        retriever_tool: YesterdayReportTool,
        llm_client: LLMClient,
        vector_retriever: Optional[UnifiedRetriever] = None
    ):
        """
        초기화
        
        Args:
            retriever_tool: 전날 보고서 검색 도구 (PostgreSQL)
            llm_client: LLM 클라이언트
            vector_retriever: VectorDB 검색기 (과거 업무 패턴 검색용, 선택적)
        """
        self.retriever_tool = retriever_tool
        self.llm_client = llm_client
        self.vector_retriever = vector_retriever
    
    async def generate(
        self,
        request: TodayPlanRequest
    ) -> TodayPlanResponse:
        """
        오늘의 일정 플래닝
        
        Args:
            request: 일정 생성 요청
            
        Returns:
            생성된 일정
        """
        # Step 1: 전날 보고서 가져오기
        yesterday_data = self.retriever_tool.get_yesterday_report(
            owner=request.owner,
            target_date=request.target_date
        )
        
        unresolved = yesterday_data["unresolved"]
        next_day_plan = yesterday_data["next_day_plan"]
        tasks = yesterday_data.get("tasks", [])
        found = yesterday_data["found"]
        
        print(f"[DEBUG] TodayPlanGenerator.generate (async): found={found}, unresolved={len(unresolved)}, next_day_plan={len(next_day_plan)}, tasks={len(tasks)}, search_date={yesterday_data.get('search_date')}")
        
        # Step 2: VectorDB에서 최근 업무 패턴 검색
        # 익일 업무 계획이 3개 이상이면 VectorDB 검색 건너뛰기 (익일 계획이 최우선)
        similar_tasks: List[UnifiedSearchResult] = []
        
        # 익일 업무 계획이 3개 미만일 때만 VectorDB 검색 수행
        should_search_vector = len(next_day_plan) < 3
        
        if should_search_vector and self.vector_retriever:
            try:
                from datetime import timedelta
                
                today = request.target_date
                period_end = today - timedelta(days=1)  # 어제까지
                
                # 날짜 필터 없이 검색 (owner만 필터링)
                # 결과를 날짜 기준으로 필터링하고 정렬하여 최신 데이터 우선 사용
                print(f"[INFO] 최근 업무 패턴 검색 (날짜 필터 없이, 검색 후 필터링)")
                
                # 다양한 검색 쿼리
                search_queries = [
                    f"{request.owner} 최근 업무",
                    f"{request.owner} 상담 고객",
                    f"{request.owner} 계약 처리",
                    f"{request.owner} 업무 진행",
                ]
                
                all_results = []
                
                for query in search_queries:
                    # 날짜 필터 없이 검색 (더 많은 결과 확보)
                    results = self.vector_retriever.search_daily(
                        query=query,
                        owner=request.owner,
                        n_results=20,  # 날짜 필터 없이 더 많은 결과 가져오기
                        chunk_types=["detail", "summary"]
                    )
                    all_results.extend(results)
                
                print(f"[INFO] 초기 검색 결과: {len(all_results)}개 발견")
                
                # 날짜 기준으로 필터링 및 정렬 (최신순)
                # 최근 30일 이내 데이터만 선택
                max_date = period_end
                min_date = max_date - timedelta(days=30)
                min_date_str = min_date.isoformat()
                max_date_str = max_date.isoformat()
                
                filtered_results = []
                for result in all_results:
                    result_date_str = result.metadata.get("date", "")
                    # 날짜 필터링: 최근 30일 이내만
                    if result_date_str and min_date_str <= result_date_str <= max_date_str:
                        filtered_results.append(result)
                
                print(f"[INFO] 날짜 필터링 후 ({min_date_str} ~ {max_date_str}): {len(filtered_results)}개")
                
                # 완료된 업무 필터링: 다음날에 완료된 업무는 제외
                from datetime import datetime
                incomplete_results = []
                for result in filtered_results:
                    result_date_str = result.metadata.get("date", "")
                    if not result_date_str:
                        incomplete_results.append(result)
                        continue
                    
                    try:
                        result_date = datetime.strptime(result_date_str, "%Y-%m-%d").date()
                        next_day = result_date + timedelta(days=1)
                        
                        # 다음날 업무 검색 (완료 여부 확인)
                        task_text = result.text
                        # 청크 타입이 detail인 경우 실제 업무 내용 추출
                        if "[일일_DETAIL]" in task_text:
                            # 시간 범위 제거하고 업무 내용만 추출
                            lines = task_text.split('\n')
                            task_content = " ".join([line.strip() for line in lines[1:] if line.strip()])
                        else:
                            task_content = task_text
                        
                        # 다음날 같은 업무가 있는지 확인
                        next_day_tasks = self.vector_retriever.search_daily(
                            query=task_content[:100],  # 업무 내용으로 검색
                            owner=request.owner,
                            single_date=next_day.isoformat(),
                            n_results=5,
                            chunk_types=["detail"]
                        )
                        
                        # 유사도가 높은 업무가 있으면 완료된 것으로 간주
                        is_completed = False
                        for next_task in next_day_tasks:
                            # 유사한 업무가 있으면 완료된 것으로 간주
                            if next_task.score > 0.7:  # 유사도 임계값
                                is_completed = True
                                break
                        
                        if not is_completed:
                            incomplete_results.append(result)
                    except Exception as e:
                        # 날짜 파싱 실패 시 포함
                        print(f"[WARNING] 날짜 파싱 실패 ({result_date_str}): {e}")
                        incomplete_results.append(result)
                
                print(f"[INFO] 완료된 업무 필터링 후: {len(incomplete_results)}개 (제외: {len(filtered_results) - len(incomplete_results)}개)")
                
                # 날짜 기준으로 정렬 (최신순)
                incomplete_results.sort(key=lambda x: (
                    x.metadata.get("date", ""),  # 날짜 기준 (최신순)
                    -x.score  # 동일 날짜면 유사도 높은 순
                ), reverse=True)
                
                # 중복 제거 및 최신 데이터 우선 선택
                seen_tasks = set()
                diverse_tasks = []
                
                for result in incomplete_results:
                    # 텍스트의 핵심 부분으로 중복 체크
                    text_key = result.text[:50].strip()
                    if text_key and text_key not in seen_tasks:
                        diverse_tasks.append(result)
                        seen_tasks.add(text_key)
                    
                    # 최대 15개까지만
                    if len(diverse_tasks) >= 15:
                        break
                
                similar_tasks = diverse_tasks
                
                # 결과 요약 출력
                if similar_tasks:
                    dates_found = sorted(set(r.metadata.get("date", "") for r in similar_tasks if r.metadata.get("date")), reverse=True)
                    oldest_date = dates_found[-1] if dates_found else "N/A"
                    newest_date = dates_found[0] if dates_found else "N/A"
                    
                    print(f"[INFO] 최근 업무 패턴 검색 완료:")
                    print(f"  ├─ 총 {len(similar_tasks)}개 업무 발견")
                    print(f"  ├─ 날짜 범위: {oldest_date} ~ {newest_date}")
                    print(f"  └─ 검색된 업무 예시 (최신순):")
                    for idx, task in enumerate(similar_tasks[:5], 1):
                        task_date = task.metadata.get("date", "N/A")
                        print(f"      [{idx}] {task_date}: {task.text[:60]}...")
                else:
                    print(f"[WARNING] 업무 패턴 검색 결과 없음 (필터링 범위: {min_date_str} ~ {max_date_str})")
                    
            except Exception as e:
                print(f"[WARNING] VectorDB 검색 실패: {e}")
                import traceback
                traceback.print_exc()
                similar_tasks = []
        else:
            if not should_search_vector:
                print(f"[INFO] 익일 업무 계획이 {len(next_day_plan)}개로 충분하여 VectorDB 검색 건너뜀 (익일 계획 최우선)")
            elif not self.vector_retriever:
                print(f"[WARNING] VectorDB 검색기 없음 - 최근 업무 패턴 검색 불가")
        
        # Step 3: LLM 프롬프트 구성
        user_prompt = self._build_user_prompt(
            today=request.target_date,
            owner=request.owner,
            unresolved=unresolved,
            next_day_plan=next_day_plan,
            similar_tasks=similar_tasks
        )
        
        # Step 4: LLM 호출 (JSON 응답)
        llm_response = await self.llm_client.acomplete_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # Step 4: 응답 파싱 및 검증
        tasks = []
        for task_dict in llm_response.get("tasks", []):
            try:
                task = TaskItem(**task_dict)
                tasks.append(task)
            except Exception as e:
                print(f"[WARNING] Task parsing error: {e}")
                continue
        
        # 최소 3개 보장 (fallback)
        if len(tasks) < 3:
            print(f"[WARNING] LLM이 {len(tasks)}개만 생성 - 기본 업무 추가")
            
            # 부족한 개수만큼 기본 업무 추가
            default_tasks = [
                TaskItem(
                    title="기존 고객 관리 및 연락",
                    description="기존 고객들에게 연락하여 현황 확인 및 관계 유지",
                    priority="medium",
                    expected_time="1시간",
                    category="고객 상담"
                ),
                TaskItem(
                    title="고객 발굴 활동",
                    description="고객 명단 검토 및 상담 준비",
                    priority="medium",
                    expected_time="1시간",
                    category="영업"
                ),
                TaskItem(
                    title="상품 정보 학습 및 업데이트",
                    description="최신 상품 정보 확인 및 학습",
                    priority="low",
                    expected_time="30분",
                    category="학습"
                )
            ]
            
            # 부족한 만큼 추가
            needed = 3 - len(tasks)
            tasks.extend(default_tasks[:needed])
        
        summary = llm_response.get("summary", "오늘의 일정 플래닝입니다.")
        
        return TodayPlanResponse(
            tasks=tasks,
            summary=summary,
            source_date=yesterday_data["search_date"],
            owner=request.owner
        )
    
    def generate_sync(
        self,
        request: TodayPlanRequest
    ) -> TodayPlanResponse:
        """
        동기 버전: 오늘의 일정 플래닝
        
        Args:
            request: 일정 생성 요청
            
        Returns:
            생성된 일정
        """
        # Step 1: 전날 보고서 가져오기
        yesterday_data = self.retriever_tool.get_yesterday_report(
            owner=request.owner,
            target_date=request.target_date
        )
        
        unresolved = yesterday_data["unresolved"]
        next_day_plan = yesterday_data["next_day_plan"]
        tasks = yesterday_data.get("tasks", [])
        found = yesterday_data["found"]
        
        print(f"[DEBUG] TodayPlanGenerator.generate_sync: found={found}, unresolved={len(unresolved)}, next_day_plan={len(next_day_plan)}, tasks={len(tasks)}, search_date={yesterday_data.get('search_date')}")
        
        # Step 2: VectorDB에서 최근 업무 패턴 검색
        # 익일 업무 계획이 3개 이상이면 VectorDB 검색 건너뛰기 (익일 계획이 최우선)
        similar_tasks: List[UnifiedSearchResult] = []
        
        # 익일 업무 계획이 3개 미만일 때만 VectorDB 검색 수행
        should_search_vector = len(next_day_plan) < 3
        
        if should_search_vector and self.vector_retriever:
            try:
                from datetime import timedelta
                
                today = request.target_date
                period_end = today - timedelta(days=1)  # 어제까지
                
                # 날짜 필터 없이 검색 (owner만 필터링)
                # 결과를 날짜 기준으로 필터링하고 정렬하여 최신 데이터 우선 사용
                print(f"[INFO] 최근 업무 패턴 검색 (날짜 필터 없이, 검색 후 필터링)")
                
                # 다양한 검색 쿼리
                search_queries = [
                    f"{request.owner} 최근 업무",
                    f"{request.owner} 상담 고객",
                    f"{request.owner} 계약 처리",
                    f"{request.owner} 업무 진행",
                ]
                
                all_results = []
                for query in search_queries:
                    # 날짜 필터 없이 검색 (더 많은 결과 확보)
                    results = self.vector_retriever.search_daily(
                        query=query,
                        owner=request.owner,
                        n_results=20,  # 날짜 필터 없이 더 많은 결과 가져오기
                        chunk_types=["detail", "summary"]
                    )
                    all_results.extend(results)
                
                print(f"[INFO] 초기 검색 결과: {len(all_results)}개 발견")
                
                # 날짜 기준으로 필터링 및 정렬 (최신순)
                # 최근 30일 이내 데이터만 선택
                max_date = period_end
                min_date = max_date - timedelta(days=30)
                min_date_str = min_date.isoformat()
                max_date_str = max_date.isoformat()
                
                filtered_results = []
                for result in all_results:
                    result_date_str = result.metadata.get("date", "")
                    # 날짜 필터링: 최근 30일 이내만
                    if result_date_str and min_date_str <= result_date_str <= max_date_str:
                        filtered_results.append(result)
                
                print(f"[INFO] 날짜 필터링 후 ({min_date_str} ~ {max_date_str}): {len(filtered_results)}개")
                
                # 완료된 업무 필터링: 다음날에 완료된 업무는 제외
                from datetime import datetime
                incomplete_results = []
                for result in filtered_results:
                    result_date_str = result.metadata.get("date", "")
                    if not result_date_str:
                        incomplete_results.append(result)
                        continue
                    
                    try:
                        result_date = datetime.strptime(result_date_str, "%Y-%m-%d").date()
                        next_day = result_date + timedelta(days=1)
                        
                        # 다음날 업무 검색 (완료 여부 확인)
                        task_text = result.text
                        # 청크 타입이 detail인 경우 실제 업무 내용 추출
                        if "[일일_DETAIL]" in task_text:
                            # 시간 범위 제거하고 업무 내용만 추출
                            lines = task_text.split('\n')
                            task_content = " ".join([line.strip() for line in lines[1:] if line.strip()])
                        else:
                            task_content = task_text
                        
                        # 다음날 같은 업무가 있는지 확인
                        next_day_tasks = self.vector_retriever.search_daily(
                            query=task_content[:100],  # 업무 내용으로 검색
                            owner=request.owner,
                            single_date=next_day.isoformat(),
                            n_results=5,
                            chunk_types=["detail"]
                        )
                        
                        # 유사도가 높은 업무가 있으면 완료된 것으로 간주
                        is_completed = False
                        for next_task in next_day_tasks:
                            # 유사한 업무가 있으면 완료된 것으로 간주
                            if next_task.score > 0.7:  # 유사도 임계값
                                is_completed = True
                                break
                        
                        if not is_completed:
                            incomplete_results.append(result)
                    except Exception as e:
                        # 날짜 파싱 실패 시 포함
                        print(f"[WARNING] 날짜 파싱 실패 ({result_date_str}): {e}")
                        incomplete_results.append(result)
                
                print(f"[INFO] 완료된 업무 필터링 후: {len(incomplete_results)}개 (제외: {len(filtered_results) - len(incomplete_results)}개)")
                
                # 날짜 기준으로 정렬 (최신순)
                incomplete_results.sort(key=lambda x: (
                    x.metadata.get("date", ""),  # 날짜 기준 (최신순)
                    -x.score  # 동일 날짜면 유사도 높은 순
                ), reverse=True)
                
                # 중복 제거 및 최신 데이터 우선 선택
                seen_tasks = set()
                diverse_tasks = []
                
                for result in incomplete_results:
                    # 텍스트의 핵심 부분으로 중복 체크
                    text_key = result.text[:50].strip()
                    if text_key and text_key not in seen_tasks:
                        diverse_tasks.append(result)
                        seen_tasks.add(text_key)
                    
                    # 최대 20개까지만
                    if len(diverse_tasks) >= 20:
                        break
                
                similar_tasks = diverse_tasks
                
                # 결과 요약 출력
                if similar_tasks:
                    dates_found = sorted(set(r.metadata.get("date", "") for r in similar_tasks if r.metadata.get("date")), reverse=True)
                    oldest_date = dates_found[-1] if dates_found else "N/A"
                    newest_date = dates_found[0] if dates_found else "N/A"
                    
                    print(f"[INFO] 최근 업무 패턴 검색 완료:")
                    print(f"  ├─ 총 {len(similar_tasks)}개 업무 발견")
                    print(f"  ├─ 날짜 범위: {oldest_date} ~ {newest_date}")
                    print(f"  └─ 검색된 업무 예시 (최신순):")
                    for idx, task in enumerate(similar_tasks[:5], 1):
                        task_date = task.metadata.get("date", "N/A")
                        print(f"      [{idx}] {task_date}: {task.text[:60]}...")
                else:
                    print(f"[WARNING] 업무 패턴 검색 결과 없음 (필터링 범위: {min_date_str} ~ {max_date_str})")
                    
            except Exception as e:
                print(f"[WARNING] VectorDB 검색 실패: {e}")
                import traceback
                traceback.print_exc()
                similar_tasks = []
        else:
            if not should_search_vector:
                print(f"[INFO] 익일 업무 계획이 {len(next_day_plan)}개로 충분하여 VectorDB 검색 건너뜀 (익일 계획 최우선)")
            elif not self.vector_retriever:
                print(f"[WARNING] VectorDB 검색기 없음 - 최근 업무 패턴 검색 불가")
        
        # Step 3: LLM 프롬프트 구성
        user_prompt = self._build_user_prompt(
            today=request.target_date,
            owner=request.owner,
            unresolved=unresolved,
            next_day_plan=next_day_plan,
            tasks=tasks,
            similar_tasks=similar_tasks
        )
        
        # Step 4: LLM 호출 (JSON 응답) - 동기
        llm_response = self.llm_client.complete_json(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.7,
            max_tokens=1500
        )
        
        # Step 5: 응답 파싱 및 검증
        tasks = []
        for task_dict in llm_response.get("tasks", []):
            try:
                task = TaskItem(**task_dict)
                tasks.append(task)
            except Exception as e:
                print(f"[WARNING] Task parsing error: {e}")
                continue
        
        # 최소 3개 보장 (fallback)
        if len(tasks) < 3:
            print(f"[WARNING] LLM이 {len(tasks)}개만 생성 - 기본 업무 추가")
            
            # 부족한 개수만큼 기본 업무 추가
            default_tasks = [
                TaskItem(
                    title="기존 고객 관리 및 연락",
                    description="기존 고객들에게 연락하여 현황 확인 및 관계 유지",
                    priority="medium",
                    expected_time="1시간",
                    category="고객 상담"
                ),
                TaskItem(
                    title="고객 발굴 활동",
                    description="고객 명단 검토 및 상담 준비",
                    priority="medium",
                    expected_time="1시간",
                    category="영업"
                ),
                TaskItem(
                    title="상품 정보 학습 및 업데이트",
                    description="최신 상품 정보 확인 및 학습",
                    priority="low",
                    expected_time="30분",
                    category="학습"
                )
            ]
            
            # 부족한 만큼 추가
            needed = 3 - len(tasks)
            tasks.extend(default_tasks[:needed])
        
        summary = llm_response.get("summary", "오늘의 일정 플래닝입니다.")
        
        return TodayPlanResponse(
            tasks=tasks,
            summary=summary,
            source_date=yesterday_data["search_date"],
            owner=request.owner
        )
    
    def _build_user_prompt(
        self,
        today: date,
        owner: str,
        unresolved: list,
        next_day_plan: list,
        tasks: list = None,
        similar_tasks: List[UnifiedSearchResult] = None
    ) -> str:
        """
        사용자 프롬프트 구성
        
        Args:
            today: 오늘 날짜
            owner: 작성자
            unresolved: 미종결 업무 목록 (PostgreSQL에서)
            next_day_plan: 익일 계획 목록 (PostgreSQL에서)
            tasks: 전날 수행한 작업 목록 (PostgreSQL에서)
            similar_tasks: 유사 업무 패턴 (VectorDB에서, 선택적)
            
        Returns:
            구성된 프롬프트
        """
        # 미종결 업무 포맷팅
        unresolved_text = "\n".join([f"- {item}" for item in unresolved]) if unresolved else "없음"
        
        # 익일 계획 포맷팅
        next_day_plan_text = "\n".join([f"- {item}" for item in next_day_plan]) if next_day_plan else "없음"
        
        # 전날 작업 포맷팅
        tasks_text = "\n".join([f"- {item}" for item in (tasks or [])]) if tasks else "없음"
        
        # 🔥 VectorDB에서 가져온 최근 5일 업무 패턴 포맷팅
        similar_tasks_text = "없음"
        if similar_tasks:
            # 디버그: 가져온 청크 타입 확인
            print(f"[DEBUG] 최근 5일 업무 패턴 검색 결과: 총 {len(similar_tasks)}개")
            for idx, result in enumerate(similar_tasks[:10]):
                task_date = result.metadata.get("date", "N/A")
                print(f"  [{idx+1}] 날짜={task_date}, chunk_type={result.chunk_type}, score={result.score:.3f}, text={result.text[:50]}...")
            
            # 최근 업무 패턴 추출 (detail과 summary만 포함)
            task_patterns = []
            for result in similar_tasks[:15]:  # 상위 15개 (더 많은 패턴 제공)
                chunk_type = result.chunk_type
                task_date = result.metadata.get("date", "N/A")
                # 새로운 4청크 구조: detail(세부 업무), summary(요약)만 사용
                if chunk_type in ["detail", "summary"]:
                    # 날짜 정보와 함께 표시하여 최근 패턴임을 명확히
                    task_patterns.append(f"- [{task_date}] {result.text}")
            
            print(f"[DEBUG] 최근 5일 업무 패턴 필터링 결과: {len(task_patterns)}개")
            
            if task_patterns:
                similar_tasks_text = "\n".join(task_patterns)
                print(f"[INFO] 최근 5일 업무 패턴을 LLM에 제공: {len(task_patterns)}개")
        
        prompt = f"""날짜: {today.isoformat()}
작성자: {owner}

【전날 수행한 작업】 (PostgreSQL)
{tasks_text}

【전날 익일 업무 계획】 (PostgreSQL) - **최우선 포함 대상 (절대 빼먹으면 안 됨!)**
{next_day_plan_text}

【전날 미종결 업무】 (PostgreSQL) - **2순위 포함 대상**
{unresolved_text}

【최근 5일 미완료 업무 패턴】 (VectorDB - 다음날 완료된 업무는 제외됨) - **3순위**
{similar_tasks_text}

위 정보를 바탕으로 오늘 하루 일정 플래닝을 JSON 형식으로 생성해주세요.

**플래닝 기준 (우선순위 순)**:
1. **익일 업무 계획 최우선**: 전날 작성한 익일 업무 계획을 반드시 포함 (절대 빼먹으면 안 됨!)
2. **미종결 업무**: 전날 미종결 업무가 있으면 2순위로 포함
3. **반복 업무**: 최근 5일간 여러 번 등장한 업무 유형/고객/카테고리 우선 플래닝
4. **긴급도가 높은 업무**: 
   - 고객 상담 관련 업무 (특히 진행 중인 고객)
   - 계약/보장 관련 업무
   - 마감이 임박한 업무
5. **우선순위가 높은 카테고리**: "고객 상담" > "계약 처리" > "내부 업무" > 기타
6. **오늘 배치 가능한 업무**: 구체적이고 실행 가능한 업무만 플래닝

**요구사항**:
1. **최소 3개 이상의 업무를 반드시 포함** (매우 중요!)
2. **익일 업무 계획이 최우선**: 전날 작성한 익일 업무 계획을 반드시 포함 (절대 빼먹으면 안 됨!)
3. **미완료 업무만 플래닝**: 제공된 최근 5일 업무 패턴은 이미 다음날 완료된 업무가 제외되어 있음
4. 전날 미종결 업무가 있으면 2순위로 포함
5. **반복 업무 분석**: 최근 5일 업무 패턴에서 여러 번 등장한 업무 유형, 고객 이름, 카테고리 등을 우선 플래닝
6. **긴급도 판단**: 고객 상담, 계약 처리 등 긴급도가 높은 업무 우선
7. **카테고리 우선순위**: "고객 상담" > "계약 처리" > "내부 업무" 순서로 우선순위 부여
8. 각 업무는 실행 가능하고 구체적이어야 함
9. 최근 업무 패턴이 부족할 때만 일반적인 업무 추가

**중요**: 
- **익일 업무 계획이 최우선**이며, 반드시 포함해야 함 (절대 빼먹으면 안 됨!)
- 제공된 최근 5일 업무 패턴은 미완료 업무만 포함되어 있음 (다음날 완료된 업무는 제외)
- 미완료, 반복, 긴급도, 우선순위 카테고리, 배치 가능성을 기준으로 플래닝
- 업무가 3개 미만이면 안 됩니다. 반드시 3개 이상 생성하세요.
"""
        
        return prompt

