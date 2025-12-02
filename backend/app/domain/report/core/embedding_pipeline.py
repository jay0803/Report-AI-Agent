"""
임베딩 파이프라인
HF sentence-transformers/all-MiniLM-L12-v2 기본 사용
"""
import os
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer

from app.infrastructure.vector_store_report import get_report_vector_store


# 기본 모델 설정
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
DEFAULT_DIMENSION = 384
BATCH_SIZE = 100


class EmbeddingPipeline:
    """임베딩 파이프라인"""
    
    def __init__(self, model_name: Optional[str] = None, vector_store=None):
        """
        초기화
        
        Args:
            model_name: Hugging Face 모델명 (None이면 기본값 사용)
            vector_store: Vector Store 인스턴스 (None이면 기본 vector store 사용)
        """
        self.model_name = model_name or DEFAULT_MODEL
        self.model = SentenceTransformer(self.model_name)
        self.dimension = DEFAULT_DIMENSION
        self.vector_store = vector_store or get_report_vector_store()
    
    def embed_texts(self, texts: List[str], batch_size: int = BATCH_SIZE) -> List[List[float]]:
        """
        텍스트 리스트를 임베딩으로 변환
        
        Args:
            texts: 텍스트 리스트
            batch_size: 배치 크기
            
        Returns:
            임베딩 리스트
        """
        embeddings = []
        total = len(texts)
        
        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self.model.encode(batch, convert_to_numpy=True).tolist()
            embeddings.extend(batch_embeddings)
        
        return embeddings
    
    def process_and_store(
        self,
        chunks: List[Dict[str, Any]],
        batch_size: int = BATCH_SIZE
    ) -> Dict[str, Any]:
        """
        청크를 임베딩하고 VectorDB에 저장
        
        Args:
            chunks: 청크 리스트
            batch_size: 배치 크기
            
        Returns:
            처리 결과 딕셔너리
        """
        if not chunks:
            return {"success": False, "message": "No chunks provided"}
        
        # 텍스트 추출
        texts = [chunk["text"] for chunk in chunks]
        
        # 임베딩 생성
        embeddings = self.embed_texts(texts, batch_size)
        
        # VectorDB 저장
        self.vector_store.insert_chunks(chunks, embeddings)
        
        collection = self.vector_store.get_collection()
        
        return {
            "success": True,
            "chunks_processed": len(chunks),
            "embeddings_created": len(embeddings),
            "total_documents": collection.count()
        }


# 전역 인스턴스
_embedding_pipeline = None


def get_embedding_pipeline(model_name: Optional[str] = None) -> EmbeddingPipeline:
    """
    EmbeddingPipeline 싱글톤 인스턴스 가져오기
    
    Args:
        model_name: 모델명 (선택적)
        
    Returns:
        EmbeddingPipeline 인스턴스
    """
    global _embedding_pipeline
    if _embedding_pipeline is None:
        _embedding_pipeline = EmbeddingPipeline(model_name)
    return _embedding_pipeline

