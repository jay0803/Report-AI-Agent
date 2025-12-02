"""
Unified Retriever

reports 컬렉션에서 doc_type별로 검색을 수행합니다.

Author: AI Assistant
Created: 2025-11-18
"""
from typing import List, Optional, Dict, Any
from datetime import date
from pydantic import BaseModel, Field
from chromadb import Collection
import os

from ingestion.embed import get_embedding_service


class UnifiedSearchResult(BaseModel):
    """통합 검색 결과"""
    chunk_id: str = Field(..., description="청크 ID")
    doc_id: str = Field(..., description="문서 ID")
    doc_type: str = Field(..., description="문서 타입")
    chunk_type: str = Field(..., description="청크 타입")
    text: str = Field(..., description="청크 텍스트")
    score: float = Field(..., description="유사도 점수")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="전체 메타데이터")


class UnifiedRetriever:
    """Unified Documents Retriever"""
    
    def __init__(
        self, 
        collection: Collection,
        openai_api_key: Optional[str] = None,
        embedding_model_type: Optional[str] = None
    ):
        """
        초기화
        
        Args:
            collection: reports Collection 객체
            openai_api_key: OpenAI API 키 (None이면 환경변수에서 가져옴)
            embedding_model_type: 임베딩 모델 타입 ("hf" 또는 "openai", None이면 환경변수에서 가져옴)
        """
        self.collection = collection
        self.embedding_service = get_embedding_service(
            api_key=openai_api_key,
            model_type=embedding_model_type
        )
    
    def search_daily(
        self,
        query: str,
        owner: Optional[str] = None,
        single_date: Optional[str] = None,
        period_start: Optional[str] = None,
        period_end: Optional[str] = None,
        week: Optional[str] = None,
        n_results: int = 5,
        chunk_types: Optional[List[str]] = None,
        doc_ids: Optional[List[str]] = None
    ) -> List[UnifiedSearchResult]:
        """
        일일보고서 청크 검색 (새로운 4청크 구조 기반)
        
        일일보고서의 의미 단위 청크(summary, detail, pending, plan_note)를 검색합니다.
        주간/월간 보고서 생성 시에도 일일보고서 청크를 사용하므로 이 메서드를 통해 검색합니다.
        
        Args:
            query: 검색 쿼리
            owner: 작성자 필터
            single_date: 단일 날짜 (YYYY-MM-DD)
            period_start: 시작 날짜
            period_end: 종료 날짜
            week: ISO week 필터 (예: "2025-W01")
            n_results: 결과 개수
            chunk_types: 청크 타입 필터 (예: ["summary", "detail", "pending", "plan_note"])
                - summary: 금일 진행 업무 요약
                - detail: 세부 업무 목록
                - pending: 미종결 업무
                - plan_note: 익일 계획 및 특이사항
            doc_ids: 사전 필터링된 문서 ID 목록 (날짜 범위 필터링 강제용)
            
        Returns:
            검색 결과 리스트
        """
        # Chroma 필터는 $and를 사용해 복잡한 조건 구성
        conditions = []
        
        # report_type 조건 (새로운 구조만 사용)
        conditions.append({
            "report_type": {"$in": ["daily", "weekly", "monthly"]}
        })
        
        # doc_ids 필터 (날짜 범위 사전 필터링)
        if doc_ids:
            conditions.append({"doc_id": {"$in": doc_ids}})
        
        # chunk_type 필터 (새로운 4청크 구조: summary, detail, pending, plan_note)
        if chunk_types:
            conditions.append({
                "chunk_type": {"$in": chunk_types}
            })
        
        # owner 필터
        if owner:
            conditions.append({"owner": owner})
        
        # week 필터 (새로운 4청크 구조용)
        if week:
            conditions.append({"week": week})
        
        # level 필터 (새로운 4청크 구조용)
        # 현재 일일보고서 검색만 지원 (level="daily")
        # 주간/월간 보고서 생성 시에도 일일보고서 청크만 사용하므로 이 필터로 충분
        conditions.append({"level": "daily"})
        
        # 날짜 필터 (새로운 구조: date 필드만 사용)
        # doc_ids가 제공되면 날짜 필터는 생략 (이미 doc_ids로 필터링됨)
        if not doc_ids:
            if single_date:
                conditions.append({"date": single_date})
            elif period_start and period_end:
                # 일일보고서는 date 필드를 사용하므로, 기간 내 모든 날짜를 $in으로 검색
                # ChromaDB는 날짜 문자열에 대해 $gte/$lte를 지원하지 않으므로 $in 사용
                from datetime import datetime, timedelta
                start = datetime.strptime(period_start, "%Y-%m-%d")
                end = datetime.strptime(period_end, "%Y-%m-%d")
                date_list = []
                current = start
                while current <= end:
                    date_list.append(current.strftime("%Y-%m-%d"))
                    current += timedelta(days=1)
                # date 필드만 검색 (새로운 구조)
                conditions.append({"date": {"$in": date_list}})
        
        # 조건이 하나만 있으면 그대로, 여러개면 $and로 묶기
        if len(conditions) == 1:
            where_filter = conditions[0]
        else:
            where_filter = {"$and": conditions}
        
        return self._execute_search(query, where_filter, n_results)
    
    def search_kpi(
        self,
        query: str,
        category: Optional[str] = None,
        n_results: int = 5
    ) -> List[UnifiedSearchResult]:
        """
        KPI 문서 검색
        
        Args:
            query: 검색 쿼리
            category: KPI 카테고리 필터
            n_results: 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        where_filter = {
            "doc_type": "kpi"
        }
        
        if category:
            where_filter["kpi_category"] = category
        
        return self._execute_search(query, where_filter, n_results)
    
    def search_template(
        self,
        query: str,
        n_results: int = 3
    ) -> List[UnifiedSearchResult]:
        """
        템플릿 문서 검색
        
        Args:
            query: 검색 쿼리
            n_results: 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        where_filter = {
            "doc_type": "template"
        }
        
        return self._execute_search(query, where_filter, n_results)
    
    def search_all(
        self,
        query: str,
        n_results: int = 10
    ) -> List[UnifiedSearchResult]:
        """
        전체 문서 검색 (fallback)
        
        Args:
            query: 검색 쿼리
            n_results: 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        return self._execute_search(query, {}, n_results)
    
    def search_by_doc_type(
        self,
        query: str,
        doc_type: str,
        n_results: int = 5,
        **filters
    ) -> List[UnifiedSearchResult]:
        """
        doc_type 지정 검색 (범용)
        
        Args:
            query: 검색 쿼리
            doc_type: 문서 타입
            n_results: 결과 개수
            **filters: 추가 필터
            
        Returns:
            검색 결과 리스트
        """
        where_filter = {"doc_type": doc_type}
        
        # None이 아닌 필터만 추가
        for key, value in filters.items():
            if value is not None:
                where_filter[key] = value
        
        return self._execute_search(query, where_filter, n_results)
    
    def _get_query_embedding(self, query: str) -> List[float]:
        """
        쿼리를 임베딩으로 변환
        
        Args:
            query: 검색 쿼리
            
        Returns:
            임베딩 벡터
        """
        try:
            return self.embedding_service.embed_text(query)
        except Exception as e:
            print(f"[ERROR] Embedding error: {e}")
            raise
    
    def _execute_search(
        self,
        query: str,
        where_filter: Dict[str, Any],
        n_results: int
    ) -> List[UnifiedSearchResult]:
        """
        실제 검색 수행
        
        Args:
            query: 검색 쿼리
            where_filter: Chroma where 필터
            n_results: 결과 개수
            
        Returns:
            검색 결과 리스트
        """
        try:
            # 디버깅: 필터 조건 출력
            print(f"[DEBUG] 검색 쿼리: {query}")
            print(f"[DEBUG] 필터 조건: {where_filter}")
            print(f"[DEBUG] 컬렉션 총 문서 수: {self.collection.count()}")
            
            # OpenAI로 쿼리 임베딩 생성
            query_embedding = self._get_query_embedding(query)
            
            # Chroma 검색 (임베딩 직접 전달)
            # where 필터가 비어있으면 None으로 전달
            where_param = where_filter if where_filter else None
            
            # 의미 검색을 위해 query() 사용 (필수)
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=n_results,
                    where=where_param
                )
            except Exception as query_error:
                # ChromaDB 버전 호환성 문제 - 에러 상세 출력
                error_type = type(query_error).__name__
                error_msg = str(query_error)
                print(f"[ERROR] ChromaDB query 실패: {error_type}: {error_msg}")
                
                # dimensionality 에러인 경우 컬렉션 재생성 필요
                if 'dimensionality' in error_msg.lower():
                    print(f"[ERROR] ⚠️  ChromaDB 컬렉션 구조 문제 감지!")
                    print(f"[ERROR] 컬렉션을 재생성해야 합니다:")
                    print(f"[ERROR]   python debug/fix_chromadb_collection.py")
                    print(f"[ERROR]   python -m backend.ingestion.ingest_mock_reports")
                    print(f"[ERROR] 의미 검색을 위해 컬렉션 재생성이 필요합니다.")
                
                import traceback
                traceback.print_exc()
                # 의미 검색이 필수이므로 빈 결과 반환 (fallback 없음)
                return []
            
            # 디버깅: 검색 결과 수 출력
            if results and results['ids']:
                print(f"[DEBUG] 검색 결과: {len(results['ids'][0])}개 발견")
                # 첫 번째 결과의 메타데이터 출력
                if len(results['metadatas'][0]) > 0:
                    print(f"[DEBUG] 첫 번째 결과 메타데이터: {results['metadatas'][0][0]}")
            else:
                print(f"[DEBUG] 검색 결과 없음")
            
            # 결과 변환
            search_results = []
            
            if results and results['ids'] and len(results['ids']) > 0:
                ids = results['ids'][0]
                documents = results['documents'][0]
                metadatas = results['metadatas'][0]
                distances = results['distances'][0]
                
                for i in range(len(ids)):
                    # 거리를 유사도 점수로 변환 (낮을수록 유사 → 높을수록 유사)
                    score = 1.0 / (1.0 + distances[i])
                    
                    search_results.append(
                        UnifiedSearchResult(
                            chunk_id=ids[i],
                            doc_id=metadatas[i].get("doc_id", ""),
                            doc_type=metadatas[i].get("doc_type", ""),
                            chunk_type=metadatas[i].get("chunk_type", ""),
                            text=documents[i],
                            score=score,
                            metadata=metadatas[i]
                        )
                    )
            
            return search_results
        
        except Exception as e:
            print(f"[ERROR] Search error: {e}")
            return []

