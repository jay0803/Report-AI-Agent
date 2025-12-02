"""
RAG Chain for Daily Report Chatbot

일일보고서 데이터를 기반으로 한 RAG 챗봇 체인
날짜 필터링을 검색 이전 단계에서 강제하고, 통계형 질의는 별도 로직으로 처리
"""
from typing import List, Optional, Dict, Any, Set
from datetime import date, datetime, timedelta
from collections import Counter
import re

from app.infrastructure.vector_store_report import get_report_vector_store
from app.domain.report.search.retriever import UnifiedRetriever, UnifiedSearchResult
from app.domain.report.core.utils_text import extract_customer_names
from app.domain.report.search.hybrid_search import (
    QueryAnalyzer,
    HybridSearcher,
    SearchKeywords
)
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
        
        # 하이브리드 검색기 초기화
        import os
        vector_store = get_report_vector_store()
        collection = vector_store.get_collection()
        embedding_model_type = os.getenv("REPORT_EMBEDDING_MODEL_TYPE", "hf")
        self.hybrid_searcher = HybridSearcher(
            collection=collection,
            embedding_model_type=embedding_model_type
        )
        
        # Retriever 초기화 (하위 호환성 유지)
        if retriever is None:
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
    
    def _detect_relative_date_range(self, query: str, base_date: date) -> Optional[Dict[str, date]]:
        """
        질문에서 상대적 날짜 키워드 또는 구체적인 날짜를 정규식 기반으로 감지하여 날짜 범위 반환
        
        Args:
            query: 사용자 질문
            base_date: 기준 날짜
            
        Returns:
            날짜 범위 딕셔너리 또는 None
        """
        # 쿼리 정규화 (특수문자 제거 및 공백 정리)
        query_lower = query.lower()
        query_normalized = query_lower.replace('(', ' ').replace(')', ' ').replace('?', ' ').replace('!', ' ').replace(',', ' ').replace('.', ' ')
        query_normalized = ' '.join(query_normalized.split())
        
        # ========== 구체적인 날짜 패턴 감지 (최우선) ==========
        # 패턴: "2025년 10월 7일", "2025-10-07", "10월 7일" 등
        specific_date_patterns = [
            # "2025년 10월 7일" 형식
            re.compile(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일'),
            # "2025-10-07" 형식
            re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})'),
            # "10월 7일" 형식 (올해로 가정)
            re.compile(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일'),
        ]
        
        for pattern in specific_date_patterns:
            match = pattern.search(query_normalized)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        # "2025년 10월 7일" 또는 "2025-10-07" 형식
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        detected_date = date(year, month, day)
                    elif len(groups) == 2:
                        # "10월 7일" 형식 (올해로 가정)
                        month, day = int(groups[0]), int(groups[1])
                        year = base_date.year
                        detected_date = date(year, month, day)
                    else:
                        continue
                    
                    # 단일 날짜는 start와 end가 동일
                    return {"start": detected_date, "end": detected_date}
                except (ValueError, TypeError):
                    continue
        # =====================================================
        
        # 정규식 패턴 정의 (상대적 날짜)
        patterns = {
            'this_week': re.compile(r'(이번\s*주|금주)'),
            'last_week': re.compile(r'(지난\s*주|저번\s*주|전주)'),
            'this_month': re.compile(r'(이번\s*달|금월|이번\s*월)'),
            'last_month': re.compile(r'(지난\s*달|전월|지난\s*월)')
        }
        
        # 이번 주 감지
        if patterns['this_week'].search(query_normalized):
            weekday = base_date.weekday()  # 0=월요일, 6=일요일
            monday = base_date - timedelta(days=weekday)
            friday = monday + timedelta(days=4)
            return {"start": monday, "end": friday}
        
        # 지난 주 감지
        if patterns['last_week'].search(query_normalized):
            weekday = base_date.weekday()
            monday = base_date - timedelta(days=weekday)
            last_week_monday = monday - timedelta(days=7)
            last_week_friday = last_week_monday + timedelta(days=4)
            return {"start": last_week_monday, "end": last_week_friday}
        
        # 이번 달 감지
        if patterns['this_month'].search(query_normalized):
            first_day = base_date.replace(day=1)
            if base_date.month == 12:
                last_day = base_date.replace(year=base_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = base_date.replace(month=base_date.month + 1, day=1) - timedelta(days=1)
            return {"start": first_day, "end": last_day}
        
        # 지난 달 감지
        if patterns['last_month'].search(query_normalized):
            if base_date.month == 1:
                last_month = base_date.replace(year=base_date.year - 1, month=12, day=1)
            else:
                last_month = base_date.replace(month=base_date.month - 1, day=1)
            first_day = last_month.replace(day=1)
            last_day = base_date.replace(day=1) - timedelta(days=1)
            return {"start": first_day, "end": last_day}
        
        return None
    
    def _is_statistical_query(self, query: str) -> bool:
        """
        통계형 질의인지 판단 (요일별 count, 가장 많은 날 등)
        
        Args:
            query: 사용자 질문
            
        Returns:
            통계형 질의 여부
        """
        query_lower = query.lower()
        statistical_keywords = [
            "가장", "많이", "몰린", "많은", "적은", "적게",
            "요일", "날짜", "날", "언제", "어느",
            "count", "통계", "집계", "분포"
        ]
        return any(keyword in query_lower for keyword in statistical_keywords)
    
    def _is_comparison_query(self, query: str) -> bool:
        """
        비교형 질의인지 판단 (예: "11월과 10월 비교", "건수 비교")
        
        Args:
            query: 사용자 질문
            
        Returns:
            비교형 질의 여부
        """
        query_lower = query.lower()
        comparison_keywords = [
            "비교", "비율", "차이", "변화", "증가", "감소", "늘어", "줄어",
            "대비", "대조", "대해", "vs", "versus"
        ]
        return any(keyword in query_lower for keyword in comparison_keywords)
    
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
    
    def _get_document_ids_in_range(
        self,
        start_date: date,
        end_date: date,
        owner: Optional[str] = None
    ) -> Set[str]:
        """
        날짜 범위에 해당하는 문서 ID 목록 추출 (검색 전 필터링)
        
        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜
            owner: 작성자 필터 (None이면 전체)
            
        Returns:
            문서 ID 집합
        """
        collection = self.retriever.collection
        
        # 날짜 범위 내 모든 날짜 리스트 생성
        date_list = []
        current = start_date
        while current <= end_date:
            date_list.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        print(f"[DEBUG] 날짜 범위 내 문서 ID 추출: {start_date} ~ {end_date} ({len(date_list)}일)")
        
        # 필터 조건 구성
        conditions = [
            {"report_type": {"$in": ["daily", "weekly", "monthly"]}},
            {"level": "daily"},
            {"date": {"$in": date_list}}
        ]
        
        if owner:
            conditions.append({"owner": owner})
        
        where_filter = {"$and": conditions} if len(conditions) > 1 else conditions[0]
        
        # ChromaDB에서 날짜 범위 내 모든 문서 가져오기
        try:
            results = collection.get(
                where=where_filter,
                limit=10000,  # 충분히 큰 수
                include=["metadatas"]
            )
            
            # doc_id 추출 (중복 제거)
            doc_ids = set()
            if results and results.get("ids"):
                for metadata in results.get("metadatas", []):
                    doc_id = metadata.get("doc_id")
                    if doc_id:
                        doc_ids.add(doc_id)
            
            print(f"[DEBUG] 날짜 범위 내 문서 ID 추출 완료: {len(doc_ids)}개 문서")
            if doc_ids:
                sample_ids = list(doc_ids)[:5]
                print(f"[DEBUG] 샘플 문서 ID: {sample_ids}")
            
            return doc_ids
            
        except Exception as e:
            print(f"[ERROR] 문서 ID 추출 실패: {e}")
            import traceback
            traceback.print_exc()
            return set()
    
    def _collect_daily_counts(
        self,
        date_range: Dict[str, date],
        category_keyword: str = "상담",
        owner: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        날짜별 통계 수집 (통계형 질의 처리용)
        
        Args:
            date_range: 날짜 범위 {"start": date, "end": date}
            category_keyword: 카테고리 키워드 (예: "상담")
            owner: 작성자 필터
            
        Returns:
            {
                "date_counts": Dict[str, int],  # 날짜별 count
                "max_date": Optional[str],  # 가장 많은 날짜
                "max_count": int,  # 최대 count
                "details": List[Dict]  # 상세 정보
            }
        """
        start_date = date_range["start"]
        end_date = date_range["end"]
        
        print(f"[DEBUG] 통계 수집 시작: {start_date} ~ {end_date}, 카테고리: {category_keyword}")
        
        # 날짜 범위 내 문서 ID 추출
        doc_ids = self._get_document_ids_in_range(start_date, end_date, owner)
        
        if not doc_ids:
            print(f"[WARNING] 날짜 범위 내 문서를 찾을 수 없습니다.")
            return {
                "date_counts": {},
                "max_date": None,
                "max_count": 0,
                "details": []
            }
        
        # 해당 문서들에서 detail 청크만 가져오기
        collection = self.retriever.collection
        
        # 필터 조건
        conditions = [
            {"doc_id": {"$in": list(doc_ids)}},
            {"chunk_type": "detail"},
            {"report_type": {"$in": ["daily", "weekly", "monthly"]}},
            {"level": "daily"}
        ]
        
        if owner:
            conditions.append({"owner": owner})
        
        where_filter = {"$and": conditions}
        
        try:
            # 모든 detail 청크 가져오기
            results = collection.get(
                where=where_filter,
                limit=10000,
                include=["metadatas", "documents"]
            )
            
            # 날짜별 카운팅
            date_counts = Counter()
            details = []
            
            if results and results.get("ids"):
                for i, metadata in enumerate(results.get("metadatas", [])):
                    doc_text = results.get("documents", [])[i] if results.get("documents") else ""
                    
                    # 카테고리 키워드 매칭
                    category = metadata.get("category", "")
                    text_lower = doc_text.lower()
                    
                    # 카테고리 또는 텍스트에 키워드 포함 여부 확인
                    is_match = (
                        category_keyword in category or
                        category_keyword in text_lower
                    )
                    
                    if is_match:
                        doc_date = metadata.get("date")
                        if doc_date:
                            date_counts[doc_date] += 1
                            details.append({
                                "date": doc_date,
                                "text": doc_text[:100] + "..." if len(doc_text) > 100 else doc_text,
                                "category": category
                            })
            
            # 최대 count 날짜 찾기
            max_date = None
            max_count = 0
            if date_counts:
                max_date = date_counts.most_common(1)[0][0]
                max_count = date_counts.most_common(1)[0][1]
            
            print(f"[DEBUG] 통계 수집 완료: {len(date_counts)}개 날짜, 최대 count: {max_count} ({max_date})")
            
            return {
                "date_counts": dict(date_counts),
                "max_date": max_date,
                "max_count": max_count,
                "details": details
            }
            
        except Exception as e:
            print(f"[ERROR] 통계 수집 실패: {e}")
            import traceback
            traceback.print_exc()
            return {
                "date_counts": {},
                "max_date": None,
                "max_count": 0,
                "details": []
            }
    
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
            # 날짜 범위 먼저 추출
            doc_ids = self._get_document_ids_in_range(next_day, next_day, self.owner)
            
            next_day_tasks = self.retriever.search_daily(
                query=issue_result.text,  # 미종결 업무 텍스트로 검색
                owner=self.owner,
                single_date=next_day.strftime("%Y-%m-%d"),
                n_results=10,
                chunk_types=["detail"],  # detail 타입만 (새로운 4청크 구조)
                doc_ids=list(doc_ids) if doc_ids else None
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
        하이브리드 검색: Keyword Filter → Vector Search → top_k 적용
        
        Args:
            query: 사용자 질문
            date_range: 날짜 범위 필터 (예: {"start": date(2025, 1, 1), "end": date(2025, 12, 31)})
            reference_date: 기준 날짜 (상대적 날짜 계산용)
            
        Returns:
            검색 결과 리스트 (relevance 기준 정렬, top_k 적용)
        """
        # 기준 날짜 설정
        base_date = reference_date if reference_date else date.today()
        
        # 1. 키워드 추출
        keywords = QueryAnalyzer.extract_keywords(query, base_date, self.owner)
        
        # 명시적 date_range가 있으면 키워드의 날짜 범위를 덮어쓰기
        if date_range:
            keywords.date_range = date_range
            keywords.single_date = None
        
        # 비교/통계 질의 감지
        is_comparison = self._is_comparison_query(query)
        is_statistical = self._is_statistical_query(query)
        requires_all_data = is_comparison or is_statistical
        
        # 검색 결과 개수 결정
        search_top_k = self.top_k
        if keywords.customer_names:
            # 고객명이 있으면 더 많이 검색
            search_top_k = self.top_k * 2
        elif requires_all_data:
            # 비교/통계 질의는 모든 데이터 필요 (top_k 제한 없음)
            search_top_k = 10000  # 충분히 큰 수
        
        # 2. 하이브리드 검색 수행
        results = self.hybrid_searcher.search(
            query=query,
            keywords=keywords,
            owner=self.owner,
            base_date_range=date_range,
            top_k=search_top_k
        )
        
        # 3. 미종결 업무 질의인 경우 다음 날 수행된 업무 제외
        if keywords.is_unresolved_query:
            results = self._filter_completed_unresolved_tasks(results)
        
        # 4. 최종 top_k 적용 (비교/통계 질의는 제한 없음)
        if requires_all_data:
            print(f"[DEBUG] 비교/통계 질의: top_k 제한 제거, 모든 결과 반환 ({len(results)}개)")
            # 모든 결과 반환 (제한 없음)
            final_results = results
        else:
            final_results = results[:self.top_k]
        
        print(f"[DEBUG] 최종 검색 결과: {len(final_results)}개 (요청된 top_k={self.top_k}, 비교/통계 질의: {requires_all_data})")
        
        return final_results
    
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
        통계형 질의는 별도 로직으로 처리
        
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
        
        # 날짜 범위 감지 (프롬프트에서도 사용)
        detected_range = self._detect_relative_date_range(query, base_date)
        if detected_range:
            date_range = detected_range
        
        # ========== 통계형 질의 처리 ==========
        is_statistical = self._is_statistical_query(query)
        
        if is_statistical and date_range:
            print(f"[DEBUG] 통계형 질의 감지: '{query}'")
            
            # 카테고리 키워드 추출 (예: "상담", "업무" 등)
            query_lower = query.lower()
            category_keyword = "상담"  # 기본값
            if "상담" in query_lower:
                category_keyword = "상담"
            elif "업무" in query_lower:
                category_keyword = "업무"
            
            # 날짜별 통계 수집
            stats = self._collect_daily_counts(date_range, category_keyword, self.owner)
            
            if stats["max_date"] and stats["max_count"] > 0:
                # 통계 결과를 LLM에게 전달
                max_date_str = stats["max_date"]
                max_count = stats["max_count"]
                date_counts_str = ", ".join([f"{d}: {c}건" for d, c in sorted(stats["date_counts"].items())])
                
                # 간단한 답변 생성
                answer = f"{date_range['start']} ~ {date_range['end']} 기간 동안 {category_keyword} 업무가 가장 많은 날은 {max_date_str}이며, 총 {max_count}건입니다.\n\n"
                answer += f"날짜별 통계: {date_counts_str}"
                
                # 근거 정보 구성
                sources = []
                for detail in stats["details"][:10]:  # 최대 10개
                    sources.append({
                        "date": detail["date"],
                        "time_slot": "",
                        "chunk_type": "detail",
                        "category": detail.get("category", ""),
                        "text_preview": detail["text"],
                        "score": 1.0
                    })
                
                return {
                    "answer": answer,
                    "sources": sources,
                    "has_results": True
                }
            else:
                # 통계 결과 없음
                return {
                    "answer": f"{date_range['start']} ~ {date_range['end']} 기간 동안 {category_keyword} 관련 데이터를 찾을 수 없습니다.",
                    "sources": [],
                    "has_results": False
                }
        # =====================================
        
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
        
        system_prompt = """당신은 일일보고서 데이터를 기반으로 질문에 답변하는 전문 어시스턴트입니다.

⚠️ 중요: 날짜 범위 필터링과 문서 검색은 이미 시스템에서 처리되었습니다.
제공된 컨텍스트는 질문에 관련된 데이터만 포함되어 있습니다.

규칙:
1. 제공된 컨텍스트(일일보고서 데이터)만을 근거로 답변하세요.
2. 컨텍스트에 없는 정보는 절대 추측하거나 만들어내지 마세요.
3. 날짜, 시간, 업무 내용 등은 컨텍스트에서 정확히 인용하세요.
4. 여러 결과가 있으면 날짜순(최신순)으로 정리해서 답변하세요.
5. 컨텍스트에 데이터가 없으면 "데이터에서 찾을 수 없습니다"라고 명확히 답변하세요.
6. 자연스럽고 친절한 톤으로 답변하세요.
7. 필요시 날짜, 시간, 카테고리 정보를 포함해서 답변하세요.

답변 형식:
- 질문에 대한 직접적인 답변
- 근거가 되는 날짜/시간 정보 포함 (연도 포함)
- 여러 결과가 있으면 날짜순(최신순) 목록으로 정리"""
        
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
