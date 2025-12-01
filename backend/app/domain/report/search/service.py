"""
Unified Search Service

Intent Router와 Retriever를 결합하여 통합 검색 서비스를 제공합니다.

Author: AI Assistant
Created: 2025-11-18
"""
from typing import List, Optional, Dict, Any
from .retriever import UnifiedRetriever, UnifiedSearchResult
from .intent_router import IntentRouter, QueryIntent


class UnifiedSearchService:
    """통합 검색 서비스"""
    
    def __init__(self, retriever: UnifiedRetriever, router: IntentRouter):
        """
        초기화
        
        Args:
            retriever: UnifiedRetriever 인스턴스
            router: IntentRouter 인스턴스
        """
        self.retriever = retriever
        self.router = router
    
    async def search(
        self,
        query: str,
        user: Optional[str] = None,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        통합 검색 수행
        
        Args:
            query: 검색 쿼리
            user: 사용자/작성자 (선택)
            n_results: 결과 개수
            
        Returns:
            검색 결과 딕셔너리
            {
                "query": str,
                "intent": str,
                "reason": str,
                "results": List[UnifiedSearchResult],
                "count": int
            }
        """
        # 1. Intent 분석
        intent_result: QueryIntent = self.router.route(query)
        
        # 2. Intent에 따라 검색 수행
        results: List[UnifiedSearchResult] = []
        
        if intent_result.intent == "daily":
            # 일일 보고서 검색
            results = self.retriever.search_daily(
                query=query,
                owner=user,
                n_results=n_results
            )
        
        elif intent_result.intent == "weekly":
            # 주간 보고서 검색 (doc_type으로 필터링)
            results = self.retriever.search_by_doc_type(
                query=query,
                doc_type="weekly",
                owner=user,
                n_results=n_results
            )
        
        elif intent_result.intent == "monthly":
            # 월간 보고서 검색
            results = self.retriever.search_by_doc_type(
                query=query,
                doc_type="monthly",
                owner=user,
                n_results=n_results
            )
        
        
        elif intent_result.intent == "template":
            # 템플릿 검색
            results = self.retriever.search_template(
                query=query,
                n_results=min(n_results, 3)  # 템플릿은 적게 반환
            )
        
        elif intent_result.intent == "mixed":
            # 혼합 검색 - 전체 검색
            results = self.retriever.search_all(
                query=query,
                n_results=n_results * 2  # 더 많은 결과 반환
            )
        
        else:
            # unknown - fallback to 전체 검색
            results = self.retriever.search_all(
                query=query,
                n_results=n_results
            )
        
        # 3. 결과 반환
        return {
            "query": query,
            "intent": intent_result.intent,
            "reason": intent_result.reason,
            "filters": intent_result.filters,
            "results": results,
            "count": len(results)
        }
    
    def search_sync(
        self,
        query: str,
        user: Optional[str] = None,
        n_results: int = 5
    ) -> Dict[str, Any]:
        """
        동기 검색 (비async 버전)
        
        Args:
            query: 검색 쿼리
            user: 사용자/작성자 (선택)
            n_results: 결과 개수
            
        Returns:
            검색 결과 딕셔너리
        """
        # 1. Intent 분석
        intent_result: QueryIntent = self.router.route(query)
        
        # 2. Intent에 따라 검색 수행
        results: List[UnifiedSearchResult] = []
        
        if intent_result.intent == "daily":
            results = self.retriever.search_daily(
                query=query,
                owner=user,
                n_results=n_results
            )
        
        elif intent_result.intent == "weekly":
            results = self.retriever.search_by_doc_type(
                query=query,
                doc_type="weekly",
                owner=user,
                n_results=n_results
            )
        
        elif intent_result.intent == "monthly":
            results = self.retriever.search_by_doc_type(
                query=query,
                doc_type="monthly",
                owner=user,
                n_results=n_results
            )
        
        elif intent_result.intent == "kpi":
            category = intent_result.filters.get("category")
            results = self.retriever.search_kpi(
                query=query,
                category=category,
                n_results=n_results
            )
        
        elif intent_result.intent == "template":
            results = self.retriever.search_template(
                query=query,
                n_results=min(n_results, 3)
            )
        
        elif intent_result.intent == "mixed":
            results = self.retriever.search_all(
                query=query,
                n_results=n_results * 2
            )
        
        else:
            results = self.retriever.search_all(
                query=query,
                n_results=n_results
            )
        
        # 3. 결과 반환
        return {
            "query": query,
            "intent": intent_result.intent,
            "reason": intent_result.reason,
            "filters": intent_result.filters,
            "results": results,
            "count": len(results)
        }

