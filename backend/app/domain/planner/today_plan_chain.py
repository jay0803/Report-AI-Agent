"""
Today Plan Chain

LangChain 기반 오늘의 추천 일정 생성 체인

Author: AI Assistant
Created: 2025-11-18
"""
from typing import Optional, List
from datetime import date

from app.llm.client import LLMClient
from app.domain.planner.tools import YesterdayReportTool
from app.domain.search.retriever import UnifiedRetriever, UnifiedSearchResult
from app.domain.planner.schemas import (
    TodayPlanRequest,
    TodayPlanResponse,
    TaskItem
)


class TodayPlanGenerator:
    """오늘의 추천 일정 생성기"""
    
    SYSTEM_PROMPT = """너는 AI 업무 플래너이다.

전날의 미종결 업무(unresolved)와 익일 계획(next_day_plan)을 우선 참고하고,
**최근 5일 업무 패턴(similar_tasks)을 적극 활용**하여 사용자 맞춤형 업무를 추천해야 한다.

규칙:
1. **최소 3개 이상의 추천 업무를 반드시 생성** (매우 중요!)
2. 미종결 업무가 있으면 우선순위를 높게 설정하고 반드시 포함
3. 익일 계획을 바탕으로 구체적인 작업 생성
4. **최근 5일 업무 패턴을 우선적으로 활용** - 사용자가 최근에 수행한 실제 업무를 기반으로 추천
5. 최근 업무 패턴이 있으면 그것을 바탕으로 구체적이고 맞춤형 업무 생성
6. 최근 업무 패턴이 부족할 때만 일반적인 업무를 추가:
   - 고객 연락 및 상담
   - 기존 고객 관리 및 계약 검토
   - 신규 고객 발굴 및 상담 준비
   - 상품 정보 학습 및 업데이트 확인
   - 보고서 작성 및 문서 정리
   - 네트워킹 및 관계 유지
7. 각 작업은 실행 가능하고 명확해야 함
8. 우선순위: high(긴급/중요), medium(보통), low(여유)
9. 예상 시간: "30분", "1시간", "2시간" 등
10. 카테고리: "고객 상담", "계약 처리", "문서 작업", "학습", "네트워킹", "기획", "기타" 등

**중요**: 최근 5일 업무 패턴이 제공되면, 반드시 그것을 우선적으로 활용하여 사용자 맞춤형 업무를 생성해야 한다.
일반적인 업무만 추천하지 말고, 최근 업무 패턴을 분석하여 구체적이고 개인화된 업무를 추천해야 한다.

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
        오늘의 추천 일정 생성
        
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
        
        # Step 2: VectorDB에서 유사 업무 패턴 검색
        # 조건: 전날 데이터가 없거나, 미종결+익일계획이 3개 미만일 때
        similar_tasks: List[UnifiedSearchResult] = []
        total_from_yesterday = len(unresolved) + len(next_day_plan)
        should_search_vector = (not found) or (total_from_yesterday < 3)
        
        if self.vector_retriever and should_search_vector:
            try:
                # 다양한 카테고리의 검색 쿼리 (다양성 확보)
                search_queries = [
                    f"{request.owner} 고객 상담 통화 연락",
                    f"{request.owner} 제안서 플랜",
                    f"{request.owner} 고객 발굴",
                    f"{request.owner} 계약 관리",
                ]
                
                all_results = []
                for query in search_queries:
                    results = self.vector_retriever.search_daily(
                        query=query,
                        owner=request.owner,
                        n_results=5,  # 각 쿼리당 5개
                        chunk_types=["detail_chunk"]  # detail_chunk 타입 청크만 검색
                    )
                    all_results.extend(results)
                
                # 중복 제거 (비슷한 업무는 하나만)
                seen_tasks = set()
                diverse_tasks = []
                
                for result in all_results:
                    text_key = result.text[:30]  # 앞 30자로 중복 체크
                    if text_key not in seen_tasks:
                        diverse_tasks.append(result)
                        seen_tasks.add(text_key)
                
                similar_tasks = diverse_tasks[:15]  # 최대 15개
                
                print(f"[INFO] VectorDB 검색 완료: {len(similar_tasks)}개 유사 업무 패턴 발견 (다양성 확보, 조건: found={found}, total_from_yesterday={total_from_yesterday})")
            except Exception as e:
                print(f"[WARNING] VectorDB 검색 실패: {e}")
                similar_tasks = []
        else:
            print(f"[INFO] VectorDB 검색 건너뜀 (충분한 전날 데이터: {total_from_yesterday}개)")
        
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
        
        summary = llm_response.get("summary", "오늘의 추천 일정입니다.")
        
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
        동기 버전: 오늘의 추천 일정 생성
        
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
        
        # Step 2: VectorDB에서 최근 5일 업무 패턴 검색 (항상 수행)
        # 최근 5일 데이터를 기반으로 사용자 맞춤형 업무 추천
        similar_tasks: List[UnifiedSearchResult] = []
        total_from_yesterday = len(unresolved) + len(next_day_plan)
        
        if self.vector_retriever:
            try:
                from datetime import timedelta
                
                # 최근 5일 날짜 범위 계산
                today = request.target_date
                period_end = today - timedelta(days=1)  # 어제까지
                period_start = period_end - timedelta(days=4)  # 5일 전부터
                
                print(f"[INFO] 최근 5일 업무 패턴 검색: {period_start} ~ {period_end}")
                
                # 최근 5일 데이터에서 실제 업무 패턴 검색
                # 다양한 검색 쿼리로 최근 업무 패턴 추출
                search_queries = [
                    f"{request.owner} 최근 업무",
                    f"{request.owner} 상담 고객",
                    f"{request.owner} 계약 처리",
                    f"{request.owner} 업무 진행",
                ]
                
                all_results = []
                for query in search_queries:
                    results = self.vector_retriever.search_daily(
                        query=query,
                        owner=request.owner,
                        period_start=period_start.isoformat(),
                        period_end=period_end.isoformat(),
                        n_results=10,  # 각 쿼리당 10개 (최근 데이터 우선)
                        chunk_types=["detail_chunk", "summary_task_chunk"]  # 실제 업무 내용 포함
                    )
                    all_results.extend(results)
                
                # 중복 제거 및 최근 데이터 우선 정렬
                seen_tasks = set()
                diverse_tasks = []
                
                # 날짜 기준으로 정렬 (최신순)
                all_results.sort(key=lambda x: x.metadata.get("date", "") or x.metadata.get("period_start", ""), reverse=True)
                
                for result in all_results:
                    # 텍스트의 핵심 부분으로 중복 체크 (더 정확하게)
                    text_key = result.text[:50].strip()  # 앞 50자로 중복 체크
                    if text_key and text_key not in seen_tasks:
                        diverse_tasks.append(result)
                        seen_tasks.add(text_key)
                
                # 최근 5일 데이터에서 최대 20개 추출
                similar_tasks = diverse_tasks[:20]
                
                print(f"[INFO] 최근 5일 업무 패턴 검색 완료: {len(similar_tasks)}개 발견 (기간: {period_start} ~ {period_end})")
                if similar_tasks:
                    print(f"[INFO] 검색된 업무 예시:")
                    for idx, task in enumerate(similar_tasks[:5], 1):
                        task_date = task.metadata.get("date", task.metadata.get("period_start", "N/A"))
                        print(f"  [{idx}] {task_date}: {task.text[:60]}...")
            except Exception as e:
                print(f"[WARNING] VectorDB 검색 실패: {e}")
                import traceback
                traceback.print_exc()
                similar_tasks = []
        else:
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
        
        summary = llm_response.get("summary", "오늘의 추천 일정입니다.")
        
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
                task_date = result.metadata.get("date", result.metadata.get("period_start", "N/A"))
                print(f"  [{idx+1}] 날짜={task_date}, chunk_type={result.chunk_type}, score={result.score:.3f}, text={result.text[:50]}...")
            
            # 최근 업무 패턴 추출 (detail_chunk와 summary_task_chunk 모두 포함)
            task_patterns = []
            for result in similar_tasks[:15]:  # 상위 15개 (더 많은 패턴 제공)
                chunk_type = result.chunk_type
                task_date = result.metadata.get("date", result.metadata.get("period_start", "N/A"))
                if chunk_type in ["detail_chunk", "summary_task_chunk"]:
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

【전날 미종결 업무】 (PostgreSQL)
{unresolved_text}

【전날 익일 계획】 (PostgreSQL)
{next_day_plan_text}

【최근 5일 업무 패턴】 (VectorDB - 사용자 맞춤형 추천의 핵심 데이터)
{similar_tasks_text}

위 정보를 바탕으로 오늘 하루 추천 일정을 JSON 형식으로 생성해주세요.

**요구사항**:
1. **최소 3개 이상의 업무를 반드시 포함** (매우 중요!)
2. 전날 미종결 업무가 있으면 우선적으로 포함
3. **최근 5일 업무 패턴을 적극 활용** - 사용자가 최근에 수행한 실제 업무를 분석하여 맞춤형 업무 추천
4. 최근 업무 패턴에서 반복되는 업무 유형, 고객 이름, 상담 내용 등을 참고하여 구체적인 업무 생성
5. 최근 업무 패턴이 부족할 때만 일반적인 업무를 추가
6. 전날 수행한 작업의 연속성과 익일 계획을 고려
7. 각 업무는 실행 가능하고 구체적이어야 함
8. **일반적인 업무("고객 연락 및 상담", "신규 고객 발굴" 등)만 추천하지 말고, 최근 5일 패턴을 기반으로 구체적이고 개인화된 업무를 추천해야 함**

**중요**: 최근 5일 업무 패턴이 제공되면, 반드시 그것을 우선적으로 활용하여 사용자 맞춤형 업무를 생성해야 합니다.
업무가 3개 미만이면 안 됩니다. 반드시 3개 이상 생성하세요.
"""
        
        return prompt

