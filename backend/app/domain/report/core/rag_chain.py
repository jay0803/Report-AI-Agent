"""
RAG Chain for Daily Report Chatbot

일일보고서 데이터를 기반으로 한 RAG 챗봇 체인
LangChain 스타일로 구성
"""
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
import re

from app.infrastructure.vector_store_advanced import get_vector_store
from app.domain.report.search.retriever import UnifiedRetriever, UnifiedSearchResult
from app.llm.client import LLMClient


class ReportRAGChain:
    """일일보고서 RAG 체인"""
    
    def __init__(
        self,
        owner: str,
        retriever: Optional[UnifiedRetriever] = None,
        llm: Optional[LLMClient] = None,
        top_k: int = 5
    ):
        """
        초기화
        
        Args:
            owner: 작성자 이름
            retriever: UnifiedRetriever 인스턴스 (None이면 자동 생성)
            llm: LLMClient 인스턴스 (None이면 자동 생성)
            top_k: 검색 결과 개수 (기본값: 5)
        """
        self.owner = owner
        self.top_k = top_k
        
        # Retriever 초기화
        if retriever is None:
            # daily_reports_advanced 컬렉션 사용
            import os
            vector_store = get_vector_store()
            collection = vector_store.get_collection()
            embedding_model_type = os.getenv("REPORT_EMBEDDING_MODEL_TYPE", "hf")
            self.retriever = UnifiedRetriever(
                collection=collection,
                embedding_model_type=embedding_model_type
            )
        else:
            self.retriever = retriever
        
        # LLM 초기화
        if llm is None:
            self.llm = LLMClient(
                model="gpt-4o-mini",
                temperature=0.7,
                max_tokens=2000
            )
        else:
            self.llm = llm
    
    def _is_unresolved_task_query(self, query: str) -> bool:
        """
        미종결 업무 관련 질의인지 판단
        
        Args:
            query: 사용자 질문
            
        Returns:
            미종결 업무 질의 여부
        """
        query_lower = query.lower()
        unresolved_keywords = ["미종결", "미완료", "처리 못한", "안 한", "안한", "안 끝난", "안끝난"]
        return any(keyword in query_lower for keyword in unresolved_keywords)
    
    def _parse_date_from_metadata(self, metadata: Dict[str, Any]) -> Optional[date]:
        """
        메타데이터에서 날짜 파싱 (새로운 4청크 구조: date 필드만 사용)
        
        Args:
            metadata: 청크 메타데이터
            
        Returns:
            파싱된 date 객체 또는 None
        """
        date_str = metadata.get("date")
        if not date_str:
            return None
        
        try:
            # YYYY-MM-DD 형식 파싱
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None
    
    def _filter_completed_unresolved_tasks(
        self,
        issue_results: List[UnifiedSearchResult]
    ) -> List[UnifiedSearchResult]:
        """
        미종결 업무 중 다음 날 실제로 수행된 항목 제외
        
        Args:
            issue_results: 미종결 업무 검색 결과
            
        Returns:
            필터링된 결과 (진행되지 않은 미종결 업무만)
        """
        if not issue_results:
            return []
        
        filtered_results = []
        
        for issue_result in issue_results:
            issue_date = self._parse_date_from_metadata(issue_result.metadata)
            if not issue_date:
                # 날짜 정보 없으면 포함
                filtered_results.append(issue_result)
                continue
            
            # 다음 날 날짜 계산
            next_day = issue_date + timedelta(days=1)
            
            # 다음 날의 task 검색 (같은 업무가 수행되었는지 확인)
            next_day_tasks = self.retriever.search_daily(
                query=issue_result.text,  # 미종결 업무 텍스트로 검색
                owner=self.owner,
                single_date=next_day.strftime("%Y-%m-%d"),
                n_results=10,
                chunk_types=["detail"]  # detail 타입만 (새로운 4청크 구조)
            )
            
            # 유사도가 높은 task가 있으면 수행된 것으로 간주
            is_completed = False
            for task in next_day_tasks:
                # 텍스트 유사도 간단 체크 (더 정교한 유사도 계산 가능)
                issue_text_lower = issue_result.text.lower()
                task_text_lower = task.text.lower()
                
                # 키워드 매칭 (50% 이상 겹치면 수행된 것으로 간주)
                issue_words = set(issue_text_lower.split())
                task_words = set(task_text_lower.split())
                if issue_words and task_words:
                    overlap = len(issue_words & task_words) / len(issue_words)
                    if overlap > 0.5:  # 50% 이상 겹치면
                        is_completed = True
                        break
            
            # 수행되지 않은 미종결 업무만 포함
            if not is_completed:
                filtered_results.append(issue_result)
        
        return filtered_results
    
    def retrieve(
        self,
        query: str,
        date_range: Optional[Dict[str, date]] = None,
        reference_date: Optional[date] = None
    ) -> List[UnifiedSearchResult]:
        """
        ChromaDB에서 관련 일일보고서 검색
        
        Args:
            query: 사용자 질문
            date_range: 날짜 범위 필터 (예: {"start": date(2025, 1, 1), "end": date(2025, 12, 31)})
            reference_date: 기준 날짜 (상대적 날짜 계산용)
            
        Returns:
            검색 결과 리스트 (날짜 정렬됨)
        """
        # 기준 날짜 설정 (상대적 날짜 계산용)
        base_date = reference_date if reference_date else date.today()
        
        # 날짜 범위 설정 (기본값: 최근 1년)
        if date_range is None:
            end_date = base_date
            start_date = end_date - timedelta(days=365)
            period_start = start_date.strftime("%Y-%m-%d")
            period_end = end_date.strftime("%Y-%m-%d")
        else:
            period_start = date_range.get("start", base_date - timedelta(days=365)).strftime("%Y-%m-%d")
            period_end = date_range.get("end", base_date).strftime("%Y-%m-%d")
        
        # 미종결 업무 질의인지 확인
        is_unresolved_query = self._is_unresolved_task_query(query)
        
        if is_unresolved_query:
            # 미종결 업무 질의: pending 타입만 검색
            results = self.retriever.search_daily(
                query=query,
                owner=self.owner,
                period_start=period_start,
                period_end=period_end,
                n_results=self.top_k * 2,  # 필터링 전 더 많이 가져오기
                chunk_types=["pending"]  # pending 타입만 (새로운 4청크 구조)
            )
            
            # 다음 날 수행된 업무 제외
            results = self._filter_completed_unresolved_tasks(results)
            
            # top_k로 제한
            results = results[:self.top_k]
        else:
            # 일반 질의: detail, pending, plan_note 모두 검색
            results = self.retriever.search_daily(
                query=query,
                owner=self.owner,
                period_start=period_start,
                period_end=period_end,
                n_results=self.top_k,
                chunk_types=["detail", "pending", "plan_note"]  # 새로운 4청크 구조
            )
        
        # 날짜 기준 정렬 (최신순, 연도 포함 정확한 정렬)
        results.sort(
            key=lambda r: (
                self._parse_date_from_metadata(r.metadata) or date.min,
                -r.score  # 같은 날짜면 유사도 높은 순
            ),
            reverse=True  # 최신순
        )
        
        return results
    
    def format_context(self, results: List[UnifiedSearchResult]) -> str:
        """
        검색 결과를 LLM 컨텍스트로 포맷팅 (날짜 정렬된 순서로)
        
        Args:
            results: 검색 결과 리스트 (이미 날짜 정렬됨)
            
        Returns:
            포맷팅된 컨텍스트 문자열
        """
        if not results:
            return "검색 결과가 없습니다."
        
        context_parts = []
        
        for idx, result in enumerate(results, 1):
            # 메타데이터에서 날짜, 시간, 카테고리 추출
            metadata = result.metadata
            date_str = metadata.get("date", "날짜 정보 없음")
            
            # 날짜 파싱하여 정확한 형식으로 표시
            parsed_date = self._parse_date_from_metadata(metadata)
            if parsed_date:
                date_str = parsed_date.strftime("%Y-%m-%d")  # 연도 포함 정확한 형식
            
            time_slot = metadata.get("time_slot", "")
            chunk_type = result.chunk_type
            category = metadata.get("category", "")
            
            # 컨텍스트 구성
            context_line = f"[{idx}] "
            
            # 날짜 정보 (연도 포함)
            context_line += f"날짜: {date_str}"
            
            # 시간 정보 (있으면)
            if time_slot:
                context_line += f", 시간: {time_slot}"
            
            # 청크 타입 (새로운 4청크 구조만 사용)
            type_map = {
                "summary": "요약",
                "detail": "세부 업무",
                "pending": "미종결",
                "plan_note": "계획/특이사항"
            }
            context_line += f", 유형: {type_map.get(chunk_type, chunk_type)}"
            
            # 카테고리 (있으면)
            if category:
                context_line += f", 카테고리: {category}"
            
            context_line += "\n"
            context_line += f"내용: {result.text}\n"
            
            context_parts.append(context_line)
        
        return "\n---\n".join(context_parts)
    
    async def generate_response(
        self,
        query: str,
        date_range: Optional[Dict[str, date]] = None,
        reference_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        RAG 파이프라인 실행: 검색 → 컨텍스트 구성 → LLM 응답 생성
        
        Args:
            query: 사용자 질문
            date_range: 날짜 범위 필터
            
        Returns:
            {
                "answer": str,  # LLM 응답
                "sources": List[Dict],  # 근거 문서 정보
                "has_results": bool  # 검색 결과 존재 여부
            }
        """
        # 기준 날짜 설정 (상대적 날짜 계산용)
        base_date = reference_date if reference_date else date.today()
        
        # 1. 검색
        results = self.retrieve(query, date_range, reference_date)
        
        # 2. 검색 결과 없으면 바로 반환
        if not results:
            # 미종결 업무 질의인 경우 특별 메시지
            if self._is_unresolved_task_query(query):
                return {
                    "answer": "최근 미종결 업무는 없습니다.",
                    "sources": [],
                    "has_results": False
                }
            return {
                "answer": "죄송합니다. 일일보고서 데이터에서 관련 정보를 찾을 수 없습니다. 다른 질문을 해주시거나, 검색 기간을 조정해주세요.",
                "sources": [],
                "has_results": False
            }
        
        # 3. 컨텍스트 포맷팅
        context = self.format_context(results)
        
        # 4. LLM 프롬프트 구성
        is_unresolved_query = self._is_unresolved_task_query(query)
        
        # 기준 날짜 정보를 프롬프트에 포함
        base_date_str = base_date.strftime("%Y년 %m월 %d일")
        
        # 기준 날짜가 속한 주의 월요일~금요일 계산
        from datetime import timedelta
        weekday = base_date.weekday()  # 0=월요일, 6=일요일
        monday = base_date - timedelta(days=weekday)
        friday = monday + timedelta(days=4)
        this_week_range = f"{monday.strftime('%Y-%m-%d')} ~ {friday.strftime('%Y-%m-%d')}"
        this_week_range_kr = f"{monday.strftime('%Y년 %m월 %d일')} ~ {friday.strftime('%Y년 %m월 %d일')}"
        
        system_prompt = f"""당신은 일일보고서 데이터를 기반으로 질문에 답변하는 전문 어시스턴트입니다.

⚠️ 중요: 현재 기준 날짜는 {base_date_str} ({base_date.strftime("%Y-%m-%d")})입니다.
이 기준 날짜는 사용자가 일일보고서 날짜 설정에서 설정한 날짜입니다.

📅 날짜 범위 정의:
- "이번 주": 기준 날짜({base_date_str})가 속한 주의 월요일~금요일 = {this_week_range_kr} ({this_week_range})
- "지난 주": 이번 주 바로 전 주의 월요일~금요일
- "이번 달": 기준 날짜가 속한 달의 1일~말일
- "지난 달": 이번 달 바로 전 달의 1일~말일

규칙:
1. 제공된 검색 결과(일일보고서 데이터)만을 근거로 답변하세요.
2. 검색 결과에 없는 정보는 절대 추측하거나 만들어내지 마세요.
3. 날짜, 시간, 업무 내용 등은 검색 결과에서 정확히 인용하세요.
4. 여러 결과가 있으면 날짜순(최신순)으로 정리해서 답변하세요.
5. 검색 결과가 없으면 "데이터에서 찾을 수 없습니다"라고 명확히 답변하세요.
6. 자연스럽고 친절한 톤으로 답변하세요.
7. 필요시 날짜, 시간, 카테고리 정보를 포함해서 답변하세요.
8. 날짜 비교 시 연도(YYYY), 월(MM), 일(DD)을 모두 고려하여 정확히 비교하세요.
9. 예: 2025-01-15는 2024-12-20보다 최신입니다.
10. "이번 주"라고 질문하면 반드시 {this_week_range} 범위의 데이터만 검색하세요.

답변 형식:
- 질문에 대한 직접적인 답변
- 근거가 되는 날짜/시간 정보 포함 (연도 포함)
- 여러 결과가 있으면 날짜순(최신순) 목록으로 정리
- 상대적 날짜 표현을 사용할 때는 구체적인 날짜 범위를 명시하세요 (예: "이번 주({this_week_range})")"""
        
        if is_unresolved_query:
            system_prompt += "\n\n특별 규칙 (미종결 업무 질의):\n- 제공된 검색 결과는 이미 다음 날 수행 여부를 확인하여 필터링된 '진행되지 않은' 미종결 업무만 포함합니다.\n- 따라서 검색 결과에 나온 항목들은 모두 아직 미종결 상태입니다."
        
        user_prompt = f"""사용자 질문: {query}

검색된 일일보고서 데이터:
{context}

위 데이터를 기반으로 사용자 질문에 답변해주세요. 검색 결과에 없는 정보는 절대 만들어내지 마세요."""
        
        # 5. LLM 호출
        try:
            answer = await self.llm.acomplete(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7
            )
        except Exception as e:
            print(f"[ERROR] LLM 호출 실패: {e}")
            return {
                "answer": "죄송합니다. 응답 생성 중 오류가 발생했습니다.",
                "sources": [],
                "has_results": False
            }
        
        # 6. 근거 문서 정보 구성
        sources = []
        for result in results:
            metadata = result.metadata
            sources.append({
                "date": metadata.get("date", ""),
                "time_slot": metadata.get("time_slot", ""),
                "chunk_type": result.chunk_type,
                "category": metadata.get("category", ""),
                "text_preview": result.text[:100] + "..." if len(result.text) > 100 else result.text,
                "score": round(result.score, 3)
            })
        
        return {
            "answer": answer,
            "sources": sources,
            "has_results": True
        }

