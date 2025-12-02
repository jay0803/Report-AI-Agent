"""
Hybrid Search Implementation
하이브리드 검색: Keyword Filter → Vector Search → top_k 적용

Author: AI Assistant
Created: 2025-12-02
"""
from typing import List, Optional, Dict, Any, Set
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import re
import numpy as np

from chromadb import Collection
from app.domain.report.search.retriever import UnifiedSearchResult, UnifiedRetriever
from app.domain.report.core.utils_text import extract_customer_names
from ingestion.embed import get_embedding_service


@dataclass
class SearchKeywords:
    """추출된 검색 키워드"""
    customer_names: List[str] = None
    date_range: Optional[Dict[str, date]] = None
    single_date: Optional[str] = None
    chunk_types: List[str] = None
    is_unresolved_query: bool = False
    is_statistical_query: bool = False
    
    def __post_init__(self):
        if self.customer_names is None:
            self.customer_names = []
        if self.chunk_types is None:
            self.chunk_types = []


class QueryAnalyzer:
    """쿼리 분석 및 키워드 추출"""
    
    @staticmethod
    def extract_keywords(
        query: str,
        base_date: Optional[date] = None,
        owner: Optional[str] = None
    ) -> SearchKeywords:
        """
        쿼리에서 검색 키워드 추출
        
        Args:
            query: 사용자 질문
            base_date: 기준 날짜 (상대적 날짜 계산용)
            owner: 작성자 (필터링용)
            
        Returns:
            SearchKeywords 객체
        """
        if base_date is None:
            base_date = date.today()
        
        # 고객명 추출
        customer_names = extract_customer_names(query)
        
        # 날짜 범위 추출
        date_range = QueryAnalyzer._detect_date_range(query, base_date)
        single_date = None
        if date_range and date_range["start"] == date_range["end"]:
            single_date = date_range["start"].strftime("%Y-%m-%d")
            date_range = None
        
        # 청크 타입 추출
        chunk_types = QueryAnalyzer._detect_chunk_types(query)
        
        # 미종결 업무 질의 감지
        is_unresolved = QueryAnalyzer._is_unresolved_query(query)
        
        # 통계형 질의 감지
        is_statistical = QueryAnalyzer._is_statistical_query(query)
        
        return SearchKeywords(
            customer_names=customer_names,
            date_range=date_range,
            single_date=single_date,
            chunk_types=chunk_types,
            is_unresolved_query=is_unresolved,
            is_statistical_query=is_statistical
        )
    
    @staticmethod
    def _detect_date_range(query: str, base_date: date) -> Optional[Dict[str, date]]:
        """
        쿼리에서 날짜 범위 감지
        
        Args:
            query: 사용자 질문
            base_date: 기준 날짜
            
        Returns:
            {"start": date, "end": date} 또는 None
        """
        query_lower = query.lower()
        query_normalized = query_lower.replace('(', ' ').replace(')', ' ').replace('?', ' ').replace('!', ' ').replace(',', ' ').replace('.', ' ')
        query_normalized = ' '.join(query_normalized.split())
        
        # 구체적인 날짜 패턴 감지 (최우선)
        specific_date_patterns = [
            re.compile(r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일'),
            re.compile(r'(\d{4})-(\d{1,2})-(\d{1,2})'),
            re.compile(r'(\d{1,2})\s*월\s*(\d{1,2})\s*일'),
        ]
        
        for pattern in specific_date_patterns:
            match = pattern.search(query_normalized)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        detected_date = date(year, month, day)
                    elif len(groups) == 2:
                        month, day = int(groups[0]), int(groups[1])
                        year = base_date.year
                        detected_date = date(year, month, day)
                    else:
                        continue
                    
                    return {"start": detected_date, "end": detected_date}
                except (ValueError, TypeError):
                    continue
        
        # 상대적 날짜 패턴 감지
        patterns = {
            'this_week': re.compile(r'(이번\s*주|금주)'),
            'last_week': re.compile(r'(지난\s*주|저번\s*주|전주)'),
            'this_month': re.compile(r'(이번\s*달|금월|이번\s*월)'),
            'last_month': re.compile(r'(지난\s*달|전월|지난\s*월)')
        }
        
        if patterns['this_week'].search(query_normalized):
            weekday = base_date.weekday()
            monday = base_date - timedelta(days=weekday)
            friday = monday + timedelta(days=4)
            return {"start": monday, "end": friday}
        
        if patterns['last_week'].search(query_normalized):
            weekday = base_date.weekday()
            monday = base_date - timedelta(days=weekday)
            last_week_monday = monday - timedelta(days=7)
            last_week_friday = last_week_monday + timedelta(days=4)
            return {"start": last_week_monday, "end": last_week_friday}
        
        if patterns['this_month'].search(query_normalized):
            first_day = base_date.replace(day=1)
            if base_date.month == 12:
                last_day = base_date.replace(year=base_date.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                last_day = base_date.replace(month=base_date.month + 1, day=1) - timedelta(days=1)
            return {"start": first_day, "end": last_day}
        
        if patterns['last_month'].search(query_normalized):
            if base_date.month == 1:
                last_month = base_date.replace(year=base_date.year - 1, month=12, day=1)
            else:
                last_month = base_date.replace(month=base_date.month - 1, day=1)
            first_day = last_month.replace(day=1)
            last_day = base_date.replace(day=1) - timedelta(days=1)
            return {"start": first_day, "end": last_day}
        
        return None
    
    @staticmethod
    def _detect_chunk_types(query: str) -> List[str]:
        """
        쿼리에서 청크 타입 감지
        
        Args:
            query: 사용자 질문
            
        Returns:
            청크 타입 리스트 (기본값: ["detail", "pending", "plan_note"])
        """
        query_lower = query.lower()
        
        # 미종결 관련 키워드
        if any(keyword in query_lower for keyword in ["미종결", "미완료", "처리 못한", "안 한", "안한"]):
            return ["pending"]
        
        # 요약 관련 키워드
        if any(keyword in query_lower for keyword in ["요약", "전체", "종합"]):
            return ["summary"]
        
        # 계획 관련 키워드
        if any(keyword in query_lower for keyword in ["계획", "예정", "일정"]):
            return ["plan_note"]
        
        # 기본값: detail, pending, plan_note
        return ["detail", "pending", "plan_note"]
    
    @staticmethod
    def _is_unresolved_query(query: str) -> bool:
        """미종결 업무 질의인지 판단"""
        query_lower = query.lower()
        unresolved_keywords = ["미종결", "미완료", "처리 못한", "안 한", "안한", "안 끝난", "안끝난"]
        return any(keyword in query_lower for keyword in unresolved_keywords)
    
    @staticmethod
    def _is_statistical_query(query: str) -> bool:
        """통계형 질의인지 판단"""
        query_lower = query.lower()
        statistical_keywords = ["가장", "많이", "몰린", "요일", "날짜", "통계", "평균", "최대", "최소", "집계", "분포"]
        return any(keyword in query_lower for keyword in statistical_keywords)
    
    @staticmethod
    def _is_comparison_query(query: str) -> bool:
        """비교형 질의인지 판단"""
        query_lower = query.lower()
        comparison_keywords = ["비교", "비율", "차이", "변화", "증가", "감소", "늘어", "줄어", "대비", "대조", "vs", "versus"]
        return any(keyword in query_lower for keyword in comparison_keywords)


class KeywordFilter:
    """키워드 기반 필터링 (ChromaDB where 조건 구성)"""
    
    @staticmethod
    def build_where_filter(
        keywords: SearchKeywords,
        owner: Optional[str] = None,
        base_date_range: Optional[Dict[str, date]] = None
    ) -> Dict[str, Any]:
        """
        ChromaDB where 필터 조건 구성
        
        Args:
            keywords: 추출된 키워드
            owner: 작성자 필터
            base_date_range: 기본 날짜 범위 (쿼리에서 추출되지 않은 경우)
            
        Returns:
            ChromaDB where 필터 딕셔너리
        """
        conditions = []
        
        # 기본 조건: report_type, level
        conditions.append({
            "report_type": {"$in": ["daily", "weekly", "monthly"]}
        })
        conditions.append({"level": "daily"})
        
        # 작성자 필터
        if owner:
            conditions.append({"owner": owner})
        
        # 날짜 필터
        date_range = keywords.date_range or base_date_range
        if keywords.single_date:
            conditions.append({"date": keywords.single_date})
        elif date_range:
            start = date_range["start"]
            end = date_range["end"]
            date_list = []
            current = start
            while current <= end:
                date_list.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
            if date_list:
                conditions.append({"date": {"$in": date_list}})
        else:
            # 기본값: 최근 1년
            end_date = date.today()
            start_date = end_date - timedelta(days=365)
            date_list = []
            current = start_date
            while current <= end_date:
                date_list.append(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
            if date_list:
                conditions.append({"date": {"$in": date_list}})
        
        # 청크 타입 필터
        if keywords.chunk_types:
            conditions.append({
                "chunk_type": {"$in": keywords.chunk_types}
            })
        
        # 고객명 필터 (ChromaDB는 문자열 포함 검색을 직접 지원하지 않으므로,
        # 여기서는 조건만 준비하고, 실제 필터링은 검색 후 수행)
        
        # 조건이 하나만 있으면 그대로, 여러개면 $and로 묶기
        if len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}
    
    @staticmethod
    def filter_by_customer(
        results: List[UnifiedSearchResult],
        customer_names: List[str]
    ) -> List[UnifiedSearchResult]:
        """
        검색 결과를 고객명으로 필터링
        
        Args:
            results: 검색 결과 리스트
            customer_names: 고객명 리스트
            
        Returns:
            필터링된 결과 리스트
        """
        if not customer_names:
            return results
        
        filtered = []
        for result in results:
            # 텍스트나 메타데이터에서 고객명 확인
            text_lower = result.text.lower()
            metadata_customer = str(result.metadata.get("customer", "")).strip().lower()
            
            for customer_name in customer_names:
                if customer_name in text_lower or customer_name in metadata_customer:
                    filtered.append(result)
                    break
        
        return filtered


class HybridSearcher:
    """하이브리드 검색 실행기"""
    
    def __init__(
        self,
        collection: Collection,
        embedding_model_type: Optional[str] = None
    ):
        """
        초기화
        
        Args:
            collection: ChromaDB Collection 객체
            embedding_model_type: 임베딩 모델 타입
        """
        self.collection = collection
        self.embedding_service = get_embedding_service(model_type=embedding_model_type)
    
    def search(
        self,
        query: str,
        keywords: SearchKeywords,
        owner: Optional[str] = None,
        base_date_range: Optional[Dict[str, date]] = None,
        top_k: int = 5
    ) -> List[UnifiedSearchResult]:
        """
        하이브리드 검색 수행
        
        단계:
        1. Keyword Filter: where 조건으로 문서 필터링
        2. Vector Search: 필터된 문서에 대해 벡터 유사도 검색
        3. Customer Filter: 고객명으로 추가 필터링 (필요시)
        4. Top-k: relevance 기준 정렬 후 top_k 적용
        
        Args:
            query: 검색 쿼리
            keywords: 추출된 키워드
            owner: 작성자 필터
            base_date_range: 기본 날짜 범위
            top_k: 반환할 결과 개수
            
        Returns:
            검색 결과 리스트 (relevance 기준 정렬)
        """
        # 1. Keyword Filter: where 조건 구성
        # 고객명이 있으면 날짜 필터 제거 (전체 기간 검색)
        effective_date_range = None if keywords.customer_names else base_date_range
        
        where_filter = KeywordFilter.build_where_filter(
            keywords=keywords,
            owner=owner,
            base_date_range=effective_date_range
        )
        
        print(f"[DEBUG] 하이브리드 검색 시작: query='{query}'")
        print(f"[DEBUG] 추출된 키워드: 고객명={keywords.customer_names}, 날짜범위={keywords.date_range}, 청크타입={keywords.chunk_types}")
        print(f"[DEBUG] where 필터 (고객명 있으면 날짜 제외): {where_filter}")
        
        # 고객명이 추출된 경우: 메타데이터에서 직접 고객명 검색 (키워드 기반 필터링)
        customer_matched_chunk_ids = set()
        
        if keywords.customer_names:
            # 제외 단어 목록
            excluded_words = {"상담", "보장", "리포트", "자료", "정리", "구성", "작성", "분석", "업무", "일정", "계획"}
            actual_customer_names = [name for name in keywords.customer_names if name not in excluded_words]
            
            if actual_customer_names:
                print(f"[DEBUG] 고객명 키워드 기반 검색 시작: {actual_customer_names}")
                
                # 날짜 범위 설정
                date_range = keywords.date_range or base_date_range
                
                # 기본 필터 조건
                base_filter = {
                    "$and": [
                        {"report_type": {"$in": ["daily", "weekly", "monthly"]}},
                        {"level": "daily"}
                    ]
                }
                
                # 고객명 검색 시 날짜 필터 완전 제거 (모든 기간 검색)
                # 고객명은 오래된 기록도 중요하므로 날짜 제한 없이 전체 검색
                print(f"[DEBUG] 고객명 검색: 날짜 필터 제거, 전체 기간 검색 수행")
                # 날짜 필터 추가하지 않음 (전체 검색)
                
                if owner:
                    base_filter["$and"].append({"owner": owner})
                
                if keywords.chunk_types:
                    base_filter["$and"].append({"chunk_type": {"$in": keywords.chunk_types}})
                
                # 고객명이 포함된 청크를 메타데이터에서 직접 검색
                try:
                    # 필터 조건 내 모든 청크 가져오기
                    # ids는 기본 포함이므로 include에서 제외
                    all_chunks = self.collection.get(
                        where=base_filter,
                        limit=50000,  # 더 큰 수로 증가
                        include=["metadatas", "documents"]
                    )
                    
                    print(f"[DEBUG] 고객명 검색: 전체 청크 {len(all_chunks.get('ids', [])) if all_chunks and all_chunks.get('ids') else 0}개 조회됨")
                    
                    # 고객명이 포함된 청크만 필터링
                    if all_chunks and all_chunks.get("ids"):
                        ids = all_chunks.get("ids", [])
                        metadatas = all_chunks.get("metadatas", [])
                        documents = all_chunks.get("documents", [])
                        
                        for idx in range(len(ids)):
                            metadata = metadatas[idx] if idx < len(metadatas) else {}
                            document_text = documents[idx] if idx < len(documents) else ""
                            
                            customer_field = str(metadata.get("customer", "")).strip()
                            text_for_search = f"{customer_field} {document_text}".lower()
                            
                            # 고객명이 메타데이터나 텍스트에 포함된 경우
                            for customer_name in actual_customer_names:
                                if customer_name in text_for_search:
                                    chunk_id = ids[idx]
                                    customer_matched_chunk_ids.add(chunk_id)
                                    break
                    
                    print(f"[DEBUG] 고객명 키워드 기반 검색: {len(customer_matched_chunk_ids)}개 청크 발견 (고객명: {actual_customer_names})")
                    
                    # 발견된 날짜 확인
                    if customer_matched_chunk_ids and all_chunks:
                        dates_found = set()
                        ids = all_chunks.get("ids", [])
                        metadatas = all_chunks.get("metadatas", [])
                        for chunk_id in customer_matched_chunk_ids:
                            if chunk_id in ids:
                                idx = ids.index(chunk_id)
                                if idx < len(metadatas):
                                    date_str = metadatas[idx].get("date", "")
                                    if date_str:
                                        dates_found.add(date_str)
                        print(f"[DEBUG] 고객명 검색으로 발견된 날짜: {sorted(dates_found)}")
                    
                except Exception as e:
                    print(f"[WARNING] 고객명 직접 검색 실패: {e}")
                    import traceback
                    traceback.print_exc()
                    customer_matched_chunk_ids = set()
        
        # 2. Vector Search: 필터된 문서에 대해 벡터 검색
        query_embedding = self.embedding_service.embed_text(query)
        
        # 검색 결과 개수 결정: 고객명이 있으면 최대한 많이 가져오기 (모든 날짜 포함)
        n_results_for_query = max(top_k * 50 if keywords.customer_names else top_k * 5, 500)
        print(f"[DEBUG] 벡터 검색: n_results={n_results_for_query} (고객명 질의: 더 많이 검색)")
        
        # 고객명으로 직접 찾은 청크가 있으면, 그 청크들만 대상으로 벡터 검색
        if customer_matched_chunk_ids:
            # 고객명으로 찾은 청크들을 직접 결과로 사용
            try:
                customer_chunks = self.collection.get(
                    ids=list(customer_matched_chunk_ids),
                    include=["metadatas", "documents", "embeddings"]
                )
                
                # 고객명 매칭 청크들을 UnifiedSearchResult로 변환
                search_results_from_customer = []
                if customer_chunks and customer_chunks.get("ids"):
                    query_embedding = self.embedding_service.embed_text(query)
                    
                    # 각 청크의 임베딩과 쿼리 임베딩 간 유사도 계산
                    for idx, chunk_id in enumerate(customer_chunks.get("ids", [])):
                        chunk_embedding = customer_chunks.get("embeddings", [])[idx] if customer_chunks.get("embeddings") else None
                        document_text = customer_chunks.get("documents", [])[idx] if idx < len(customer_chunks.get("documents", [])) else ""
                        metadata = customer_chunks.get("metadatas", [])[idx] if idx < len(customer_chunks.get("metadatas", [])) else {}
                        
                        # 유사도 계산 (임베딩이 있는 경우)
                        if chunk_embedding:
                            # 코사인 유사도 계산
                            query_vec = np.array(query_embedding)
                            chunk_vec = np.array(chunk_embedding)
                            similarity = np.dot(query_vec, chunk_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(chunk_vec))
                            score = float(similarity)
                        else:
                            # 임베딩이 없으면 기본 점수
                            score = 1.0
                        
                        search_results_from_customer.append(
                            UnifiedSearchResult(
                                chunk_id=chunk_id,
                                doc_id=metadata.get("doc_id", ""),
                                doc_type=metadata.get("doc_type", "daily"),
                                chunk_type=metadata.get("chunk_type", ""),
                                text=document_text,
                                score=score,
                                metadata=metadata
                            )
                        )
                    
                    # 유사도 기준 정렬
                    search_results_from_customer.sort(key=lambda r: -r.score)
                    print(f"[DEBUG] 고객명 직접 검색 결과: {len(search_results_from_customer)}개 청크, 유사도 계산 완료")
                    
            except Exception as e:
                print(f"[WARNING] 고객명 청크 유사도 계산 실패: {e}")
                search_results_from_customer = []
                customer_matched_chunk_ids = set()
        
        # 고객명으로 직접 찾은 결과가 있으면 우선 사용
        if customer_matched_chunk_ids and search_results_from_customer:
            # 고객명 직접 검색 결과를 우선 사용
            print(f"[DEBUG] 고객명 직접 검색 결과 우선 사용: {len(search_results_from_customer)}개")
            
            # "모든 날짜" 요청인지 확인 ("다", "모두", "전부", "전체", "모든" 키워드)
            query_lower = query.lower()
            all_date_keywords = ["다", "모두", "전부", "전체", "모든", "일체", "모두", "전체다", "다알려줘", "다알려", "전부알려줘"]
            is_all_dates_query = any(keyword in query_lower for keyword in all_date_keywords)
            
            # 고객명 질의는 항상 모든 결과 반환 (날짜 누락 방지)
            print(f"[DEBUG] 고객명 직접 검색 결과: 모든 결과 반환 ({len(search_results_from_customer)}개)")
            final_results = search_results_from_customer
            
            # 날짜별로 그룹화하여 모든 날짜가 포함되었는지 확인
            dates_found = set()
            for result in final_results:
                date_str = result.metadata.get("date", "")
                if date_str:
                    dates_found.add(date_str)
            print(f"[DEBUG] 최종 검색 결과 (고객명 직접 검색): {len(final_results)}개 청크, {len(dates_found)}개 날짜 발견: {sorted(dates_found)}")
            
            return final_results
        
        # 벡터 검색 수행
        try:
            # ChromaDB query 수행 (where 필터 적용)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results_for_query,
                where=where_filter
            )
        except Exception as e:
            print(f"[ERROR] ChromaDB query 실패: {e}")
            results = None
        
        # 검색 결과가 없으면 필터를 완화하여 재검색 시도
        if not results or not results.get('ids') or len(results['ids'][0]) == 0:
            print(f"[DEBUG] 초기 검색 결과 없음, 필터 완화하여 재검색 시도...")
            
            # 1차 재시도: 날짜 필터만 제거
            simplified_filter = KeywordFilter.build_where_filter(
                keywords=SearchKeywords(chunk_types=keywords.chunk_types),
                owner=owner,
                base_date_range=None  # 날짜 범위 제거
            )
            
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results_for_query * 2,
                    where=simplified_filter
                )
                
                # 여전히 결과가 없으면 2차 재시도: 최소 필터만 사용
                if not results or not results.get('ids') or len(results['ids'][0]) == 0:
                    print(f"[DEBUG] 1차 재검색도 결과 없음, 최소 필터로 재검색 시도...")
                    minimal_filter = {
                        "$and": [
                            {"report_type": {"$in": ["daily", "weekly", "monthly"]}},
                            {"level": "daily"}
                        ]
                    }
                    if owner:
                        minimal_filter["$and"].append({"owner": owner})
                    
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=n_results_for_query * 3,
                        where=minimal_filter
                    )
                    print(f"[DEBUG] 최소 필터 재검색: {len(results.get('ids', [[]])[0]) if results and results.get('ids') else 0}개 발견")
                else:
                    print(f"[DEBUG] 1차 재검색 성공: {len(results.get('ids', [[]])[0]) if results and results.get('ids') else 0}개 발견")
                    
            except Exception as e2:
                print(f"[WARNING] 재검색 실패: {e2}")
                return []
        
        # 3. 검색 결과 변환
        search_results = []
        initial_result_count = 0
        if results and results.get('ids') and len(results['ids']) > 0:
            initial_result_count = len(results['ids'][0])
        
        print(f"[DEBUG] ChromaDB 검색 결과: {initial_result_count}개 발견")
        
        if results and results.get('ids') and len(results['ids']) > 0:
            ids = results['ids'][0]
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]
            
            for i in range(len(ids)):
                # 거리를 유사도 점수로 변환
                score = 1.0 / (1.0 + distances[i])
                
                search_results.append(
                    UnifiedSearchResult(
                        chunk_id=ids[i],
                        doc_id=metadatas[i].get("doc_id", ""),
                        doc_type=metadatas[i].get("doc_type", "daily"),
                        chunk_type=metadatas[i].get("chunk_type", ""),
                        text=documents[i],
                        score=score,
                        metadata=metadatas[i]
                    )
                )
        
        # 4. 고객명 필터링 (필요시) - 엄격한 필터링
        if keywords.customer_names and len(search_results) > 0:
            # 제외 단어 목록 (고객명이 아닌 단어)
            excluded_words = {
                "상담", "상담한", "상담했", "상담할", "상담하",  # 동사 형태
                "보장", "리포트", "자료", "정리", "구성", "작성", "분석", 
                "업무", "일정", "계획", "뽑아줘", "뽑아", "날짜", "다", "전부", "모두"
            }
            
            # 실제 고객명만 필터링 (제외 단어 제거)
            actual_customer_names = [name for name in keywords.customer_names if name not in excluded_words]
            
            if actual_customer_names:
                # 고객명 필터링 전에 모든 결과를 확인
                filtered_by_customer = []
                for result in search_results:
                    text_lower = result.text.lower()
                    metadata_customer = str(result.metadata.get("customer", "")).strip().lower()
                    
                    # 고객명이 텍스트나 메타데이터에 포함된 경우
                    for customer_name in actual_customer_names:
                        if customer_name in text_lower or customer_name in metadata_customer:
                            filtered_by_customer.append(result)
                            break
                
                print(f"[DEBUG] 고객명 필터링: 원본 {len(search_results)}개 → 필터링 후 {len(filtered_by_customer)}개 (고객명: {actual_customer_names})")
                
                # 고객명 필터링 결과가 있으면 사용, 없어도 최소한 원본 결과에서 고객명 포함된 항목 우선 정렬
                if len(filtered_by_customer) > 0:
                    search_results = filtered_by_customer
                else:
                    print(f"[WARNING] 고객명 '{actual_customer_names}' 매칭 결과 없음")
                    # 원본 결과를 사용하되, 고객명이 포함된 항목을 우선 정렬
                    customer_partial_match = []
                    other_results = []
                    for result in search_results:
                        text_lower = result.text.lower()
                        has_partial = any(name in text_lower for name in actual_customer_names)
                        if has_partial:
                            customer_partial_match.append(result)
                        else:
                            other_results.append(result)
                    search_results = customer_partial_match + other_results
            else:
                print(f"[DEBUG] 실제 고객명 없음 (모두 제외 단어), 필터링 건너뜀")
        
        # 5. Relevance 기준 정렬 및 top_k 적용
        # 고객명이 포함된 경우 우선 정렬
        if keywords.customer_names:
            # 제외 단어 목록
            excluded_words = {"상담", "보장", "리포트", "자료", "정리", "구성", "작성", "분석", "업무", "일정", "계획"}
            actual_customer_names = [name for name in keywords.customer_names if name not in excluded_words]
            
            if actual_customer_names:
                customer_matched = []
                customer_unmatched = []
                
                for result in search_results:
                    text_lower = result.text.lower()
                    metadata_customer = str(result.metadata.get("customer", "")).strip().lower()
                    
                    # 실제 고객명만으로 매칭 확인
                    is_matched = any(
                        customer_name in text_lower or customer_name in metadata_customer
                        for customer_name in actual_customer_names
                    )
                    
                    if is_matched:
                        customer_matched.append(result)
                    else:
                        customer_unmatched.append(result)
                
                # 고객명 매칭 결과를 먼저 정렬 (relevance 높은 순)
                customer_matched.sort(key=lambda r: -r.score)
                customer_unmatched.sort(key=lambda r: -r.score)
                
                search_results = customer_matched + customer_unmatched
                print(f"[DEBUG] 고객명 매칭: {len(customer_matched)}개 (고객명: {actual_customer_names}), 전체: {len(search_results)}개")
        
        # relevance 기준 정렬
        search_results.sort(key=lambda r: -r.score)
        
        # 6. 쿼리 키워드 매칭 강화 (특정 키워드가 포함된 결과 우선 정렬)
        # "연금", "상담" 같은 키워드가 포함된 결과를 우선 정렬
        # 불필요한 단어 제외 목록
        stop_words = {
            "언제", "했었", "했지", "했어", "했는", "했던", "최근", "나", "내", 
            "는", "은", "이", "가", "을", "를", "의", "에", "에서", "로", "으로",
            "고객", "했", "했는지", "했었지", "했었어", "했었는", "했었던"
        }
        
        # 쿼리에서 의미 있는 키워드 추출 (2자 이상, stop words 제외)
        query_words = query.split()
        meaningful_keywords = [
            word for word in query_words 
            if len(word) >= 2 and word not in stop_words
        ]
        
        if meaningful_keywords:
            keyword_matched = []
            keyword_unmatched = []
            
            for result in search_results:
                text_lower = result.text.lower()
                # 의미 있는 키워드가 텍스트에 포함되어 있는지 확인
                has_keyword = any(
                    keyword.lower() in text_lower 
                    for keyword in meaningful_keywords
                )
                
                if has_keyword:
                    keyword_matched.append(result)
                else:
                    keyword_unmatched.append(result)
            
            # 키워드 매칭 결과를 먼저 정렬
            keyword_matched.sort(key=lambda r: -r.score)
            keyword_unmatched.sort(key=lambda r: -r.score)
            
            search_results = keyword_matched + keyword_unmatched
            print(f"[DEBUG] 키워드 매칭: {len(keyword_matched)}개 (키워드: {meaningful_keywords}), 전체: {len(search_results)}개")
        
        # 7. Top-k 적용
        # 비교/통계/고객명 질의는 모든 결과 반환 (정확한 수치 계산을 위해)
        query_lower = query.lower()
        all_date_keywords = ["다", "모두", "전부", "전체", "모든", "일체", "전체다", "다알려줘", "다알려", "전부알려줘", "알려줘"]
        comparison_keywords = ["비교", "비율", "차이", "변화", "증가", "감소", "늘어", "줄어", "대비", "대조"]
        statistical_keywords = ["가장", "많이", "몰린", "많은", "통계", "집계", "건수"]
        
        is_all_dates_query = any(keyword in query_lower for keyword in all_date_keywords)
        is_comparison_query = any(keyword in query_lower for keyword in comparison_keywords)
        is_statistical_query = any(keyword in query_lower for keyword in statistical_keywords)
        requires_all_data = is_comparison_query or is_statistical_query or keywords.is_statistical_query
        
        # 고객명 질의, 비교/통계 질의, 모든 날짜 요청인 경우 모든 결과 반환
        if keywords.customer_names:
            print(f"[DEBUG] 고객명 질의: 모든 결과 반환 ({len(search_results)}개 청크)")
            final_results = search_results
        elif requires_all_data:
            print(f"[DEBUG] 비교/통계 질의: 모든 결과 반환 ({len(search_results)}개 청크)")
            final_results = search_results
        elif is_all_dates_query:
            # 고객명 없지만 모든 날짜 요청: 모든 결과 반환
            print(f"[DEBUG] '모든 날짜' 요청: top_k 제한 제거, 모든 결과 반환 ({len(search_results)}개)")
            final_results = search_results
        else:
            final_results = search_results[:top_k]
        
        # 날짜별로 그룹화하여 모든 날짜가 포함되었는지 확인
        dates_found = set()
        for result in final_results:
            date_str = result.metadata.get("date", "")
            if date_str:
                dates_found.add(date_str)
        
        print(f"[DEBUG] 최종 검색 결과: {len(final_results)}개 청크, {len(dates_found)}개 날짜 발견: {sorted(dates_found)}")
        return final_results
